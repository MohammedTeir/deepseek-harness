// Original node-pty feasibility only; no agent, generic command API or terminal backend.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { readProcIdentity } from '../proc-identity.mjs';
const require = createRequire(import.meta.url);
const output = process.argv[2];
assert.ok(output && path.isAbsolute(output));
const active = new Set(), cases = [];
const planned = ['input-resize', 'exit-seven', 'ctrl-c', 'terminate', 'timeout-kill'];
let cancelled = false, stage = 'load-original-node-pty';
process.once('SIGTERM', () => { cancelled = true; for (const terminal of active) { try { terminal.kill('SIGKILL'); } catch {} } });
async function main() {
  const pty = process.platform === 'android' || process.env.HARNESS_NODE_PTY_USE_SOURCE_BINDING === '1'
    ? require('./loader.cjs')(process.env.HARNESS_NODE_PTY_PACKAGE, process.env.HARNESS_NODE_PTY_ADDON)
    : require(path.resolve(process.env.HARNESS_NODE_PTY_PACKAGE));
  const fixture = process.env.HARNESS_NODE_PTY_FIXTURE;
  assert.ok(fixture && path.isAbsolute(fixture), 'Native-owned fixed fixture path required; no shell fallback');
  const cwd = process.cwd();
  async function run(name, role, expectedSignal, input, naturalExit = false) {
    stage = name; assert.equal(cancelled, false);
    const terminal = pty.spawn(fixture, [role], { cwd, env: { PATH: '/system/bin', HARNESS_PTY_OWNER_PID: String(process.pid) }, cols: 80, rows: 24, name: 'xterm' });
    active.add(terminal);
    let text = '', ready = false, failure, timedOut = false, deadline, force;
    const signal = value => { try { terminal.kill(value); } catch (error) { failure ??= 'Signal failed: ' + error.message; } };
    const result = await new Promise((resolve, reject) => {
      const data = terminal.onData(chunk => {
        text += chunk;
        if (text.length > 16384) { failure = 'Output cap exceeded'; signal('SIGKILL'); return; }
        if (!ready && text.includes(role === '--tty-child' ? 'TTY-READY' : naturalExit ? 'EXIT-SEVEN' : 'READY')) {
          ready = true;
          try {
            if (naturalExit) { /* Fixed child exits by itself. */ }
            else if (input) { terminal.resize(100, 40); terminal.write('pty-input\n'); }
            else if (expectedSignal === 2) terminal.write('\x03');
            else if (expectedSignal === 15) signal('SIGTERM');
            else { clearTimeout(deadline); deadline = setTimeout(() => { timedOut = true; signal('SIGTERM'); force = setTimeout(() => signal('SIGKILL'), 300); }, 100); }
          } catch (error) { failure = error.message; signal('SIGKILL'); }
        }
      });
      const exit = terminal.onExit(event => {
        clearTimeout(deadline); clearTimeout(force); data.dispose(); exit.dispose(); active.delete(terminal);
        const report = { name, role, status: 'FAIL', pid: terminal.pid, exitCode: event.exitCode, signal: event.signal ?? 0, ready, timedOut,
          output: text.slice(0, 16384), exitEventObserved: true, childNoLongerObservable: false };
        cases.push(report);
        try {
          report.childNoLongerObservable = !exists(terminal.pid);
          const match = text.match(/IDENTITY:(\{[^\r\n]+\})/); assert.ok(match);
          const identity = JSON.parse(match[1]); report.nativeIdentity = identity;
          assert.equal(identity.parentPid, process.pid); assert.equal(identity.pid, terminal.pid); assert.equal(identity.uid, readProcIdentity().uid);
          assert.equal(failure, undefined); assert.equal(cancelled, false); assert.equal(ready, true); assert.equal(event.signal ?? 0, expectedSignal);
          if (naturalExit) assert.equal(event.exitCode, 7);
          if (input) { assert.equal(event.exitCode, 0); assert.ok(text.includes('TTY-INPUT:pty-input ROWS:40 COLS:100')); assert.ok(text.includes('TTY-STDERR')); }
          assert.equal(report.childNoLongerObservable, true);
          report.status = 'PASS'; resolve(report);
        } catch (error) { report.failure = error.message; reject(error); }
      });
      deadline = setTimeout(() => { failure = 'Readiness/completion deadline exceeded'; signal('SIGKILL'); }, 8000);
    });
    return result;
  }
  function exists(pid) { try { process.kill(pid, 0); return true; } catch (error) { if (error.code === 'ESRCH') return false; throw error; } }
  await run('input-resize', '--tty-child', 0, true);
  await run('exit-seven', '--exit-seven', 0, false, true);
  await run('ctrl-c', '--wait', 2);
  await run('terminate', '--wait', 15);
  await run('timeout-kill', '--ignore-term', 9);
  return { schemaVersion: 1, suite: 'original-node-pty-v1', status: 'PASS', node: process.version, platform: process.platform, arch: process.arch,
    kernelIdentity: readProcIdentity(), originalNodePtyVersion: '1.2.0-beta.15', nativeSourceModified: false, spawnHelperUsed: false,
    fixtureExecutable: fixture, cwd, cases, stderrMergedByPty: true, harnessStarted: false, originalTerminalIntegrated: false,
    generalShellProviderImplemented: false, gate3Passed: false };
}
try { await fs.writeFile(output, JSON.stringify(await main())); }
catch (error) {
  await fs.writeFile(output, JSON.stringify({ schemaVersion: 1, suite: 'original-node-pty-v1', status: 'FAIL', stage, failure: error.stack,
    node: process.version, platform: process.platform, arch: process.arch, cases,
    testOutcomes: planned.map(name => ({ name, status: cases.find(item => item.name === name)?.status ?? (stage === name ? 'FAIL' : 'BLOCKED') })), gate3Passed: false }));
  console.error(error.stack); process.exitCode = 1;
} finally { for (const terminal of active) { try { terminal.kill('SIGKILL'); } catch {} } }
