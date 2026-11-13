// Real original profile + registry + native-approved fixed PTY; no external model request.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { terminalRequest } from './terminal-wire.mjs';
import { relayTerminalApproval } from './terminal-authorization.mjs';
import { readProcIdentity } from './proc-identity.mjs';
import { shutdownConfirmed } from './session-diagnostics.mjs';
const cli = createRequire(new URL('../../cli/package.json', import.meta.url));
const terminal = createRequire(new URL('../../../packages/terminal/terminal-bash/package.json', import.meta.url));
const { HarnessClient } = await import(cli.resolve('@deepseek-ai/dsh-sdk-client'));
const output = process.argv[2], clients = new Set(), observed = [], diagnostic = {};
let stage = 'native-describe';
const redact = text => String(text).replaceAll(process.env.HARNESS_TERMINAL_SECRET, '[redacted]');
process.once('SIGTERM', () => { Promise.allSettled([...clients].map(client => client.close())).finally(() => process.exit(143)); });
async function main() {
  if (!output || !path.isAbsolute(output)) throw new Error('Absolute result path required');
  const native = await terminalRequest('describe');
  if (!native.ok || native.callIds.length !== 2) throw new Error('Native terminal configuration unavailable');
  const configuration = native.configuration, sessionId = native.sessionId;
  const negative = {}, outcomes = [];
  const field = { sessionId, ownerId: sessionId, callId: native.callIds[1], terminalId: 'pty-2', backend: configuration.backend,
    executable: configuration.executable, arguments: configuration.arguments, cwd: configuration.cwd, columns: 80, rows: 24 };
  negative.unapproved = await terminalRequest('consume', field);
  negative.unauthenticated = await terminalRequest('describe', { token: 'invalid' });
  negative.agentApproval = await terminalRequest('approve');
  if (negative.unapproved.code !== 'APPROVAL_REQUIRED' || negative.unauthenticated.code !== 'UNAUTHENTICATED'
    || negative.agentApproval.code !== 'UNSUPPORTED_ACTION') throw new Error('Native initial denial checks failed');
  const plugin = fileURLToPath(new URL('./terminal-plugin.mjs', import.meta.url));
  const patch = path.join(path.dirname(output), 'terminal.generated.patch.yml');
  await fs.writeFile(patch, `- insert:\n    - id: android-terminal-service\n      name: ${JSON.stringify(terminal.resolve('@deepseek-ai/dsh-terminal'))}\n    - id: android-terminal-approval\n      name: '@deepseek-ai/dsh-user-approval'\n      config: {policy: ask}\n    - id: android-terminal-commands\n      name: '@deepseek-ai/dsh-commands'\n    - id: android-terminal-qualification\n      name: ${JSON.stringify(plugin)}\n- id: sdk-jsonrpc-server\n  inject: [sdkAppStartup, loader, sessionPersistence, approval, commands, androidTerminalQualificationReady]\n`);
  const env = { ...process.env };
  for (const key of Object.keys(env)) if ((/KEY|TOKEN|SECRET|PASSWORD/i.test(key) && key !== 'HARNESS_TERMINAL_SECRET') || ['NODE_OPTIONS', 'NODE_PATH'].includes(key)) delete env[key];
  const options = { profile: 'sdk-minimal', patches: [fileURLToPath(new URL('./profile/no-execution.patch.yml', import.meta.url)), patch],
    env, dshHome: path.join(path.dirname(output), 'home'), processCwd: configuration.cwd,
    initializeTimeoutMs: 30000, requestTimeoutMs: 85000, shutdownTimeoutMs: 500, disposeEofGraceMs: 6000 };
  const initialize = { cwd: configuration.cwd, provider: 'deepseek-official', model: 'deepseek-v4-flash', approvalRequests: true };
  const first = new HarnessClient(options); clients.add(first); observed.push(first);
  await first.start();
  let allowedFields;
  first.onRequest(async (method, params) => {
    if (method !== 'approval/request') throw new Error('Unexpected SDK request');
    const answer = await relayTerminalApproval(params, { configuration, callIds: native.callIds, toolName: 'android_qualified_terminal',
      requestNative: async (action, fields) => {
        const reply = await terminalRequest(action, fields);
        if (!reply.ok) diagnostic.nativeApprovalFailure = reply;
        if (reply.ok && reply.outcome === 'allowed-once') {
          allowedFields = fields;
          negative.duplicate = await terminalRequest('prepare', fields);
          if (negative.duplicate.code !== 'DUPLICATE') throw new Error('Duplicate native prompt accepted');
          for (const [key, change] of Object.entries({ terminal: { terminalId: 'pty-999' }, owner: { ownerId: 'other' },
            executable: { executable: '/system/bin/sh' }, arguments: { arguments: ['--wait'] }, cwd: { cwd: '/' },
            columns: { columns: 81 }, rows: { rows: 25 }, session: { sessionId: 'other' }, call: { callId: 'other' }, uid: { uid: 0 } })) {
            const result = await terminalRequest('consume', { ...fields, ...change });
            if (result.ok || !['REQUEST_CHANGED', 'MALFORMED', 'MALFORMED_OR_DISCONNECTED'].includes(result.code)) throw new Error('Native mutation accepted: ' + key);
            negative[key] = result;
          }
        }
        return reply;
      } });
    outcomes.push({ callId: params.callId, outcome: answer.outcome });
    return answer;
  });
  stage = 'original-profile';
  const identity = await first.initialize(initialize);
  if (identity.serverInfo.name !== 'deepseek-harness-sdk-runtime') throw new Error('Unexpected original runtime identity');
  await first.setWorkingDirectory(sessionId, configuration.cwd);
  const events = first.subscribe(e => e.method === 'session.event' && e.params.sessionId === sessionId);
  for (let index = 0; index < 2; index++) {
    stage = index ? 'approved-original-terminal' : 'denied-original-terminal';
    await first.prompt(sessionId, [{ type: 'text', text: 'Run bounded original terminal qualification without a model request.' }]);
    await first.request('session/wait', { sessionId });
  }
  const history = [];
  for (let item; (item = events.tryNext());) {
    const event = item.params.event;
    if (event.type === 'approval/asked' || event.type === 'approval/decided' || (event.type === 'command/done' && event.data.text?.startsWith('{"terminalProof":'))) history.push(event);
  }
  events.close(); diagnostic.history = history; diagnostic.outcomes = outcomes; diagnostic.negative = negative;
  const commands = history.filter(e => e.type === 'command/done').map(e => JSON.parse(e.data.text));
  if (commands.length !== 2 || commands[0].processStarts !== 0 || commands[0].batch.results[0].result.error?.info?.code !== 'TERMINAL_APPROVAL_REJECTED'
    || commands[1].batch.results[0].result.isError || outcomes[0]?.outcome !== 'rejected' || outcomes[1]?.outcome !== 'allowed-once') throw new Error('Expected native Deny then Approve with original outcomes');
  const report = JSON.parse(commands[1].batch.results[0].result.content[0].text);
  if (report.starts !== 1 || report.concurrentConsumers !== 2 || report.concurrentRejections !== 1 || !report.originalTerminalRegistry || !report.ownerActivityDrained) throw new Error('Original terminal result differs');
  if (configuration.qualification === 'lifecycle' && (report.qualification !== 'lifecycle'
    || report.lifecycle?.timeout?.waitReason !== 'timeout' || report.lifecycle?.timeout?.sessionStatus?.kind !== 'running'
    || !report.lifecycle?.explicitCancellation || !report.lifecycle?.childNoLongerObservable
    || report.result.sessionStatus.signal !== 'SIGINT' || report.result.sessionStatus.exitCode !== null)) {
    throw new Error('Original terminal lifecycle evidence differs');
  }
  negative.replay = await terminalRequest('consume', allowedFields);
  if (negative.replay.ok || !['USED', 'CLOSED'].includes(negative.replay.code)) throw new Error('Native allocation replay accepted');
  stage = 'original-session-recovery';
  await shutdownConfirmed(first); clients.delete(first);
  const second = new HarnessClient({ ...options, env: { ...env, HARNESS_TERMINAL_RECOVER_ONLY: '1' } }); clients.add(second); observed.push(second);
  await second.initialize(initialize); await second.resumeSession(sessionId);
  const recoveredEvents = second.subscribe(e => e.method === 'session.event' && e.params.sessionId === sessionId);
  await second.prompt(sessionId, [{ type: 'text', text: 'Read actual persisted original terminal records.' }]);
  await second.request('session/wait', { sessionId });
  let recovered;
  for (let item; (item = recoveredEvents.tryNext());) if (item.params.event.type === 'command/done' && item.params.event.data.text?.startsWith('[')) recovered = JSON.parse(item.params.event.data.text);
  recoveredEvents.close();
  if (JSON.stringify(recovered) !== JSON.stringify(history)) throw new Error('Recovered original terminal records differ');
  await shutdownConfirmed(second); clients.delete(second);
  const hashes = {};
  const store = path.join(options.dshHome, 'sessions');
  for (const name of await fs.readdir(store, { recursive: true })) if (name.endsWith('.jsonl')) hashes[name] = crypto.createHash('sha256').update(await fs.readFile(path.join(store, name))).digest('hex');
  return { schemaVersion: 1, suite: 'original-harness-native-terminal-v1', node: process.version, platform: process.platform, arch: process.arch,
    kernelIdentity: readProcIdentity(), harnessStarted: true, serverInfo: identity.serverInfo, sessionId, report, approvalOutcomes: outcomes,
    negative, history, recoveredHistory: recovered, persistedJsonlSha256: hashes, sessionRecoveredAcrossRuntimeRestart: true,
    appRestartVerified: false, modelRequestExecuted: false, generalShellProviderImplemented: false, gate3Passed: false,
    runtimeStderr: await Promise.all(observed.map(async client => redact(await client.runtimeStderr()))) };
}
try { await fs.writeFile(output, JSON.stringify(await main())); }
catch (error) { await fs.writeFile(output, JSON.stringify({ schemaVersion: 1, suite: 'original-harness-native-terminal-v1', stage,
  failure: redact(error.stack ?? error), diagnostic, gate3Passed: false, runtimeStderr: await Promise.all(observed.map(async client => redact(await client.runtimeStderr()))) })); console.error(redact(error.stack ?? error)); process.exitCode = 1; }
finally { await Promise.allSettled([...clients].map(client => client.close())); }
