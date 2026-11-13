// Genuine shipped-profile/session reference on the host, not Android feasibility evidence.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { load as loadYaml } from 'js-yaml';

const output = process.argv[2];
const bounded = process.argv[3] === '--no-execution';
if (process.argv.length > (bounded ? 4 : 3)) throw new Error('Unknown reference option');
const patch = fileURLToPath(new URL('../runtime/profile/no-execution.patch.yml', import.meta.url));
if (!output || !path.isAbsolute(output)) throw new Error('Absolute evidence path required');
// Use the existing CLI workspace's declared same-version public SDK dependency.
const resolveCli = createRequire(new URL('../../cli/package.json', import.meta.url));
const { HarnessClient } = await import(resolveCli.resolve('@deepseek-ai/dsh-sdk-client'));
const root = await fs.mkdtemp(path.join(os.tmpdir(), 'android-host-profile-'));
try {
  const workspace = path.join(root, 'workspace');
  const nested = path.join(workspace, 'nested');
  await fs.mkdir(nested, { recursive: true });
  const env = { ...process.env };
  delete env.DEEPSEEK_API_KEY;
  let composition;
  if (bounded) {
    const dsh = path.join(path.dirname(resolveCli.resolve('@deepseek-ai/dsh/package.json')), 'lib/bin.js');
    const dump = spawnSync(process.execPath, [dsh, '--profile', 'sdk-minimal', '--patch', patch, '--dump-config'],
      { env: { ...env, DSH_HOME: path.join(root, 'home') }, cwd: workspace, encoding: 'utf8', timeout: 30000 });
    if (dump.error || dump.status !== 0) throw new Error(`Profile dump failed: ${dump.error ?? dump.stderr}`);
    const rows = loadYaml(dump.stdout, { schema: (await import(resolveCli.resolve('@deepseek-ai/cordis-plugin-include'))).entryListSchema });
    const disabled = ['subprocess', 'pty', 'terminal-bash', 'terminal-pwsh', 'persistent-bash', 'persistent-pwsh', 'tool-fs'];
    for (const id of disabled) {
      if (rows.find(row => row.id === id)?.disabled !== true) throw new Error(`Execution row remains enabled: ${id}`);
    }
    if (!rows.find(row => row.id === 'sdk-jsonrpc-server')?.inject?.includes('sessionPersistence')) {
      throw new Error('Profile qualification must require persistence readiness');
    }
    if (rows.some(row => row.name === '@deepseek-ai/dsh-spill-local')) throw new Error('Unqualified ownership cleanup must not be mounted');
    composition = { disabledRows: disabled, spillLocalMounted: false,
      patchSha256: crypto.createHash('sha256').update(await fs.readFile(patch)).digest('hex'),
      originalProfileWithOverlay: true, requiresPersistenceBeforeSdk: true, securitySandboxClaim: false };
  }
  const options = { profile: 'sdk-minimal', ...(bounded ? { patches: [patch] } : {}), dshHome: path.join(root, 'home'), processCwd: workspace,
    env, initializeTimeoutMs: 30000, requestTimeoutMs: 10000 };
  const initialize = { cwd: workspace, provider: 'deepseek-official', model: 'deepseek-v4-flash' };
  const sessionId = 'android-host-reference-' + crypto.randomUUID();
  const first = new HarnessClient(options);
  let identity;
  try {
    identity = await first.initialize(initialize);
    await first.setWorkingDirectory(sessionId, nested);
  } finally { await first.close(); }
  const second = new HarnessClient(options);
  let recovered;
  try {
    await second.initialize(initialize);
    await second.resumeSession(sessionId);
    recovered = await second.getWorkingDirectory(sessionId);
  } finally { await second.close(); }
  if (recovered !== nested) throw new Error('Persisted working directory did not recover');
  const store = path.join(root, 'home', 'sessions');
  const files = await fs.readdir(store, { recursive: true });
  const persisted = {};
  for (const name of files) {
    if (!name.endsWith('.jsonl')) continue;
    persisted[name] = crypto.createHash('sha256').update(await fs.readFile(path.join(store, name))).digest('hex');
  }
  if (!Object.keys(persisted).length) throw new Error('No real session JSONL files were persisted');
  const result = { schemaVersion: 1, environment: { platform: process.platform, arch: process.arch, node: process.version },
    profile: 'sdk-minimal', ...(bounded ? { composition } : {}), serverInfo: identity.serverInfo, sessionId,
    realProfileInitialized: true, sessionRecoveredAcrossRuntimeRestart: true,
    recoveredNondefaultDirectory: true, persistedJsonlSha256: persisted,
    modelRequestExecuted: false, androidVerified: false, harnessPhoneGatePassed: false };
  await fs.writeFile(output, JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result, null, 2));
} finally { await fs.rm(root, { recursive: true, force: true }); }
