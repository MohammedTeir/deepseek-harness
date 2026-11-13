// Original dsh profile/session proof. No replacement agent, model response or tool execution.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { readProcIdentity } from './proc-identity.mjs';
import { describeFailure, storagePrerequisites, sessionInventory, shutdownConfirmed } from './session-diagnostics.mjs';

const resolveCli = createRequire(new URL('../../cli/package.json', import.meta.url));
const output = process.argv[2];
if (!output || !path.isAbsolute(output)) throw new Error('Absolute result path required');
let stage = 'sdk-import';
let harnessStarted = false;
let cancelled = false;
const clients = new Set();
const diagnostic = { shutdownAcknowledgements: 0 };
const observedClients = [];
const store = path.join(path.dirname(output), 'home/sessions');
async function closeClients() {
  const results = await Promise.allSettled([...clients].map(client => client.close()));
  const failures = results.filter(result => result.status === 'rejected');
  if (failures.length) throw new AggregateError(failures.map(result => result.reason), 'SDK runtime cleanup failed');
}
process.once('SIGTERM', () => {
  cancelled = true;
  closeClients().then(() => process.exit(143), error => { console.error(error); process.exitCode = 1; });
});
async function main() {
  stage = 'native-internal-loader';
  const builtin = resolveCli('node-addon-require-builtin');
  const internal = builtin.requireBuiltin('internal/modules/esm/loader');
  if (typeof internal.getOrInitializeCascadedLoader !== 'function') throw new Error('Original internal loader API unavailable');
  const binding = builtin.getBindingInfo();
  if (binding.product !== 'require-builtin' || binding.backend !== 'napi' || binding.abi !== 'napi-v9') {
    throw new Error('Unexpected original internal-loader binding');
  }
  const { HarnessClient } = await import(resolveCli.resolve('@deepseek-ai/dsh-sdk-client'));
  const identityKernel = readProcIdentity();
  const root = path.dirname(output);
  const workspace = path.join(root, 'workspace');
  const nested = path.join(workspace, 'nested');
  await fs.mkdir(nested, { recursive: true });
  const env = { ...process.env };
  for (const key of Object.keys(env)) {
    if (/KEY|SECRET|TOKEN|PASSWORD/i.test(key) || ['NODE_OPTIONS', 'NODE_PATH'].includes(key)) delete env[key];
  }
  const options = { profile: 'sdk-minimal', dshHome: path.join(root, 'home'), processCwd: workspace,
    patches: [fileURLToPath(new URL('./profile/no-execution.patch.yml', import.meta.url))],
    env, initializeTimeoutMs: 30000, requestTimeoutMs: 10000,
    shutdownTimeoutMs: 500, disposeEofGraceMs: 6000, disposeGraceMs: 1000 };
  const initialize = { cwd: workspace, provider: 'deepseek-official', model: 'deepseek-v4-flash' };
  const sessionId = 'android-profile-' + crypto.randomUUID();
  const first = new HarnessClient(options);
  clients.add(first);
  observedClients.push(first);
  stage = 'profile-initialize';
  const identity = await first.initialize(initialize);
  if (cancelled) throw new Error('Cancelled');
  if (identity.serverInfo?.name !== 'deepseek-harness-sdk-runtime') throw new Error('Unexpected original SDK runtime');
  harnessStarted = true;
  diagnostic.serverInfo = identity.serverInfo;
  diagnostic.node = process.version;
  diagnostic.platform = process.platform;
  diagnostic.arch = process.arch;
  diagnostic.kernelIdentity = identityKernel;
  stage = 'storage-prerequisites';
  diagnostic.storage = await storagePrerequisites(root);
  let previousRunSessionRecovered = false;
  const checkpoint = path.join(root, 'session-checkpoint.json');
  let saved;
  try { saved = JSON.parse(await fs.readFile(checkpoint, 'utf8')); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  if (saved) {
    stage = 'previous-session-recovery';
    if (typeof saved.sessionId !== 'string' || !/^android-profile-[a-z0-9-]+$/.test(saved.sessionId) || saved.cwd !== nested) {
      throw new Error('Invalid private session checkpoint');
    }
    await first.resumeSession(saved.sessionId);
    if (await first.getWorkingDirectory(saved.sessionId) !== nested) throw new Error('Previous session did not recover');
    previousRunSessionRecovered = true;
  }
  stage = 'session-create';
  await first.setWorkingDirectory(sessionId, nested);
  if (await first.getWorkingDirectory(sessionId) !== nested) throw new Error('Live working directory differs');
  stage = 'first-shutdown';
  await shutdownConfirmed(first);
  diagnostic.shutdownAcknowledgements++;
  diagnostic.afterFirstShutdown = await sessionInventory(store);
  clients.delete(first);
  const second = new HarnessClient(options);
  clients.add(second);
  observedClients.push(second);
  stage = 'profile-restart';
  await second.initialize(initialize);
  diagnostic.beforeResume = await sessionInventory(store);
  stage = 'session-failure-integrity';
  const persistedBeforeFailure = await sessionInventory(store);
  const filesBeforeFailure = {};
  for (const name of await fs.readdir(store, { recursive: true })) {
    if (name.endsWith('.jsonl')) filesBeforeFailure[name] = crypto.createHash('sha256').update(await fs.readFile(path.join(store, name))).digest('hex');
  }
  let missingRejected = false;
  try { await second.resumeSession('android-missing-' + crypto.randomUUID()); }
  catch (error) {
    if (error.name !== 'JsonRpcResponseError' || !String(error.message).includes('not found')) throw error;
    missingRejected = true;
    diagnostic.missingSessionFailure = describeFailure(error);
  }
  if (!missingRejected) throw new Error('Missing original session was accepted');
  for (const [name, digest] of Object.entries(filesBeforeFailure)) {
    if (crypto.createHash('sha256').update(await fs.readFile(path.join(store, name))).digest('hex') !== digest) {
      throw new Error('Committed JSONL changed after rejected session recovery');
    }
  }
  diagnostic.sessionIntegrityAfterRejectedRecovery = true;
  diagnostic.persistedBeforeRejectedRecovery = persistedBeforeFailure;
  stage = 'session-recovery';
  await second.resumeSession(sessionId);
  const recovered = await second.getWorkingDirectory(sessionId);
  if (recovered !== nested) throw new Error('Original session working directory did not recover');
  stage = 'second-shutdown';
  await shutdownConfirmed(second);
  diagnostic.shutdownAcknowledgements++;
  clients.delete(second);
  const persisted = {};
  for (const name of await fs.readdir(store, { recursive: true })) {
    if (name.endsWith('.jsonl')) persisted[name] = crypto.createHash('sha256').update(await fs.readFile(path.join(store,name))).digest('hex');
  }
  if (!Object.keys(persisted).length) throw new Error('No original session JSONL persisted');
  if (cancelled) throw new Error('Cancelled');
  await fs.writeFile(checkpoint + '.pending', JSON.stringify({ sessionId, cwd: nested }), { mode: 0o600 });
  await fs.rename(checkpoint + '.pending', checkpoint);
  return { schemaVersion: 1, node: process.version, platform: process.platform, arch: process.arch,
    persistenceDiagnostics: diagnostic,
    nativeInternalLoader: { product: binding.product, backend: binding.backend, abi: binding.abi, mode: binding.mode },
    pid: process.pid, kernelIdentity: identityKernel, execPath: process.execPath, profile: 'sdk-minimal', serverInfo: identity.serverInfo,
    harnessStarted: true, previousRunSessionRecovered, appRestartVerified: false, sessionRecoveredAcrossRuntimeRestart: true, recoveredNondefaultDirectory: true,
    persistedJsonlSha256: persisted, modelRequestExecuted: false, approvedCommandExecuted: false, gate2Passed: false };
}
let result;
try { result = await main(); }
catch (error) {
  console.error(error.stack ?? String(error));
  result = { schemaVersion: 1, stage, failure: error.message, error: describeFailure(error),
    storageStage: error.storageStage ?? null, persistenceDiagnostics: diagnostic, harnessStarted, gate2Passed: false };
  process.exitCode = 1;
} finally {
  try { await closeClients(); }
  catch (error) {
    console.error(error);
    if (process.exitCode) result.cleanupFailure = describeFailure(error);
    else result = { schemaVersion: 1, stage: 'cleanup', failure: error.message, error: describeFailure(error), harnessStarted, gate2Passed: false };
    process.exitCode = 1;
  }
}
diagnostic.runtimeStderr = (await Promise.all(observedClients.map(client => client.runtimeStderr())))
  .map(text => text.slice(-12288));
if (process.exitCode) {
  try { result.finalSessionInventory = await sessionInventory(store); }
  catch (error) { result.inventoryFailure = describeFailure(error); }
}
await fs.writeFile(output + '.pending', JSON.stringify(result), { mode: 0o600 });
await fs.rename(output + '.pending', output);
