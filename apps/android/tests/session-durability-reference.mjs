// Real Linux permission failure in original Harness persistence, never Android compatibility evidence.
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { shutdownConfirmed } from '../runtime/session-diagnostics.mjs';

if (process.platform !== 'linux' || process.getuid() === 0) throw new Error('Non-root Linux host required');
const output = process.argv[2];
if (!output || !path.isAbsolute(output)) throw new Error('Absolute result path required');
const resolveCli = createRequire(new URL('../../cli/package.json', import.meta.url));
const { HarnessClient } = await import(resolveCli.resolve('@deepseek-ai/dsh-sdk-client'));
const root = await fs.mkdtemp(path.join(os.tmpdir(), 'harness-durability-reference-'));
try {
  async function scenario(strict) {
    const base = path.join(root, strict ? 'confirmed' : 'plain');
    const workspace = path.join(base, 'workspace');
    const initial = path.join(workspace, 'initial');
    const changed = path.join(workspace, 'changed');
    await fs.mkdir(initial, { recursive: true }); await fs.mkdir(changed);
    const env = { PATH: process.env.PATH };
    const options = { profile: 'sdk-minimal', dshHome: path.join(base, 'home'), processCwd: workspace,
      patches: [fileURLToPath(new URL('../runtime/profile/no-execution.patch.yml', import.meta.url))],
      env, requestTimeoutMs: 10000 };
    const initialize = { cwd: workspace, provider: 'deepseek-official', model: 'deepseek-v4-flash' };
    const id = 'durability-reference';
    const first = new HarnessClient(options);
    try { await first.initialize(initialize); await first.setWorkingDirectory(id, initial); await shutdownConfirmed(first); }
    finally { await first.close(); }
    const store = path.join(base, 'home/sessions');
    const logs = (await fs.readdir(store, { recursive: true })).filter(name => name.endsWith('.jsonl')).map(name => path.join(store,name));
    if (logs.length !== 1) throw new Error('Expected one original session file');
    const second = new HarnessClient(options);
    let error; let phase = 'set-working-directory';
    try {
      await second.initialize(initialize); await second.resumeSession(id);
      for (const log of logs) await fs.chmod(log, 0o400);
      await second.setWorkingDirectory(id, changed);
      phase = 'shutdown';
      if (strict) await shutdownConfirmed(second); else await second.close();
    } catch (failure) { error = { phase, name: failure.name, message: failure.message }; }
    finally {
      for (const log of logs) await fs.chmod(log, 0o600);
      await second.close();
    }
    const stderr = await second.runtimeStderr();
    return { rejected: Boolean(error), error: error ?? null, stderr };
  }
  const plain = await scenario(false);
  const confirmed = await scenario(true);
  if (plain.rejected || !confirmed.rejected || confirmed.error.phase !== 'shutdown') throw new Error('Expected plain-close suppression and confirmed-shutdown rejection');
  if (!plain.stderr.includes('EACCES') || !confirmed.stderr.includes('EACCES')) throw new Error('Actual filesystem denial missing from retained diagnostics');
  const result = { schemaVersion: 1, platform: process.platform, node: process.version,
    originalProfile: 'sdk-minimal', fault: 'Real temporary JSONL file made read-only for non-root process',
    plainClose: plain, confirmedShutdown: confirmed, androidReproduced: false, androidRootCauseEstablished: false };
  await fs.writeFile(output, JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result, null, 2));
} finally { await fs.rm(root, { recursive: true, force: true }); }
