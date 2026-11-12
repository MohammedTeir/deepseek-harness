// Host transport failure injection with a real owned Node child, not Android IPC evidence.
import net from 'node:net';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import assert from 'node:assert/strict';
import { brokerRequest } from '../runtime/command-wire.mjs';
const root = await fs.mkdtemp(path.join(os.tmpdir(), 'hcwire-'));
const socketPath = path.join(root, 's');
const previous = { socket: process.env.HARNESS_COMMAND_SOCKET, secret: process.env.HARNESS_COMMAND_SECRET };
process.env.HARNESS_COMMAND_SOCKET = socketPath;
process.env.HARNESS_COMMAND_SECRET = 'host-transport-fixture';
let child, exited, cancelled = false;
const sockets = new Set();
const server = net.createServer(socket => {
  sockets.add(socket); socket.once('close', () => sockets.delete(socket));
  let bytes = '';
  socket.on('data', async chunk => {
    bytes += chunk;
    if (!bytes.endsWith('\n')) return;
    socket.removeAllListeners('data');
    try {
      const request = JSON.parse(bytes);
      if (request.action === 'execute') {
        child = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { stdio: 'ignore' });
        exited = new Promise((resolve, reject) => { child.once('error', reject); child.once('close', resolve); });
        await new Promise((resolve, reject) => { child.once('spawn', resolve); child.once('error', reject); });
        socket.destroy(); // Lose the execution response while the real child is still alive.
      } else if (request.action === 'cancel') {
        assert.ok(child);
        child.kill('SIGTERM');
        await exited;
        cancelled = true;
        socket.end(JSON.stringify({ ok: true }) + '\n');
      } else throw new Error('Unexpected fixture action');
    } catch (error) { socket.destroy(error); }
  });
});
try {
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(socketPath, resolve); });
  await assert.rejects(brokerRequest('execute', { sessionId: 'host', callId: 'host-call' }));
  assert.equal(cancelled, true);
  assert.ok(child.exitCode !== null || child.signalCode !== null);
  console.log('PASS: lost execution reply rejected only after cancellation acknowledged and real child reaped');
} finally {
  if (child && child.exitCode === null && child.signalCode === null) { child.kill('SIGKILL'); await exited; }
  for (const socket of sockets) socket.destroy();
  await new Promise(resolve => server.close(resolve));
  await fs.rm(root, { recursive: true, force: true });
  for (const [name, value] of [['HARNESS_COMMAND_SOCKET', previous.socket], ['HARNESS_COMMAND_SECRET', previous.secret]]) {
    if (value === undefined) delete process.env[name]; else process.env[name] = value;
  }
}
