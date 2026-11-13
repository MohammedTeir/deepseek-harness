// HOST ONLY: real production controller/profile/PTY; automated broker contract double.
import net from 'node:net';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
export async function qualify(resultPath, runtime = fileURLToPath(new URL('../runtime/terminal-smoke.mjs', import.meta.url))) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'hterm-'));
  const workspace = path.join(root, 'workspace'); await fs.mkdir(workspace);
  const executable = process.env.HARNESS_TERMINAL_FIXTURE;
  if (!executable || !path.isAbsolute(executable) || path.basename(executable) !== 'libharness_pty_fixture.so') throw new Error('Prebuilt host fixture required');
  const sessionId = 'android-terminal-host', callIds = ['deny-host', 'allow-host'];
  const configuration = { sessionId, ownerId: sessionId, backend: 'android-fixed-pty-v1', executable,
    arguments: ['--tty-child'], cwd: workspace, columns: 80, rows: 24, uid: process.getuid() };
  const secret = crypto.randomBytes(32).toString('hex'), address = path.join(root, 's');
  const states = new Map(), peers = new Set(); let consumed = 0;
  const server = net.createServer(socket => {
    peers.add(socket); socket.once('close', () => peers.delete(socket));
    let text = ''; socket.setTimeout(10000, () => socket.destroy());
    socket.on('data', data => {
      text += data;
      if (text.length > 8192) return socket.destroy();
      if (!text.endsWith('\n')) return;
      socket.removeAllListeners('data');
      try {
        const req = JSON.parse(text);
        const reply = (() => {
          if (req.version !== 1) return { ok: false, code: 'MALFORMED_OR_DISCONNECTED' };
          if (req.token !== secret) return { ok: false, code: 'UNAUTHENTICATED' };
          if (req.action === 'describe') return { ok: true, sessionId, callIds, configuration };
          if (!['prepare', 'consume', 'cancel'].includes(req.action)) return { ok: false, code: 'UNSUPPORTED_ACTION' };
          if ('uid' in req) return { ok: false, code: 'MALFORMED' };
          if (req.sessionId !== sessionId || req.ownerId !== sessionId || !callIds.includes(req.callId)
            || req.backend !== configuration.backend || req.executable !== executable || req.cwd !== workspace
            || req.columns !== 80 || req.rows !== 24 || JSON.stringify(req.arguments) !== '["--tty-child"]') return { ok: false, code: 'REQUEST_CHANGED' };
          const state = states.get(req.callId);
          if (state && state.terminalId !== req.terminalId) return { ok: false, code: 'REQUEST_CHANGED' };
          if (req.action === 'prepare') {
            if (state) return { ok: false, code: 'DUPLICATE' };
            const outcome = req.callId === callIds[0] ? 'rejected' : 'allowed-once';
            states.set(req.callId, { terminalId: req.terminalId, outcome }); return { ok: true, outcome };
          }
          if (req.action === 'cancel') { states.set(req.callId, { terminalId: req.terminalId, outcome: 'CLOSED' }); return { ok: true }; }
          if (!state) return { ok: false, code: 'APPROVAL_REQUIRED' };
          if (state.outcome !== 'allowed-once') return { ok: false, code: state.outcome };
          state.outcome = 'USED'; consumed++;
          const { version, token, action, ...fields } = req;
          return { ok: true, allocation: { ...fields, uid: configuration.uid } };
        })();
        socket.end(JSON.stringify(reply) + '\n');
      } catch { socket.destroy(); }
    });
  });
  let child;
  try {
    await new Promise((resolve, reject) => { server.once('error', reject); server.listen(address, resolve); });
    const output = path.join(root, 'result.json');
    const env = { ...process.env, HARNESS_TERMINAL_SOCKET: address, HARNESS_TERMINAL_SECRET: secret, HARNESS_TERMINAL_HOST_QUALIFICATION: '1' };
    child = spawn(process.execPath, [runtime, output], { env, stdio: ['ignore', 'pipe', 'pipe'] });
    let logs = ''; child.stdout.on('data', data => logs += data); child.stderr.on('data', data => logs += data);
    let force;
    const timer = setTimeout(() => { child.kill('SIGTERM'); force = setTimeout(() => child.kill('SIGKILL'), 10000); }, 110000);
    let code;
    try { code = await new Promise((resolve, reject) => { child.once('error', reject); child.once('close', resolve); }); }
    finally { clearTimeout(timer); clearTimeout(force); }
    if (code !== 0) throw new Error('Production terminal controller host qualification failed:\n' + logs + '\n' + await fs.readFile(output, 'utf8'));
    const result = JSON.parse(await fs.readFile(output, 'utf8'));
    if (consumed !== 1 || !result.sessionRecoveredAcrossRuntimeRestart || result.report.starts !== 1) throw new Error('Host original terminal invariants differ');
    result.hostQualification = { nativeTransportIsDouble: true, automatedDecisions: true, androidExecuted: false, humanApprovalVerified: false, consumed };
    await fs.writeFile(resultPath, JSON.stringify(result, null, 2) + '\n');
    return result;
  } finally {
    if (child && child.exitCode === null && child.signalCode === null) {
      child.kill('SIGKILL'); await new Promise(resolve => child.once('close', resolve));
    }
    for (const peer of peers) peer.destroy();
    if (server.listening) await new Promise(resolve => server.close(resolve));
    await fs.rm(root, { recursive: true, force: true });
  }
}
if (process.argv[1] === fileURLToPath(import.meta.url)) await qualify(process.argv[2], process.argv[3]);
