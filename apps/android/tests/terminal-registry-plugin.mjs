// HOST ONLY: real original SDK/profile/tools/approval/agents/terminal registry.
// Automated SDK approval and this fixture authority are NOT Android native authorization.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { AsyncLocalStorage } from 'node:async_hooks';
import { createRequire } from 'node:module';
import { createFixtureTerminalBackend } from '../runtime/node-pty-proof/terminal-backend.ts';
import { createFixtureTerminalHandle } from '../runtime/node-pty-proof/terminal-handle.ts';
const cli = createRequire(new URL('../../cli/package.json', import.meta.url));
const ptyResolve = createRequire(new URL('../../../packages/subprocess/subprocess-local/package.json', import.meta.url));
const pty = ptyResolve('node-pty');
const { defineTool } = await import(cli.resolve('@deepseek-ai/dsh-tools'));
const scope = new AsyncLocalStorage();
export const name = 'host-terminal-registry-qualification';
export const inject = ['tools', 'approval', 'commands', 'terminals', 'agents'];
export function apply(ctx) {
  const rootId = process.env.HARNESS_TERMINAL_SESSION;
  const cwd = process.env.HARNESS_TERMINAL_WORKSPACE;
  const fixture = process.env.HARNESS_NODE_PTY_FIXTURE;
  const calls = ['deny-terminal', 'allow-terminal']; let next = 0, starts = 0;
  const pids = []; const permissions = [];
  let cancellation, publicationCancellation;
  const backend = createFixtureTerminalBackend({ startupMs: 5000,
    async authorize(request, signal) {
      signal.throwIfAborted();
      const current = scope.getStore();
      if (!current || !current.owners.has(request.owner) || request.cwd !== cwd) throw new Error('HOST_FIXTURE_AUTHORITY_REQUIRED');
      permissions.push({ owner: request.owner.id, terminalId: request.sessionId, cwd: request.cwd, name: request.name });
      if (request.name === 'cancel-before-allocation') await new Promise(resolve => { current.release = resolve; current.waiting.resolve(); });
    },
    createHandle(request, ownerSignal) {
      starts++;
      const handle = createFixtureTerminalHandle(pty, { fixtureExecutable: fixture, cwd: request.cwd, role: request.name === 'fail-startup' ? '--exit-seven' : '--tty-child', graceMs: 100, ownerSignal });
      pids.push(handle.pid);
      if (request.name === 'cancel-after-allocation') handle.output.once('data', () => cancellation.abort(new Error('controlled allocation cancellation')));
      return handle;
    },
  });
  ctx.terminals.registerBackend({ type: backend.type, async spawn(spec) {
    const session = await backend.spawn(spec);
    if (spec.name === 'cancel-at-publication') publicationCancellation.abort(new Error('publication cancellation'));
    return session;
  } });
  async function run(agent) {
    const child = await ctx.agents.create({ sessionId: 'terminal-owned-' + crypto.randomUUID(), meta: { cwd },
      agentOptions: { provider: 'deepseek-official', model: 'deepseek-v4-flash' } });
    const unscopedStarts = starts;
    await assert.rejects(ctx.terminals.spawn(agent, { type: backend.type, name: 'without-host-permit', cwd }), /HOST_FIXTURE_AUTHORITY_REQUIRED/);
    assert.equal(starts, unscopedStarts); assert.equal(ctx.terminals.hasOwnerActivity(agent), false);
    const state = { owners: new Set([agent, child.agent]) };
    return scope.run(state, async () => {
      try {
        const terminal = await ctx.terminals.spawn(agent, { type: backend.type, name: 'main', cwd });
        assert.equal(ctx.terminals.list(agent).length, 1);
        assert.equal(ctx.terminals.list(child.agent).length, 0);
        assert.equal(ctx.terminals.hasOwnerActivity(agent), true);
        const negatives = {};
        const rejected = async (key, action, code) => { await assert.rejects(action, error => { negatives[key] = error.code; return error.code === code; }); };
        assert.throws(() => ctx.terminals.read(child.agent, terminal.sessionId), error => { negatives.foreign = error.code; return error.code === 'FOREIGN_SESSION'; });
        await rejected('duplicateName', () => ctx.terminals.spawn(agent, { type: backend.type, name: 'main', cwd }), 'DUPLICATE_NAME');
        await rejected('forgedOwner', () => ctx.terminals.spawn({ id: agent.id, ctx: agent.ctx }, { type: backend.type, cwd }), 'OWNER_NOT_LIVE');
        await rejected('unknownForeground', () => ctx.terminals.signal(agent, terminal.sessionId, 'SIGTERM'), 'SUBPROCESS_PTY_UNAVAILABLE');
        assert.throws(() => ctx.terminals.startSend(agent, terminal.sessionId, { text: 'arbitrary command', submit: true }), { code: 'INIT_REJECTED' });
        const operation = ctx.terminals.startSend(agent, terminal.sessionId, { text: 'pty-input', submit: true });
        assert.throws(() => ctx.terminals.startSend(agent, terminal.sessionId, { text: 'pty-input', submit: true }), error => { negatives.concurrentSend = error.code; return error.code === 'SEND_ACTIVE'; });
        const result = await operation.done;
        assert.deepEqual(result.sessionStatus, { kind: 'exited', exitCode: 0, signal: null });
        assert.equal(result.waitReason, 'session_exit');
        assert.match(result.viewport, /TTY-INPUT:pty-input ROWS:40 COLS:100/);
        assert.match(ctx.terminals.read(agent, terminal.sessionId, { count: 64 }).text, /TTY-STDERR/);
        assert.equal(operation.cancel(), false);
        assert.equal(await ctx.terminals.kill(agent, terminal.sessionId), true);
        assert.equal(ctx.terminals.hasOwnerActivity(agent), false);

        await rejected('startupExit', () => ctx.terminals.spawn(agent, { type: backend.type, name: 'fail-startup', cwd }), 'STARTUP_EXITED');
        assert.equal(ctx.terminals.hasOwnerActivity(agent), false); assert.equal(ctx.terminals.list(agent).length, 0);
        assert.throws(() => process.kill(pids.at(-1), 0), { code: 'ESRCH' });

        // Cancel while authority is held, then release its late answer: no process may start.
        const before = starts; const controller = new AbortController(); state.waiting = Promise.withResolvers();
        const pending = ctx.terminals.spawn(agent, { type: backend.type, name: 'cancel-before-allocation', cwd }, controller.signal);
        await state.waiting.promise;
        assert.equal(ctx.terminals.hasOwnerActivity(agent), true);
        controller.abort(new Error('before-allocation cancellation'));
        await assert.rejects(pending, /cancellation/);
        state.release(); await Promise.resolve(); await Promise.resolve();
        assert.equal(starts, before); assert.equal(ctx.terminals.hasOwnerActivity(agent), false);

        cancellation = new AbortController();
        const cancelStarted = starts;
        await assert.rejects(ctx.terminals.spawn(agent, { type: backend.type, name: 'cancel-after-allocation', cwd }, cancellation.signal), /cancellation/);
        assert.equal(starts, cancelStarted + 1); assert.equal(ctx.terminals.list(agent).length, 0);
        assert.equal(ctx.terminals.hasOwnerActivity(agent), false);
        assert.throws(() => process.kill(pids.at(-1), 0), { code: 'ESRCH' });
        // The failed reservation must release its owner-local name.
        const retried = await ctx.terminals.spawn(agent, { type: backend.type, name: 'cancel-after-allocation', cwd });
        await ctx.terminals.kill(agent, retried.sessionId);

        publicationCancellation = new AbortController();
        await assert.rejects(ctx.terminals.spawn(agent, { type: backend.type, name: 'cancel-at-publication', cwd }, publicationCancellation.signal), /publication cancellation/);
        assert.equal(ctx.terminals.list(agent).length, 0); assert.equal(ctx.terminals.hasOwnerActivity(agent), false);
        assert.throws(() => process.kill(pids.at(-1), 0), { code: 'ESRCH' });

        const owned = await ctx.terminals.spawn(child.agent, { type: backend.type, name: 'disposed-owner', cwd });
        await child.dispose();
        assert.equal(ctx.terminals.hasOwnerActivity(child.agent), false);
        assert.equal(ctx.terminals.list(child.agent).length, 0);
        assert.throws(() => process.kill(owned.pid, 0), { code: 'ESRCH' });
        await rejected('disposedOwner', () => ctx.terminals.spawn(child.agent, { type: backend.type, cwd }), 'OWNER_NOT_LIVE');
        for (const pid of pids) assert.throws(() => process.kill(pid, 0), { code: 'ESRCH' });
        return { originalTerminalRegistry: true, genuineAgentOwners: 2, unscopedAuthorityRejected: true, negatives, result, starts, pids,
          allocationCancellationBeforeSpawn: true, allocationCancellationAfterSpawn: true, registryPublicationRollbackObserved: true, ownerDisposalObserved: true,
          registeredOwnerActivityDrained: true, startupFailureCleanupObserved: true, authority: 'host fixture only; not Android native authorization' };
      } finally {
        state.release?.();
        await child.dispose();
        for (const terminal of ctx.terminals.list(agent)) await ctx.terminals.kill(agent, terminal.sessionId, 'host fixture cleanup');
      }
    });
  }
  ctx.tools.register(defineTool({ name: 'host_qualified_terminal', description: 'Host-only fixed original terminal registry qualification.', parameters: {},
    output: { schema: { type: 'object', additionalProperties: false, properties: { report: { type: 'string', required: true } } }, render: (_args, value) => [{ type: 'text', text: value.report }] },
    async execute(_args, exec) { if (exec.agent.id !== rootId) throw new Error('Wrong host qualification session'); return { report: JSON.stringify(await run(exec.agent)) }; },
  }));
  ctx.on('tools/pre-execute', async (exec, next) => {
    const decision = await next();
    return exec.name === 'host_qualified_terminal' && decision.kind === 'allow' ? { kind: 'ask', reason: 'HOST ONLY terminal registry fixture' } : decision;
  });
  ctx.commands.register({ name: 'host-terminal-call', description: 'Bounded original terminal registry test.',
    async handler({ agent, signal }) {
      const callId = calls[next++];
      const batch = await ctx.tools.execute({ agent, signal, calls: [{ type: 'tool-call', id: callId, name: 'host_qualified_terminal', arguments: '{}' }] });
      return { kind: 'success', text: JSON.stringify({ terminalProof: true, callId, batch, processStarts: starts }) };
    },
  });
  ctx.commands.register({ name: 'host-terminal-history', description: 'Read actual original qualification events.', handler({ agent }) {
    return { kind: 'success', text: JSON.stringify(agent.session.snapshotEvents().filter(e => e.type === 'approval/asked' || e.type === 'approval/decided' || (e.type === 'command/done' && e.data.text?.startsWith('{"terminalProof":')))) };
  } });
  ctx.on('agent/pre-step', async ({ agent, signal }, nextStep) => {
    if (agent.id !== rootId) return nextStep();
    if (process.env.HARNESS_TERMINAL_RECOVER === '1') await ctx.commands.execute(agent, '/host-terminal-history', [], signal);
    else if (next < 2) await ctx.commands.execute(agent, '/host-terminal-call', [], signal);
    return { kind: 'reject' }; // No provider request or fabricated model event.
  });
  ctx.provide('hostTerminalQualificationReady', { ready: true });
}
