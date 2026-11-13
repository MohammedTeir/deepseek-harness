// HOST ONLY: real original profile/tool/approval/session + actual Linux pwd.
// Automated broker decision fixture does not establish Android IPC or human approval.
import net from 'node:net';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
export async function qualify(resultPath, runtime = fileURLToPath(new URL('../runtime/command-smoke.mjs', import.meta.url))) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'hcmd-'));
  const socketPath = path.join(root, 's');
  const workspace = path.join(root, 'workspace'); await fs.mkdir(workspace);
  const secret = 'host-fixture-only'; const sessionId = 'android-command-host'; const callIds = ['deny-host', 'allow-host'];
  const state = new Map(); let processes = 0;
  const peers = new Set();
  const server = net.createServer(socket => {
    peers.add(socket); socket.once('close', () => peers.delete(socket));
    let bytes = '';
    socket.on('data', async data => {
      bytes += data;
      if (!bytes.endsWith('\n')) return;
      socket.removeAllListeners('data');
      try {
        const request = JSON.parse(bytes);
        const reply = async () => {
          if (request.version !== 1) return { ok: false, code: 'MALFORMED_OR_DISCONNECTED' };
          if (request.token !== secret) return { ok: false, code: 'UNAUTHENTICATED' };
          if (request.action === 'describe') return { ok: true, sessionId, callIds, cwd: workspace };
          if (!['prepare', 'execute', 'cancel'].includes(request.action)) return { ok: false, code: 'UNSUPPORTED_ACTION' };
          if ('uid' in request) return { ok: false, code: 'MALFORMED' };
          if (request.sessionId !== sessionId || !callIds.includes(request.callId) || request.cwd !== workspace || request.executable !== '/system/bin/pwd' || request.arguments.length) return { ok: false, code: 'REQUEST_CHANGED' };
          if (request.action === 'prepare') { if (state.has(request.callId)) return { ok: false, code: 'DUPLICATE' }; const outcome = request.callId === callIds[0] ? 'rejected' : 'allowed-once'; state.set(request.callId, outcome); return { ok: true, outcome }; }
          if (!state.has(request.callId)) return { ok: false, code: 'APPROVAL_REQUIRED' };
          if (state.get(request.callId) !== 'allowed-once') return { ok: false, code: 'USED' };
          state.set(request.callId, 'used'); processes++;
          const child = spawn('/usr/bin/pwd', [], { cwd: workspace, env: {} });
          let stdout = '', stderr = '';
          child.stdout.on('data', data => stdout += data); child.stderr.on('data', data => stderr += data);
          const exitCode = await new Promise((resolve, reject) => { child.once('error', reject); child.once('close', resolve); });
          return { ok: true, result: { stdout, stderr, exitCode, cwd: workspace } };
        };
        socket.end(JSON.stringify(await reply()) + '\n');
      } catch (error) { socket.destroy(error); }
    });
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(socketPath, resolve); });
  try {
    const env = { ...process.env, HARNESS_COMMAND_SOCKET: socketPath, HARNESS_COMMAND_SECRET: secret };
    delete env.DEEPSEEK_API_KEY;
    const output = path.join(root, 'result.json');
    const child = spawn(process.execPath, [runtime, output], { env, stdio: ['ignore', 'pipe', 'pipe'] });
    let logs = ''; child.stdout.on('data', data => logs += data); child.stderr.on('data', data => logs += data);
    let forced;
    const deadline = setTimeout(() => { child.kill('SIGTERM'); forced = setTimeout(() => child.kill('SIGKILL'), 10000); }, 110000);
    let code;
    try { code = await new Promise((resolve, reject) => { child.once('error', reject); child.once('close', resolve); }); }
    finally { clearTimeout(deadline); clearTimeout(forced); }
    if (code !== 0) throw new Error('Original host command qualification failed:\n' + logs + '\n' + await fs.readFile(output, 'utf8'));
    const result = JSON.parse(await fs.readFile(output, 'utf8'));
    if (processes !== 1) throw new Error('Expected exactly one real host child');
    result.hostQualification = { automatedDecisionFixture: true, androidIpcTested: false, androidExecutionTested: false, humanApprovalTested: false, actualHostExecutable: '/usr/bin/pwd', processLaunches: processes };
    await fs.writeFile(resultPath, JSON.stringify(result, null, 2) + '\n');
    return result;
  } finally {
    for (const peer of peers) peer.destroy();
    await new Promise(resolve => server.close(resolve));
    await fs.rm(root, { recursive: true, force: true });
  }
}
if (process.argv[1] === fileURLToPath(import.meta.url)) await qualify(process.argv[2], process.argv[3]);
