// Fixed original terminal qualification. No automated decisions or arbitrary commands.
import { AsyncLocalStorage } from 'node:async_hooks';
import { createRequire } from 'node:module';
import { createTerminalAllocationAuthority } from './terminal-authorization.mjs';
import { terminalRequest } from './terminal-wire.mjs';
import { readProcIdentity } from './proc-identity.mjs';
import { createFixtureTerminalBackend, createAndroidFixtureTerminalBackend } from './node-pty-proof/terminal-backend.bundle.mjs';
import { createFixtureTerminalHandle, createAndroidFixtureTerminalHandle } from './node-pty-proof/terminal-handle.bundle.mjs';
const cli = createRequire(new URL('../../cli/package.json', import.meta.url));
const subprocess = createRequire(new URL('../../../packages/subprocess/subprocess-local/package.json', import.meta.url));
const require = createRequire(import.meta.url);
const { defineTool } = await import(cli.resolve('@deepseek-ai/dsh-tools'));
export const name = 'android-terminal-qualification';
export const inject = ['agents', 'tools', 'commands', 'terminals', 'approval'];
export async function apply(ctx) {
  const native = await terminalRequest('describe');
  if (!native.ok || native.callIds.length !== 2) throw new Error('Native terminal configuration unavailable');
  const configuration = native.configuration, callIds = native.callIds, sessionId = native.sessionId;
  const host = process.platform === 'linux' && process.env.HARNESS_TERMINAL_HOST_QUALIFICATION === '1';
  if (!host && process.platform !== 'android') throw new Error('Unsupported qualification platform');
  const pty = host ? subprocess('node-pty') : require('./node-pty-proof/loader.cjs')(
    process.env.HARNESS_NODE_PTY_PACKAGE, process.env.HARNESS_NODE_PTY_ADDON);
  if (!host && configuration.executable !== process.env.HARNESS_NODE_PTY_FIXTURE) throw new Error('Installed fixture binding changed');
  const lifecycle = configuration.qualification === 'lifecycle'
  const scope = new AsyncLocalStorage(), toolName = 'android_qualified_terminal';
  let next = 0, starts = 0, concurrentConsumers = 0, concurrentRejections = 0;
  const backend = (host ? createFixtureTerminalBackend : createAndroidFixtureTerminalBackend)({ startupMs: 5000, authorizationMs: 65000, sendWaitMs: lifecycle ? 1000 : 5000,
    async authorize(spec, signal) {
      const authority = scope.getStore();
      if (!authority) throw new Error('No original tool allocation context');
      await authority.authorize(spec, signal);
    },
    createHandle(spec, ownerSignal) {
      const authority = scope.getStore();
      let changedRejected = false;
      try { authority.take({ ...spec }); } catch (error) { changedRejected = error.code === 'TERMINAL_PERMIT_USED'; }
      if (!changedRejected) throw new Error('Changed allocation object was accepted');
      const receipt = authority.take(spec);
      let replayRejected = false;
      try { authority.take(spec); } catch (error) { replayRejected = error.code === 'TERMINAL_PERMIT_USED'; }
      if (!replayRejected) throw new Error('Allocation receipt was reused');
      starts++;
      return (host ? createFixtureTerminalHandle : createAndroidFixtureTerminalHandle)(pty, {
        fixtureExecutable: receipt.executable, cwd: receipt.cwd, role: '--tty-child', graceMs: 300, ownerSignal,
      });
    },
  });
  ctx.terminals.registerBackend(backend);
  ctx.tools.register(defineTool({ name: toolName, description: 'Native-approved fixed TTY fixture qualification; no shell.', parameters: {},
    output: { schema: { type: 'object', additionalProperties: false, properties: { report: { type: 'string', required: true } } },
      render: (_args, value) => [{ type: 'text', text: value.report }] },
    async execute(_args, exec) {
      const authority = createTerminalAllocationAuthority({ ctx, exec, configuration, callIds, toolName,
        registryType: backend.type, requestNative: async (action, fields, signal) => {
          if (action !== 'consume') return terminalRequest(action, fields, signal);
          const replies = await Promise.all([terminalRequest(action, fields, signal), terminalRequest(action, fields, signal)]);
          const winners = replies.filter(reply => reply.ok), rejected = replies.filter(reply => reply.code === 'USED');
          if (winners.length !== 1 || rejected.length !== 1) throw new Error('Native concurrent allocation invariant failed');
          concurrentConsumers = 2; concurrentRejections = 1; return winners[0];
        } });
      let terminal;
      try {
        terminal = await scope.run(authority, () => ctx.terminals.spawn(exec.agent, { type: backend.type, cwd: configuration.cwd }, exec.signal));
        let result, lifecycleReport;
        if (lifecycle) {
          const wait = ctx.terminals.startSend(exec.agent, terminal.sessionId, { text: '', submit: false });
          const timeout = await wait.done;
          if (timeout.waitReason !== 'timeout' || timeout.sessionStatus.kind !== 'running' || wait.cancel()) throw new Error('Terminal timeout state differs');
          process.kill(terminal.pid, 0); // A wait timeout does not itself terminate the terminal.
          const operation = ctx.terminals.startSend(exec.agent, terminal.sessionId, { text: '', submit: false });
          if (!operation.cancel() || operation.cancel()) throw new Error('Terminal cancellation was not one-shot');
          result = await operation.done;
          if (result.waitReason !== 'session_exit' || result.sessionStatus.kind !== 'exited'
            || result.sessionStatus.exitCode !== null || result.sessionStatus.signal !== 'SIGINT' || operation.cancel()) {
            throw new Error('Actual original terminal cancellation outcome differs');
          }
          try { process.kill(terminal.pid, 0); throw new Error('Cancelled child remains observable'); }
          catch (error) { if (error.code !== 'ESRCH') throw error; }
          lifecycleReport = { timeout, timeoutLeavesChildRunning: true, explicitCancellation: true,
            repeatedCancellationRejected: true, childNoLongerObservable: true };
        } else {
          result = await ctx.terminals.startSend(exec.agent, terminal.sessionId, { text: 'pty-input', submit: true }).done;
          if (result.sessionStatus.kind !== 'exited' || result.sessionStatus.exitCode !== 0 || result.sessionStatus.signal !== null
            || !result.viewport.includes('TTY-INPUT:pty-input ROWS:40 COLS:100') || !result.viewport.includes('TTY-STDERR')) {
            throw new Error('Actual original terminal outcome differs');
          }
        }
        const match = result.viewport.match(/IDENTITY:(\{[^\r\n]+\})/);
        if (!match) throw new Error('Native child identity missing');
        const identity = JSON.parse(match[1]);
        if (identity.uid !== configuration.uid || identity.pid !== terminal.pid || identity.parentPid !== process.pid) throw new Error('Native TTY identity changed');
        const terminalId = terminal.sessionId;
        await ctx.terminals.kill(exec.agent, terminalId); terminal = undefined;
        if (ctx.terminals.hasOwnerActivity(exec.agent)) throw new Error('Original terminal owner activity did not drain');
        return { report: JSON.stringify({ originalTerminalRegistry: true, terminalId, result, nativeIdentity: identity,
          qualification: lifecycle ? 'lifecycle' : 'input-resize', lifecycle: lifecycleReport, engineIdentity: readProcIdentity(), starts, concurrentConsumers, concurrentRejections, changedReceiptRejected: true, replayedReceiptRejected: true,
          ownerActivityDrained: true, stderrMergedByPty: true }) };
      } finally {
        try { if (terminal) await ctx.terminals.kill(exec.agent, terminal.sessionId); }
        finally { await authority.close(); }
      }
    },
  }));
  ctx.commands.register({ name: 'android-terminal-call', description: 'Invoke the registered fixed terminal tool.', async handler({ agent, signal }) {
    if (agent.id !== sessionId || next >= callIds.length) return { kind: 'error', text: 'Qualification budget exhausted' };
    const callId = callIds[next++];
    const batch = await ctx.tools.execute({ agent, signal, calls: [{ type: 'tool-call', id: callId, name: toolName, arguments: '{}' }] });
    return { kind: 'success', text: JSON.stringify({ terminalProof: true, callId, batch, processStarts: starts }) };
  } });
  ctx.commands.register({ name: 'android-terminal-history', description: 'Read actual persisted qualification records.', handler({ agent }) {
    return { kind: 'success', text: JSON.stringify(agent.session.snapshotEvents().filter(e => e.type === 'approval/asked'
      || e.type === 'approval/decided' || (e.type === 'command/done' && e.data.text?.startsWith('{"terminalProof":')))) };
  } });
  ctx.on('agent/pre-step', async ({ agent, signal }, nextStep) => {
    if (agent.id !== sessionId) return nextStep();
    await ctx.commands.execute(agent, process.env.HARNESS_TERMINAL_RECOVER_ONLY === '1' ? '/android-terminal-history' : '/android-terminal-call', [], signal);
    return { kind: 'reject' }; // No model response or model tool-call events are manufactured.
  });
  ctx.provide('androidTerminalQualificationReady', { ready: true });
}
