// Qualification seam only. Reviewed bundled code; not a same-UID plugin isolation boundary.
import { createRequire } from 'node:module';
import { isAbsolute } from 'node:path';
import { isDeepStrictEqual } from 'node:util';
const cli = createRequire(new URL('../../cli/package.json', import.meta.url));
const { HarnessError } = await import(cli.resolve('@deepseek-ai/dsh-llm'));
export class TerminalAuthorizationError extends HarnessError {}
const fail = (code, message, cause) => new TerminalAuthorizationError(message, code, { cause });
const keys = ['sessionId', 'callId', 'ownerId', 'terminalId', 'backend', 'executable', 'arguments', 'cwd', 'columns', 'rows'];
const outcomes = new Set(['allowed-once', 'rejected', 'cancelled', 'unavailable']);
function nativeConfiguration(input, ids) {
  if (!input || !['sessionId', 'backend', 'executable', 'cwd'].every(key => typeof input[key] === 'string' && !input[key].includes('\0'))
    || input.sessionId.length < 1 || input.sessionId.length > 256 || input.backend !== 'android-fixed-pty-v1'
    || !isAbsolute(input.cwd) || !isAbsolute(input.executable) || !input.executable.endsWith('/libharness_pty_fixture.so')
    || !Number.isSafeInteger(input.uid) || input.uid <= 0 || !Array.isArray(ids) || ids.length < 1 || ids.length > 2
    || new Set(ids).size !== ids.length || !ids.every(id => typeof id === 'string' && id.length > 0 && id.length <= 256 && !id.includes('\0'))) {
    throw fail('TERMINAL_CONFIGURATION_INVALID', 'Native-owned fixed qualification configuration is required');
  }
  return { configuration: Object.freeze({ sessionId: input.sessionId, backend: input.backend,
    executable: input.executable, cwd: input.cwd, uid: input.uid }), callIds: Object.freeze([...ids]) };
}


function checkedFields(fields, configuration, callIds) {
  if (!fields || typeof fields !== 'object' || Object.keys(fields).sort().join() !== [...keys].sort().join()
    || !keys.filter(key => !['arguments', 'columns', 'rows'].includes(key)).every(key => typeof fields[key] === 'string')
    || fields.sessionId !== configuration.sessionId || fields.ownerId !== configuration.sessionId
    || !callIds.includes(fields.callId) || !/^pty-[1-9][0-9]{0,15}$/.test(fields.terminalId)
    || fields.backend !== 'android-fixed-pty-v1' || fields.backend !== configuration.backend
    || fields.executable !== configuration.executable || !isAbsolute(fields.executable)
    || !fields.executable.endsWith('/libharness_pty_fixture.so') || fields.cwd !== configuration.cwd || !isAbsolute(fields.cwd)
    || !isDeepStrictEqual(fields.arguments, ['--tty-child']) || fields.columns !== 80 || fields.rows !== 24) {
    throw fail('TERMINAL_REQUEST_CHANGED', 'Fixed native terminal binding does not match');
  }
  return Object.freeze({ ...fields, arguments: Object.freeze([...fields.arguments]) });
}

/** Controller-side relay: only the native broker supplies the outcome, never reason text or agent output. */
export async function relayTerminalApproval(params, options) {
  const { configuration, callIds } = nativeConfiguration(options.configuration, options.callIds);
  const { toolName, requestNative } = options;
  if (params.toolName !== toolName || params.sessionId !== configuration.sessionId) {
    throw fail('TERMINAL_REQUEST_CHANGED', 'Unexpected original approval request');
  }
  let fields;
  try { fields = checkedFields(JSON.parse(params.reason), configuration, callIds); }
  catch (cause) { throw fail('TERMINAL_REQUEST_CHANGED', 'Malformed terminal allocation reason', cause); }
  if (fields.callId !== params.callId) throw fail('TERMINAL_REQUEST_CHANGED', 'Approval call binding changed');
  const reply = await requestNative('prepare', fields);
  if (!reply?.ok || !outcomes.has(reply.outcome)) throw fail('TERMINAL_BROKER_REJECTED', 'Native approval did not return a valid outcome');
  return { outcome: reply.outcome };
}

