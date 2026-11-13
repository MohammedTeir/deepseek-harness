// Bounded native qualification plugin, mounted into the original sdk-minimal profile.
import { brokerRequest } from './command-wire.mjs';
import { createRequire } from 'node:module';
const resolveCli = createRequire(new URL('../../cli/package.json', import.meta.url));
const { defineTool } = await import(resolveCli.resolve('@deepseek-ai/dsh-tools'));
export const name = 'android-command-qualification';
export const inject = ['tools', 'approval', 'commands'];
const tool = 'android_qualified_pwd';
export function apply(ctx) {
  const sessionId = process.env.HARNESS_COMMAND_SESSION;
  const callIds = JSON.parse(process.env.HARNESS_COMMAND_CALLS);
  let nextCall = 0;
  ctx.tools.register(defineTool({
    name: tool, description: 'Qualification only: native approved fixed pwd, no arguments.', parameters: {},
    output: {
      schema: { type: 'object', additionalProperties: false, properties: {
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
      const settled = await Promise.allSettled([brokerRequest('execute', fields, exec.signal), brokerRequest('execute', fields, exec.signal)]);
      const failures = settled.filter(item => item.status === 'rejected');
      if (failures.length) throw new AggregateError(failures.map(item => item.reason), 'Native execution communication failed after cancellation');
      const attempts = settled.map(item => item.value);
      const winners = attempts.filter(result => result.ok);
      const rejected = attempts.filter(result => !result.ok && result.code === 'USED');
      if (winners.length !== 1 || rejected.length !== 1) throw new Error('Native concurrent one-shot invariant failed: ' + JSON.stringify(attempts));
      return { ...winners[0].result, nativeConcurrentConsumers: attempts.length, nativeConcurrentRejections: rejected.length };
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
