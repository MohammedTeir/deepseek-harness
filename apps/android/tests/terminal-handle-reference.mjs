// HOST ONLY: actual original node-pty and the original TypeScript handle contract.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { createRequire } from 'node:module';
import { createFixtureTerminalHandle } from '../runtime/node-pty-proof/terminal-handle.ts';
const require = createRequire(import.meta.url);
const pty = require('../runtime/node-pty-proof/loader.cjs')(process.env.HARNESS_NODE_PTY_PACKAGE, process.env.HARNESS_NODE_PTY_ADDON);
let launches = 0; const killSignals = [];
const backend = { spawn(...args) {
  launches++; const terminal = pty.spawn(...args); const kill = terminal.kill.bind(terminal);
  terminal.kill = signal => { killSignals.push(signal); return kill(signal); };
  return terminal;
} };
const options = { fixtureExecutable: process.env.HARNESS_NODE_PTY_FIXTURE, cwd: process.cwd(), graceMs: 100 };
const reports = [];
async function scenario(role, action) {
  const handle = createFixtureTerminalHandle(backend, { ...options, role, ...action.ownerSignal ? { ownerSignal: action.ownerSignal } : {} });
  let text = '', readyResolve; const ready = new Promise(resolve => { readyResolve = resolve; });
  const reading = (async () => { for await (const chunk of handle.output) { text += chunk; if (text.includes(role === '--tty-child' ? 'TTY-READY' : 'READY')) readyResolve(); } })();
  let deadline;
  const waitReady = () => Promise.race([ready, handle.done.then(() => { throw new Error('Child exited before readiness'); }), new Promise((_, reject) => { deadline = setTimeout(() => reject(new Error('Readiness deadline')), 5000); })]).finally(() => clearTimeout(deadline));
  try {
    if (role !== '--exit-seven') await waitReady();
    await action(handle);
    const outcome = await handle.done; await reading;
    reports.push({ role, pid: handle.pid, outcome, output: text });
    await assert.rejects(handle.write('pty-input\n'), /closing or exited/);
    await assert.rejects(handle.resize(100, 40), /closing or exited/);
    return outcome;
  } finally { clearTimeout(deadline); await handle.terminate(); await reading; }
}
const aborted = new AbortController(); aborted.abort();
assert.throws(() => createFixtureTerminalHandle(backend, { ...options, role: '--wait', ownerSignal: aborted.signal }));
for (const change of [{ role: 'arbitrary-command' }, { graceMs: 0 }, { fixtureExecutable: 'relative' }]) {
  assert.throws(() => createFixtureTerminalHandle(backend, { ...options, role: '--wait', ...change }));
}
assert.equal(launches, 0);
const normal = await scenario('--tty-child', async handle => {
  assert.equal(await handle.inspectForeground(), undefined);
  assert.equal((await handle.inspectActivity()).state, 'unknown');
  await assert.rejects(handle.signalForeground('SIGTERM'), { code: 'SUBPROCESS_PTY_UNAVAILABLE' });
  await assert.rejects(handle.write('pwd\n'), /fixed qualification input/);
  await assert.rejects(handle.resize(0, 40), /Invalid dimensions/);
  await handle.resize(100, 40); await handle.write('pty-input\n');
});
assert.deepEqual(normal, { exitCode: 0, signal: null });
assert.match(reports[0].output, /TTY-INPUT:pty-input ROWS:40 COLS:100/);
assert.match(reports[0].output, /TTY-STDERR/);
assert.deepEqual(await scenario('--exit-seven', async () => {}), { exitCode: 7, signal: null });
assert.deepEqual(await scenario('--wait', handle => handle.write('\x03')), { exitCode: null, signal: 'SIGINT' });
const before = killSignals.length;
assert.deepEqual(await scenario('--ignore-term', handle => Promise.all([handle.terminate(), handle.terminate()])), { exitCode: null, signal: 'SIGKILL' });
assert.deepEqual(killSignals.slice(before), ['SIGTERM', 'SIGKILL']);
const owner = new AbortController(); const abortAction = async () => { owner.abort(); }; abortAction.ownerSignal = owner.signal;
assert.deepEqual(await scenario('--wait', abortAction), { exitCode: null, signal: 'SIGTERM' });
assert.equal(launches, 5);
await fs.writeFile(process.argv[2], JSON.stringify({ environment: 'Linux host only; not Android evidence', scope: 'Fixed fixture handles only; not an execution authority', launches, reports,
  originalHandleInterface: 'SubprocessTerminalHandle; strict typecheck recorded separately', managedRange: 'Fixed direct child only', foregroundIdentityVerified: false, androidHandleExecuted: false, originalTerminalIntegrated: false, gate3Passed: false }, null, 2));
console.log('PASS: real original node-pty handle I/O, exit 7, SIGINT, concurrent TERM/KILL cleanup, owner abort, unsupported foreground and post-close requests');
