// Original SDK + profile + registry + pipeline + approval; never a model substitute.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { brokerRequest } from './command-wire.mjs';
import { shutdownConfirmed } from './session-diagnostics.mjs';
import { readProcIdentity } from './proc-identity.mjs';
const resolveCli = createRequire(new URL('../../cli/package.json', import.meta.url));
const output = process.argv[2];
if (!output || !path.isAbsolute(output)) throw new Error('Absolute result path required');
let client, stage = 'native-describe';
const clients = new Set();
const observedClients = [];
const diagnostic = {};
const redact = text => String(text).replaceAll(process.env.HARNESS_COMMAND_SECRET, "[redacted]");
process.once('SIGTERM', () => { Promise.allSettled([...clients].map(c => c.close())).finally(() => process.exit(143)); });
async function main() {
  const config = await brokerRequest('describe');
  if (!config.ok || config.callIds.length !== 2) throw new Error('Native fixed configuration unavailable');
  const sessionId = config.sessionId;
  const fields = callId => ({ sessionId, callId, executable: '/system/bin/pwd', arguments: [], cwd: config.cwd });
  const negative = {};
  negative.unapproved = await brokerRequest('execute', fields(config.callIds[1]));
  if (negative.unapproved.code !== 'APPROVAL_REQUIRED') throw new Error('Missing approval was not rejected');
  negative.unauthenticated = await brokerRequest('describe', { token: 'invalid' });
  if (negative.unauthenticated.code !== 'UNAUTHENTICATED') throw new Error('Authentication did not reject');
  negative.malformed = await brokerRequest('describe', { version: 2 });
  if (negative.malformed.ok || negative.malformed.code !== 'MALFORMED_OR_DISCONNECTED') throw new Error('Malformed version not rejected');
  negative.approvalMethod = await brokerRequest('approve');
  if (negative.approvalMethod.code !== 'UNSUPPORTED_ACTION') throw new Error('Agent-visible approval method');
  const env = { ...process.env };
  for (const key of Object.keys(env)) if (/KEY|TOKEN|SECRET|PASSWORD/i.test(key) && key !== 'HARNESS_COMMAND_SECRET' || ['NODE_OPTIONS', 'NODE_PATH'].includes(key)) delete env[key];
  env.HARNESS_COMMAND_SESSION = sessionId;
  env.HARNESS_COMMAND_CALLS = JSON.stringify(config.callIds);
  env.HARNESS_COMMAND_PLUGIN = fileURLToPath(new URL('./command-plugin.mjs', import.meta.url));
  const patch = path.join(path.dirname(output), 'command-proof.generated.patch.yml');
  const template = await fs.readFile(new URL('./profile/command-proof.patch.yml', import.meta.url), 'utf8');
  await fs.writeFile(patch, template.replace('__ANDROID_COMMAND_PLUGIN__', JSON.stringify(env.HARNESS_COMMAND_PLUGIN)));
  const { HarnessClient } = await import(resolveCli.resolve('@deepseek-ai/dsh-sdk-client'));
  const options = { profile: 'sdk-minimal', dshHome: path.join(path.dirname(output), 'home'), processCwd: config.cwd, env,
    patches: [fileURLToPath(new URL('./profile/no-execution.patch.yml', import.meta.url)), patch],
    initializeTimeoutMs: 30000, requestTimeoutMs: 85000, shutdownTimeoutMs: 500, disposeEofGraceMs: 6000, disposeGraceMs: 1000 };
  const initialize = { cwd: config.cwd, provider: 'deepseek-official', model: 'deepseek-v4-flash', approvalRequests: true };
  client = new HarnessClient(options); clients.add(client); observedClients.push(client);
  const notifications = client.subscribe(n => n.method === 'session.event' && n.params.sessionId === sessionId);
  await client.start();
  const outcomes = [];
  client.onRequest(async (method, params) => {
    if (method !== 'approval/request' || params.toolName !== 'android_qualified_pwd' || params.sessionId !== sessionId || !config.callIds.includes(params.callId)) {
      throw new Error('Unexpected original approval request');
    }
    const answer = await brokerRequest('prepare', fields(params.callId));
    if (!answer.ok) throw new Error('Native approval unavailable');
    outcomes.push({ callId: params.callId, outcome: answer.outcome });
    if (answer.outcome === 'allowed-once') {
      negative.duplicate = await brokerRequest('prepare', fields(params.callId));
      if (negative.duplicate.code !== 'DUPLICATE') throw new Error('Duplicate approval request not rejected');
      const mutations = {
        command: { executable: '/system/bin/sh' }, arguments: { arguments: ['-P'] }, cwd: { cwd: '/' },
        session: { sessionId: 'other' }, call: { callId: 'other' }, uid: { uid: 0 },
      };
      for (const [key, change] of Object.entries(mutations)) {
        const result = await brokerRequest('execute', { ...fields(params.callId), ...change });
        if (result.ok || !['REQUEST_CHANGED', 'MALFORMED'].includes(result.code)) throw new Error('Mutation not rejected: ' + key);
        negative[key] = result;
      }
    }
    return { outcome: answer.outcome };
  });
  stage = 'original-profile-start';
  const identity = await client.initialize(initialize);
  if (identity.serverInfo.name !== 'deepseek-harness-sdk-runtime') throw new Error('Wrong original runtime');
  await client.setWorkingDirectory(sessionId, config.cwd);
  for (let index = 0; index < 2; index++) {
    stage = index === 0 ? 'deny-original-tool' : 'approve-original-tool';
    await client.prompt(sessionId, [{ type: 'text', text: 'Run the bounded Android qualification action; no model request.' }]);
    await client.request('session/wait', { sessionId });
  }
  const drain = subscription => {
    const events = [];
    for (let item; (item = subscription.tryNext());) events.push(item.params.event);
    return events;
  };
  const selected = event => event.type === 'approval/asked' || event.type === 'approval/decided'
    || (event.type === 'command/done' && event.data.text?.startsWith('{"callId":'));
  const history = drain(notifications).filter(selected);
  notifications.close();
  diagnostic.history = history; diagnostic.approvalOutcomes = outcomes; diagnostic.negative = negative;
  const calls = history.filter(e => e.type === 'command/done').map(e => JSON.parse(e.data.text));
  if (calls.length !== 2 || !calls[0].batch.results[0].result.isError || calls[1].batch.results[0].result.isError) throw new Error('Expected human Deny then Approve; original outcomes differ');
  if (calls[0].batch.results[0].result.error?.info?.code !== 'APPROVAL_REJECTED') throw new Error('Original denial code missing');
  const commandResult = JSON.parse(calls[1].batch.results[0].result.content[0].text);
  diagnostic.commandResult = commandResult;
  if (commandResult.stdout !== config.cwd + '\n' || commandResult.exitCode !== 0 || typeof commandResult.stderr !== 'string') throw new Error('Real pwd output differs');
  negative.replay = await brokerRequest('execute', fields(config.callIds[1]));
  if (negative.replay.ok || negative.replay.code !== 'USED') throw new Error('Replay did not reject');
  stage = 'persist-original-tool-outcomes';
  await shutdownConfirmed(client); clients.delete(client);
  const second = new HarnessClient({ ...options, env: { ...options.env, HARNESS_COMMAND_RECOVER_ONLY: '1' } }); clients.add(second); observedClients.push(second);
  const recoveredNotifications = second.subscribe(n => n.method === 'session.event' && n.params.sessionId === sessionId);
  await second.initialize(initialize);
  await second.resumeSession(sessionId);
  await second.prompt(sessionId, [{ type: 'text', text: 'Inspect the persisted qualification results without executing a tool.' }]);
  await second.request('session/wait', { sessionId });
  const snapshot = drain(recoveredNotifications).find(e => e.type === 'command/done' && e.data.text?.startsWith('['));
  recoveredNotifications.close();
  if (!snapshot) throw new Error('Original recovery command snapshot missing');
  const recovered = JSON.parse(snapshot.data.text);
  diagnostic.recoveredHistory = recovered;
  if (JSON.stringify(recovered) !== JSON.stringify(history)) throw new Error('Recovered approval/tool outcomes differ');
  await shutdownConfirmed(second); clients.delete(second);
  const hashes = {};
  const store = path.join(options.dshHome, 'sessions');
  for (const name of await fs.readdir(store, { recursive: true })) if (name.endsWith('.jsonl')) hashes[name] = crypto.createHash('sha256').update(await fs.readFile(path.join(store, name))).digest('hex');
  return { schemaVersion: 1, suite: 'original-harness-approved-pwd-v1', node: process.version, platform: process.platform, arch: process.arch,
    kernelIdentity: readProcIdentity(), harnessStarted: true, serverInfo: identity.serverInfo, sessionId,
    runtimeStderr: await Promise.all(observedClients.map(async current => redact(await current.runtimeStderr()))),
    originalRegistryAndPipeline: true, approvalOutcomes: outcomes, commandResult, negative, history, recoveredHistory: recovered,
    sessionRecoveredAcrossRuntimeRestart: true, persistedJsonlSha256: hashes,
    eventStorage: 'original command/done contains canonical tool batch; original approval audit events; no fabricated model tool/call events',
    approvedCommandExecuted: true, modelRequestExecuted: false, gate2Passed: false };
}
try { const result = await main(); await fs.writeFile(output, JSON.stringify(result)); }
catch (error) { await fs.writeFile(output, JSON.stringify({ schemaVersion: 1, stage, failure: redact(error.stack ?? error), diagnostic, runtimeStderr: await Promise.all(observedClients.map(async current => redact(await current.runtimeStderr()))), gate2Passed: false })); console.error(redact(error.stack ?? error)); process.exitCode = 1; }
finally { await Promise.allSettled([...clients].map(c => c.close())); }
