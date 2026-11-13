// Genuine original services and real PTY. Native transport is an explicitly labelled host test double.
import assert from 'node:assert/strict';
import { AsyncLocalStorage } from 'node:async_hooks';
import { createRequire } from 'node:module';
import { createFixtureTerminalBackend } from '../runtime/node-pty-proof/terminal-backend.ts';
import { createFixtureTerminalHandle } from '../runtime/node-pty-proof/terminal-handle.ts';
import { createTerminalAllocationAuthority } from '../runtime/terminal-authorization.mjs';
const cli = createRequire(new URL('../../cli/package.json', import.meta.url));
const ptyResolve = createRequire(new URL('../../../packages/subprocess/subprocess-local/package.json', import.meta.url));
const { defineTool } = await import(cli.resolve('@deepseek-ai/dsh-tools'));
const pty = ptyResolve('node-pty'), scope = new AsyncLocalStorage();
export const name = 'host-terminal-allocation-authority';
export const inject = ['agents', 'tools', 'commands', 'terminals', 'approval'];
export function apply(ctx) {
  const sessionId = process.env.HARNESS_TERMINAL_SESSION, cwd = process.env.HARNESS_TERMINAL_WORKSPACE;
  const executable = process.env.HARNESS_NODE_PTY_FIXTURE;
  const callIds = ['deny-terminal', 'allow-terminal'], toolName = 'host_qualified_terminal';
  const configuration = { sessionId, ownerId: sessionId, backend: 'android-fixed-pty-v1', executable,
    arguments: ['--tty-child'], cwd, columns: 80, rows: 24, uid: process.getuid() };
  let next = 0, starts = 0, consumes = 0, revocations = 0;
  const receipts = [];
  // This callback is a transport contract double, NOT the Android broker or its security evidence.
  const requestNative = async (action, fields) => {
    if (action === 'cancel') { revocations++; return { ok: true }; }
    assert.equal(action, 'consume'); consumes++; receipts.push(fields);
    return { ok: true, allocation: { ...fields, uid: configuration.uid } };
  };
  const backend = createFixtureTerminalBackend({ startupMs: 5000,
    async authorize(spec, signal) {
      const authority = scope.getStore();
      if (!authority) throw new Error('No host tool authority');
      await authority.authorize(spec, signal);
    },
    createHandle(spec, ownerSignal) {
      const authority = scope.getStore(); authority.take(spec);
      assert.throws(() => authority.take(spec), { code: 'TERMINAL_PERMIT_USED' });
      starts++;
      return createFixtureTerminalHandle(pty, { fixtureExecutable: executable, cwd: spec.cwd,
        role: '--tty-child', graceMs: 100, ownerSignal });
    },
  });
  ctx.terminals.registerBackend(backend);
  ctx.tools.register(defineTool({ name: toolName, description: 'Host-only original allocation-approval integration.', parameters: {},
    output: { schema: { type: 'object', additionalProperties: false, properties: { report: { type: 'string', required: true } } },
      render: (_args, value) => [{ type: 'text', text: value.report }] },
    async execute(_args, exec) {
      const authority = createTerminalAllocationAuthority({ ctx, exec, configuration, callIds, toolName,
        registryType: backend.type, requestNative });
      let terminal;
      try {
        terminal = await scope.run(authority, () => ctx.terminals.spawn(exec.agent, { type: backend.type, cwd }, exec.signal));
        const operation = ctx.terminals.startSend(exec.agent, terminal.sessionId, { text: 'pty-input', submit: true });
        const result = await operation.done;
        assert.deepEqual(result.sessionStatus, { kind: 'exited', exitCode: 0, signal: null });
        assert.match(result.viewport, /TTY-INPUT:pty-input ROWS:40 COLS:100/);
        await ctx.terminals.kill(exec.agent, terminal.sessionId); terminal = undefined;
        assert.equal(ctx.terminals.hasOwnerActivity(exec.agent), false);
        assert.equal(consumes, 1); assert.equal(starts, 1);
        return { report: JSON.stringify({ originalTerminalRegistry: true, genuineAgentOwners: 1, result,
          starts, consumes, receipts, nativeWireIsTestDouble: true, nativeHumanApprovalVerified: false }) };
      } finally {
        try { if (terminal) await ctx.terminals.kill(exec.agent, terminal.sessionId); }
        finally { await authority.close(); }
      }
    },
  }));
  ctx.commands.register({ name: 'host-terminal-call', description: 'Run fixed original tool context.', async handler({ agent, signal }) {
    const callId = callIds[next++];
    const batch = await ctx.tools.execute({ agent, signal, calls: [{ type: 'tool-call', id: callId, name: toolName, arguments: '{}' }] });
    return { kind: 'success', text: JSON.stringify({ terminalProof: true, callId, batch, processStarts: starts }) };
  } });
  ctx.commands.register({ name: 'host-terminal-history', description: 'Read original records.', handler({ agent }) {
    return { kind: 'success', text: JSON.stringify(agent.session.snapshotEvents().filter(e => e.type === 'approval/asked'
      || e.type === 'approval/decided' || (e.type === 'command/done' && e.data.text?.startsWith('{"terminalProof":')))) };
  } });
  ctx.on('agent/pre-step', async ({ agent, signal }, nextStep) => {
    if (agent.id !== sessionId) return nextStep();
    await ctx.commands.execute(agent, process.env.HARNESS_TERMINAL_RECOVER === '1' ? '/host-terminal-history' : '/host-terminal-call', [], signal);
    return { kind: 'reject' }; // No model request or fabricated response.
  });
  ctx.provide('hostTerminalQualificationReady', { ready: true });
}
