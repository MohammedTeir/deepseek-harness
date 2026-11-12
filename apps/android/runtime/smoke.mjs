// Deterministic embedded-runtime probe. No model, credentials, or Harness loop is simulated.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { Worker } from 'node:worker_threads';
import { DatabaseSync } from 'node:sqlite';
import dns from 'node:dns/promises';
import https from 'node:https';

let stage = 'startup';

async function main() {
  const output = process.argv[2];
  if (!output || !path.isAbsolute(output)) throw new Error('An absolute result path is required');
  stage = 'sqlite';
  const sqlite = new DatabaseSync(':memory:');
  try {
    if (sqlite.prepare('select 42 as answer').get().answer !== 42) throw new Error('SQLite result mismatch');
  } finally { sqlite.close(); }
  stage = 'worker';
  const worker = new Worker("require('node:worker_threads').parentPort.postMessage(42)", { eval: true });
  try {
    const answer = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Worker timeout')), 5000);
      worker.once('message', value => { clearTimeout(timer); resolve(value); });
      worker.once('error', error => { clearTimeout(timer); reject(error); });
    });
    if (answer !== 42) throw new Error('Worker result mismatch');
  } finally { await worker.terminate(); }
  stage = 'native-lock';
  let lock = false;
  if (process.platform === 'android') {
    const { tryLockExclusive } = await import('./harness-flock.mjs');
    const file = path.join(path.dirname(output), 'probe.lock');
    let first;
    let second;
    const acquire = tryLockExclusive;
    try {
      first = fs.openSync(file, 'a');
      second = fs.openSync(file, 'a');
      await acquire(first);
      let rejected = false;
      try { await acquire(second); }
      catch (error) {
        if (!['EAGAIN', 'EWOULDBLOCK'].includes(error.code) || error.syscall !== 'flock') throw error;
        rejected = true;
      }
      if (!rejected) throw new Error('Native lock contention was not rejected');
      fs.closeSync(first);
      first = undefined;
      await acquire(second);
      lock = true;
    } finally {
      if (first !== undefined) fs.closeSync(first);
      if (second !== undefined) fs.closeSync(second);
    }
  }
  stage = 'esm';
  const esm = await import('node:path');
  if (esm.basename('/probe/test') !== 'test') throw new Error('ESM import mismatch');
  // Fixed public host, no credentials. Failures are retained as unverified API evidence.
  stage = 'network';
  const network = { dns: false, tls: false, failure: null };
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    try {
      await Promise.race([
        dns.lookup('example.com'),
        new Promise((_, reject) => controller.signal.addEventListener('abort', () => reject(new Error('DNS timeout')), { once: true })),
      ]);
      network.dns = true;
    } finally { clearTimeout(timer); }
    await new Promise((resolve, reject) => {
      const request = https.request('https://example.com/', { method: 'HEAD', timeout: 5000 }, response => {
        response.resume();
        response.once('end', resolve);
      });
      request.once('timeout', () => request.destroy(new Error('TLS timeout')));
      request.once('error', reject);
      request.end();
    });
    network.tls = true;
  } catch (error) { network.failure = error instanceof Error ? error.message : 'Network probe failed'; }
  stage = 'result-write';
  const result = JSON.stringify({ schemaVersion: 1, node: process.version, platform: process.platform,
    arch: process.arch, pid: process.pid, uid: typeof process.getuid === 'function' ? process.getuid() : null,
    uidApiAvailable: typeof process.getuid === 'function', execPath: process.execPath, childNodeLaunch: 'not-tested', nativeLock: lock,
    nativeLockProvider: lock ? 'upstream-system-entry' : 'not-tested', network, sqlite: true, worker: true, esm: true,
    crypto: crypto.createHash('sha256').update('probe').digest('hex'), harnessStarted: false });
  const pending = output + '.pending';
  fs.writeFileSync(pending, result, { mode: 0o600 });
  fs.renameSync(pending, output);
}
/** Completion of the fixed API probe, also awaited by the executable comparison. */
export const probeCompletion = main().catch(error => {
  console.error(error instanceof Error ? error.stack : String(error));
  const output = process.argv[2];
  if (output && path.isAbsolute(output)) {
    try {
      const pending = output + '.pending';
      fs.writeFileSync(pending, JSON.stringify({ schemaVersion: 1, stage,
        failure: error instanceof Error ? error.message : String(error),
        node: process.version, platform: process.platform, arch: process.arch,
        harnessStarted: false }), { mode: 0o600 });
      fs.renameSync(pending, output);
    } catch (writeError) { console.error('Failure result could not be written:', writeError.message); }
  }
  process.exitCode = 1;
});