/** One original tool call owns this allocation authority. It creates no PTY itself. */
export function createTerminalAllocationAuthority({ ctx, exec, configuration: inputConfiguration, callIds: inputCallIds, toolName, registryType, requestNative }) {
  const { configuration, callIds } = nativeConfiguration(inputConfiguration, inputCallIds);
  let state = 'new', binding, originalSpec, revocation;
  const revoked = new AbortController();
  function cancel() {
    if (!binding) return Promise.resolve();
    revocation ??= (async () => {
      const reply = await requestNative('cancel', binding);
      if (!reply?.ok) throw fail('TERMINAL_AUTHORITY_CLEANUP_FAILED', 'Native grant revocation was not acknowledged');
    })();
    return revocation;
  }
  return {
    async authorize(spec, callerSignal) {
      const signal = AbortSignal.any([callerSignal, revoked.signal]);
      signal.throwIfAborted();
      if (state !== 'new') throw fail('TERMINAL_PERMIT_USED', 'Allocation authority has already been attempted');
      if (!exec.agent || ctx.agents.get(exec.agent.id) !== exec.agent || spec.owner !== exec.agent
        || spec.type !== registryType || spec.cwd !== configuration.cwd) {
        throw fail('TERMINAL_AUTHORITY_REQUIRED', 'A genuine matching original tool/Agent context is required');
      }
      binding = checkedFields({ sessionId: exec.agent.id, ownerId: spec.owner.id, callId: exec.callId,
        terminalId: spec.sessionId, backend: configuration.backend, executable: configuration.executable,
        arguments: ['--tty-child'], cwd: spec.cwd, columns: 80, rows: 24 }, configuration, callIds);
      state = 'preparing'; originalSpec = spec;
      try {
        const outcome = await ctx.approval.request({ agent: exec.agent, toolName, callId: exec.callId,
          reason: JSON.stringify(binding), signal });
        signal.throwIfAborted();
        if (outcome !== 'allowed-once') {
          const code = { rejected: 'TERMINAL_APPROVAL_REJECTED', cancelled: 'TERMINAL_APPROVAL_CANCELLED', unavailable: 'TERMINAL_APPROVAL_UNAVAILABLE' }[outcome];
          throw fail(code ?? 'TERMINAL_BROKER_REJECTED', 'Original approval did not authorize terminal allocation');
        }
        const reply = await requestNative('consume', binding, signal);
        if (!reply?.ok) throw fail('TERMINAL_BROKER_REJECTED', 'Native allocation consumption rejected: ' + String(reply?.code));
        const returned = Object.fromEntries(keys.map(key => [key, reply.allocation?.[key]]));
        if (!isDeepStrictEqual(returned, binding) || reply.allocation.uid !== configuration.uid) {
          throw fail('TERMINAL_REQUEST_CHANGED', 'Native allocation receipt changed the approved request');
        }
        signal.throwIfAborted(); state = 'granted';
      } catch (cause) {
        state = 'closed';
        try { await cancel(); }
        catch (cleanup) { throw fail('TERMINAL_AUTHORITY_CLEANUP_FAILED', 'Allocation and revocation failed', new AggregateError([cause, cleanup])); }
        throw cause;
      }
    },
    take(spec) {
      revoked.signal.throwIfAborted(); spec.signal?.throwIfAborted();
      if (ctx.agents.get(exec.agent.id) !== exec.agent) throw fail('TERMINAL_AUTHORITY_REQUIRED', 'Original Agent owner is no longer live');
      if (state !== 'granted' || spec !== originalSpec) throw fail('TERMINAL_PERMIT_USED', 'No unused exact allocation receipt exists');
      state = 'taken'; return binding;
    },
    async close() { revoked.abort(fail('TERMINAL_AUTHORITY_REVOKED', 'Allocation owner revoked authority')); state = 'closed'; await cancel(); },
  };
}
