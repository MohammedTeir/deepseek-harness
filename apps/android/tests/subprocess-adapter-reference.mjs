// Linux-only original-service tests with a transport fixture and a real host pwd.
import assert from 'node:assert/strict';
import net from 'node:net';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { AndroidFixedPwdSubprocess, withFixedPwdCall } from '../runtime/android-subprocess.mjs';
const requireLocal = createRequire(new URL('../../../packages/subprocess/subprocess-local/package.json', import.meta.url));
const { Context } = await import(requireLocal.resolve('@deepseek-ai/cordis'));
const { SubprocessRuntime } = await import(requireLocal.resolve('@deepseek-ai/dsh-subprocess'));
const root = await fs.mkdtemp(path.join(os.tmpdir(), 'hsub-'));
const socketPath = path.join(root, 's');
const previous = { socket: process.env.HARNESS_COMMAND_SOCKET, secret: process.env.HARNESS_COMMAND_SECRET };
process.env.HARNESS_COMMAND_SOCKET = socketPath; process.env.HARNESS_COMMAND_SECRET = 'host-only-test';
const peers = new Set(), grants = new Set(); let launches = 0, requests = 0;
let holdingReady, cancelSeen, releaseCancel;
const holding = new Promise(resolve => { holdingReady = resolve; });
const cancelled = new Promise(resolve => { cancelSeen = resolve; });
const cancelGate = new Promise(resolve => { releaseCancel = resolve; });
const server = net.createServer(socket => {
  peers.add(socket); socket.once('close', () => peers.delete(socket));
  let text = '';
  socket.on('data', async chunk => {
    text += chunk; if (!text.endsWith('\n')) return; socket.removeAllListeners('data'); requests++;
    try {
      const request = JSON.parse(text);
      if (request.token !== 'host-only-test') return socket.end(JSON.stringify({ ok: false, code: 'UNAUTHENTICATED' })+'\n');
      if (request.callId === 'no-ack') return socket.end(JSON.stringify(request.action === 'cancel' ? { ok: false, code: 'CLOSED' } : { ok: true, result: {} })+'\n');
      if (request.action === 'describe') return socket.end(JSON.stringify({ ok: true, fixedExecutableAvailable: true })+'\n');
      if (request.action === 'cancel') { if (request.callId === 'hold') { cancelSeen(); await cancelGate; } return socket.end(JSON.stringify({ ok: true })+'\n'); }
      if (request.callId === 'hold') { holdingReady(); return; } // Transport fixture only: no native process or manufactured command result.
      if (grants.has(request.callId)) return socket.end(JSON.stringify({ ok: false, code: 'USED' })+'\n');
      grants.add(request.callId); launches++;
      const child = spawn(request.callId === 'nonzero' ? '/usr/bin/false' : '/usr/bin/pwd', [], { cwd: root, env: {} });
      let stdout = '', stderr = '';
      child.stdout.on('data', data => stdout += data); child.stderr.on('data', data => stderr += data);
      const exitCode = await new Promise((resolve, reject) => { child.once('error', reject); child.once('close', resolve); });
      socket.end(JSON.stringify({ ok: true, result: { stdout, stderr, exitCode, cwd: root } })+'\n');
    } catch (error) { socket.destroy(error); }
  });
});
await new Promise((resolve, reject) => { server.once('error', reject); server.listen(socketPath, resolve); });
const ctx = new Context();
const runtime = new AndroidFixedPwdSubprocess(ctx);
const fields = { sessionId: 'host-session', callId: 'host-call', executable: '/system/bin/pwd', arguments: [], cwd: root };
const spec = { argv: ['/system/bin/pwd'], cwd: root, stdio: { stdin: 'ignore', stdout: { maxBytes: 65536 }, stderr: { maxBytes: 65536 } }, graceMs: 2000 };
try {
  assert.ok(runtime instanceof SubprocessRuntime);
  assert.throws(() => runtime.spawn(spec), /tool-call binding/);
  await assert.rejects(runtime.spawnTerminal({ signal: undefined }), { code: 'SUBPROCESS_PTY_UNAVAILABLE' });
  await assert.rejects(runtime.resolveExecutable('bash'), { code: 'SUBPROCESS_EXECUTABLE_NOT_FOUND' });
  assert.deepEqual(await runtime.terminalEnvironment(), { platform: 'posix' });
  assert.equal(await runtime.resolveExecutable('pwd'), '/system/bin/pwd');
  await withFixedPwdCall(fields, async () => {
    const before = requests;
    for (const change of [{ argv: ['/system/bin/sh'] }, { cwd: '/' }, { env: { KEY: 'never-forward' } }, { stdio: { ...spec.stdio, stdout: 'pipe' } }, { graceMs: 0 }, { stdio: { ...spec.stdio, stdout: { maxBytes: 8, spill: { maxBytes: 100 } } } }]) assert.throws(() => runtime.spawn({ ...spec, ...change }));
    const abort = new AbortController(); abort.abort(); assert.throws(() => runtime.spawn({ ...spec, signal: abort.signal }));
    assert.equal(requests, before);
    const handles = [runtime.spawn(spec), runtime.spawn(spec)];
    const outcomes = await Promise.allSettled(handles.map(handle => handle.done));
    assert.equal(outcomes.filter(outcome => outcome.status === 'fulfilled').length, 1);
    assert.equal(outcomes.filter(outcome => outcome.status === 'rejected' && outcome.reason.nativeCode === 'USED').length, 1);
    assert.deepEqual(await Promise.all(handles.map(handle => handle.waitForExit())), [true, true]);
    const winner = handles[outcomes.findIndex(outcome => outcome.status === 'fulfilled')];
    const first = winner.collected.stdout.readFrom(0);
    assert.equal(first.text, root+'\n'); assert.equal(first.lossy, false);
    assert.deepEqual(winner.collected.stdout.readFrom(0), first); // Independent readers do not consume.
    assert.equal(winner.collected.stdout.readFrom(first.nextOffset).text, '');
    assert.equal(winner.collected.stderr.readFrom(0).text, '');
    assert.throws(() => winner.collected.stdout.readFrom(-1));
    const bounded = await withFixedPwdCall({ ...fields, callId: 'tail' }, async () => {
      const handle = runtime.spawn({ ...spec, stdio: { ...spec.stdio, stdout: { maxBytes: 3 } } });
      await handle.done; await handle.waitForExit(); return handle.collected.stdout;
    });
    assert.deepEqual(bounded.readFrom(0), { text: (root+'\n').slice(-3), nextOffset: Buffer.byteLength(root+'\n'), lossy: true });
  });
  await withFixedPwdCall({ ...fields, callId: 'nonzero' }, async () => {
    const failed = runtime.spawn(spec);
    await assert.rejects(failed.done, error => error.nativeExitCode === 1 && error.code === 'SUBPROCESS_RUNNER_FAILED');
    assert.equal(await failed.waitForExit(), true);
  });
  assert.equal(launches, 3);
  await withFixedPwdCall({ ...fields, callId: 'hold' }, async () => {
    const controller = new AbortController();
    const handle = runtime.spawn({ ...spec, signal: controller.signal });
    let completed = false; void handle.done.then(() => { completed = true; }, () => { completed = true; });
    await holding; controller.abort();
    let disposed = false; const disposal = ctx.fiber.dispose().then(() => { disposed = true; });
    await cancelled; assert.equal(disposed, false);
    const stopWaiting = new AbortController(); stopWaiting.abort();
    assert.equal(await handle.waitForExit(stopWaiting.signal), false);
    assert.equal(completed, false); // Cancellation cannot settle before native cleanup acknowledgment.
    releaseCancel(); await assert.rejects(handle.done, /cancelled/);
    assert.equal(await handle.waitForExit(), true); await disposal; assert.equal(disposed, true);
  });
  await ctx.fiber.dispose(); assert.throws(() => withFixedPwdCall(fields, () => runtime.spawn(spec)), /live original/);
  const failedCtx = new Context(); const failedRuntime = new AndroidFixedPwdSubprocess(failedCtx);
  await withFixedPwdCall({ ...fields, callId: 'no-ack' }, async () => {
    const handle = failedRuntime.spawn(spec);
    await assert.rejects(handle.done, { code: 'SUBPROCESS_RUNNER_IPC_FAILED' });
    await assert.rejects(handle.waitForExit(), /unacknowledged/);
    assert.equal(failedRuntime.cleanupFailures.length, 1);
  });
  let cleanupRejected = false;
  try { await failedCtx.fiber.dispose(); } catch (error) { cleanupRejected = true; assert.match(String(error), /quiescence/); }
  // Original root Context disposal collects cleanup errors instead of propagating them.
  assert.equal(cleanupRejected, false);
  console.log('PASS: original SubprocessRuntime; real host pwd; exact binding; unsupported features reject before IPC; one-shot concurrency; independent bounded readers; awaited disposal. NOT Android evidence.');
} finally {
  releaseCancel();
  await ctx.fiber.dispose();
  for (const peer of peers) peer.destroy();
  await new Promise(resolve => server.close(resolve));
  for (const [key, value] of [['HARNESS_COMMAND_SOCKET',previous.socket],['HARNESS_COMMAND_SECRET',previous.secret]]) { if (value === undefined) delete process.env[key]; else process.env[key] = value; }
  await fs.rm(root, { recursive: true, force: true });
}
