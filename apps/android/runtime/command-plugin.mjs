// Bounded native qualification plugin, mounted into the original sdk-minimal profile.
import { brokerRequest } from './command-wire.mjs';
import { withFixedPwdCall } from './android-subprocess.mjs';
import { createRequire } from 'node:module';
const resolveCli = createRequire(new URL('../../cli/package.json', import.meta.url));
const { defineTool } = await import(resolveCli.resolve('@deepseek-ai/dsh-tools'));
export const name = 'android-command-qualification';
export const inject = ['tools', 'approval', 'commands', 'subprocess'];
const tool = 'android_qualified_pwd';
export function apply(ctx) {
  const sessionId = process.env.HARNESS_COMMAND_SESSION;
  const callIds = JSON.parse(process.env.HARNESS_COMMAND_CALLS);
  let nextCall = 0;
  ctx.tools.register(defineTool({
    name: tool, description: 'Qualification only: native approved fixed pwd, no arguments.', parameters: {},
    output: {
      schema: { type: 'object', additionalProperties: false, properties: {
        subprocessProvider: { type: 'string', required: true },
        stdout: { type: 'string', required: true }, stderr: { type: 'string', required: true },
        exitCode: { type: 'integer', required: true }, cwd: { type: 'string', required: true },
        nativeConcurrentConsumers: { type: 'integer', required: true }, nativeConcurrentRejections: { type: 'integer', required: true },
      } },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    async execute(_args, exec) {
      if (!exec.agent || exec.agent.id !== sessionId) throw new Error('Qualification session mismatch');
      const config = await brokerRequest('describe', {}, exec.signal);
      const fields = { sessionId, callId: exec.callId, executable: '/system/bin/pwd', arguments: [], cwd: config.cwd };
      return withFixedPwdCall(fields, async () => {
        const executable = await ctx.subprocess.resolveExecutable('/system/bin/pwd', undefined, exec.signal);
        const spec = { argv: [executable], cwd: config.cwd, stdio: { stdin: 'ignore', stdout: { maxBytes: 65536 }, stderr: { maxBytes: 65536 } }, graceMs: 2000, signal: exec.signal };
        const handles = [ctx.subprocess.spawn(spec), ctx.subprocess.spawn(spec)];
        const attempts = await Promise.allSettled(handles.map(handle => handle.done));
        await Promise.all(handles.map(handle => handle.waitForExit()));
        const winners = attempts.flatMap((result, index) => result.status === 'fulfilled' ? [{ result: result.value, handle: handles[index] }] : []);
        const rejected = attempts.filter(result => result.status === 'rejected' && result.reason.nativeCode === 'USED');
        if (winners.length !== 1 || rejected.length !== 1) throw new Error('Original subprocess/native one-shot invariant failed');
        const winner = winners[0];
        return { stdout: winner.handle.collected.stdout.readFrom(0).text, stderr: winner.handle.collected.stderr.readFrom(0).text,
          exitCode: winner.result.exitCode, cwd: config.cwd, nativeConcurrentConsumers: handles.length, nativeConcurrentRejections: rejected.length,
          subprocessProvider: 'android-fixed-pwd-v1' };
      });
    },
  }));
  // The original pipeline resolves ask through ApprovalService, including its audit pair.
  ctx.on('tools/pre-execute', async (exec, next) => {
    const decision = await next();
    if (exec.name !== tool || decision.kind !== 'allow') return decision;
    return { kind: 'ask', reason: 'Native fixed pwd qualification; exact request is rendered by Android.' };
  });
  ctx.commands.register({
    name: 'android-proof-call', description: 'Run the fixed registered tool in the open qualification turn.',
    async handler({ agent, signal }) {
      if (agent.id !== sessionId || nextCall >= callIds.length) return { kind: 'error', text: 'Qualification budget exhausted' };
      const callId = callIds[nextCall++];
      const batch = await ctx.tools.execute({ agent, signal,
        calls: [{ type: 'tool-call', id: callId, name: tool, arguments: '{}' }] });
      if (signal.aborted) {
        const cancelled = await brokerRequest('cancel', { sessionId, callId, executable: '/system/bin/pwd', arguments: [], cwd: process.cwd() });
        if (!cancelled.ok) throw new Error('Native cancellation not acknowledged');
      }
      // Preserve the actual canonical pipeline result in the original command lifecycle.
      return { kind: 'success', text: JSON.stringify({ callId, batch }) };
    },
  });
  ctx.commands.register({
    name: 'android-proof-history', description: 'Inspect this qualification session without changing its history.',
    handler({ agent }) {
      const events = agent.session.snapshotEvents().filter(event =>
        event.type === 'approval/asked' || event.type === 'approval/decided'
        || (event.type === 'command/done' && event.data.text?.startsWith('{"callId":')));
      return { kind: 'success', text: JSON.stringify(events) };
    },
  });
  ctx.on('agent/pre-step', async ({ agent, signal }, next) => {
    if (agent.id !== sessionId) return next();
    if (process.env.HARNESS_COMMAND_RECOVER_ONLY === '1') {
      await ctx.commands.execute(agent, '/android-proof-history', [], signal);
      return { kind: 'reject' };
    }
    if (nextCall < callIds.length) await ctx.commands.execute(agent, '/android-proof-call', [], signal);
    // No provider request, assistant message or fabricated model-step events.
    return { kind: 'reject' };
  });
  ctx.provide('androidCommandQualificationReady', { ready: true });
}
