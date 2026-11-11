// Deterministic embedded-runtime probe. No model, credentials, or Harness loop is simulated.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { Worker } from 'node:worker_threads';
import { DatabaseSync } from 'node:sqlite';
import dns from 'node:dns/promises';
import https from 'node:https';
import { constants } from 'node:os';

async function main() {
  const output = process.argv[2];
  if (!output || !path.isAbsolute(output)) throw new Error('An absolute result path is required');
  const sqlite = new DatabaseSync(':memory:');
  try {
    if (sqlite.prepare('select 42 as answer').get().answer !== 42) throw new Error('SQLite result mismatch');
  } finally { sqlite.close(); }
  const worker = new Worker("require('node:worker_threads').parentPort.postMessage(42)", { eval: true });
  try {
    const answer = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Worker timeout')), 5000);
      worker.once('message', value => { clearTimeout(timer); resolve(value); });
      worker.once('error', error => { clearTimeout(timer); reject(error); });
    });
    if (answer !== 42) throw new Error('Worker result mismatch');
  } finally { await worker.terminate(); }
  let lock = false;
  if (process.platform === 'android') {
    const binding = { exports: {} };
    process.dlopen(binding, 'libharness_system.so');
    const file = path.join(path.dirname(output), 'probe.lock');
    let first;
    let second;
    const acquire = fd => new Promise(resolve => binding.exports.tryLock(fd, resolve));
    try {
      first = fs.openSync(file, 'a');
      second = fs.openSync(file, 'a');
      if (await acquire(first) !== 0) throw new Error('Native lock acquisition failed');
      const contention = await acquire(second);
      if (contention !== constants.errno.EAGAIN && contention !== constants.errno.EWOULDBLOCK) {
        throw new Error('Native lock contention was not rejected');
      }
      fs.closeSync(first);
      first = undefined;
      if (await acquire(second) !== 0) throw new Error('Native lock release/reacquisition failed');
      lock = true;
    } finally {
      if (first !== undefined) fs.closeSync(first);
      if (second !== undefined) fs.closeSync(second);
    }
  }
  const esm = await import('node:path');
  if (esm.basename('/probe/test') !== 'test') throw new Error('ESM import mismatch');
  // Fixed public host, no credentials. Failures are retained as unverified API evidence.
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
  const result = JSON.stringify({ schemaVersion: 1, node: process.version, platform: process.platform,
    arch: process.arch, pid: process.pid, uid: process.getuid(), execPath: process.execPath, childNodeLaunch: 'not-tested', nativeLock: lock, network, sqlite: true, worker: true, esm: true,
    crypto: crypto.createHash('sha256').update('probe').digest('hex'), harnessStarted: false });
  const pending = output + '.pending';
  fs.writeFileSync(pending, result, { mode: 0o600 });
  fs.renameSync(pending, output);
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
