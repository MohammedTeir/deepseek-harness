// HOST ONLY. SDK decisions are automated; this is not a native Android approval test.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { shutdownConfirmed } from '../runtime/session-diagnostics.mjs';
const cli = createRequire(new URL('../../cli/package.json', import.meta.url));
const terminal = createRequire(new URL('../../../packages/terminal/terminal-bash/package.json', import.meta.url));
const { HarnessClient } = await import(cli.resolve('@deepseek-ai/dsh-sdk-client'));
const root = await fs.mkdtemp(path.join(os.tmpdir(), 'terminal-registry-'));
const clients = new Set();
try {
  const cwd = path.join(root, 'workspace'); await fs.mkdir(cwd);
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !/KEY|TOKEN|SECRET|PASSWORD/i.test(key)));
  env.HARNESS_TERMINAL_SESSION = 'terminal-host-profile'; env.HARNESS_TERMINAL_WORKSPACE = cwd;
  const patch = path.join(root, 'terminal.patch.yml');
  await fs.writeFile(patch, `- insert:\n    - id: host-terminal-service\n      name: ${JSON.stringify(terminal.resolve('@deepseek-ai/dsh-terminal'))}\n    - id: host-terminal-approval\n      name: '@deepseek-ai/dsh-user-approval'\n      config: {policy: ask}\n    - id: host-terminal-commands\n      name: '@deepseek-ai/dsh-commands'\n    - id: host-terminal-plugin\n      name: ${JSON.stringify(fileURLToPath(new URL('./terminal-registry-plugin.mjs', import.meta.url)))}\n- id: sdk-jsonrpc-server\n  inject: [sdkAppStartup, loader, sessionPersistence, approval, commands, hostTerminalQualificationReady]\n`);
  const options = { profile: 'sdk-minimal', patches: [fileURLToPath(new URL('../runtime/profile/no-execution.patch.yml', import.meta.url)), patch], dshHome: path.join(root, 'home'), processCwd: cwd, env,
    initializeTimeoutMs: 30000, requestTimeoutMs: 30000, shutdownTimeoutMs: 1000, disposeEofGraceMs: 6000 };
  const init = { cwd, provider: 'deepseek-official', model: 'deepseek-v4-flash', approvalRequests: true };
  const first = new HarnessClient(options); clients.add(first);
  const decisions = [];
  await first.start();
  first.onRequest(async (method, params) => {
    assert.equal(method, 'approval/request'); assert.equal(params.sessionId, env.HARNESS_TERMINAL_SESSION);
    const outcome = params.callId === 'deny-terminal' ? 'rejected' : 'allowed-once'; decisions.push(outcome); return { outcome };
  });
  await first.initialize(init); await first.setWorkingDirectory(env.HARNESS_TERMINAL_SESSION, cwd);
  const notifications = first.subscribe(e => e.method === 'session.event' && e.params.sessionId === env.HARNESS_TERMINAL_SESSION);
  for (let index = 0; index < 2; index++) { await first.prompt(env.HARNESS_TERMINAL_SESSION, [{ type: 'text', text: 'Run bounded host fixture, no model request.' }]); await first.request('session/wait', { sessionId: env.HARNESS_TERMINAL_SESSION }); }
  const events = []; for (let item; (item = notifications.tryNext());) events.push(item.params.event); notifications.close();
  const history = events.filter(e => e.type === 'approval/asked' || e.type === 'approval/decided' || (e.type === 'command/done' && e.data.text?.startsWith('{"terminalProof":')));
  const commands = history.filter(e => e.type === 'command/done').map(e => JSON.parse(e.data.text));
  assert.equal(commands.length, 2); assert.equal(commands[0].processStarts, 0);
  assert.equal(commands[0].batch.results[0].result.error.info.code, 'APPROVAL_REJECTED');
  const allowed = commands[1].batch.results[0].result;
  assert.equal(allowed.isError, false, JSON.stringify(allowed));
  const result = JSON.parse(allowed.content[0].text);
  assert.equal(result.originalTerminalRegistry, true); assert.equal(result.genuineAgentOwners, 2);
  assert.deepEqual(decisions, ['rejected', 'allowed-once']);
  await shutdownConfirmed(first); clients.delete(first);
  const second = new HarnessClient({ ...options, env: { ...env, HARNESS_TERMINAL_RECOVER: '1' } }); clients.add(second);
  await second.initialize(init); await second.resumeSession(env.HARNESS_TERMINAL_SESSION);
  const recoveredEvents = second.subscribe(e => e.method === 'session.event' && e.params.sessionId === env.HARNESS_TERMINAL_SESSION);
  await second.prompt(env.HARNESS_TERMINAL_SESSION, [{ type: 'text', text: 'Read the actual persisted qualification records.' }]); await second.request('session/wait', { sessionId: env.HARNESS_TERMINAL_SESSION });
  let recovered; for (let item; (item = recoveredEvents.tryNext());) if (item.params.event.type === 'command/done' && item.params.event.data.text?.startsWith('[')) recovered = JSON.parse(item.params.event.data.text);
  recoveredEvents.close(); assert.deepEqual(recovered, history);
  await shutdownConfirmed(second); clients.delete(second);
  await fs.writeFile(process.argv[2], JSON.stringify({ environment: 'Linux host only; NOT Android evidence', profile: 'sdk-minimal', result, history, recoveredHistory: recovered,
    runtimeStderr: [await first.runtimeStderr(), await second.runtimeStderr()], sessionRecoveredAcrossRuntimeRestart: true, automatedApprovalFixture: true, nativeHumanApprovalVerified: false, modelRequestExecuted: false, androidTerminalIntegrated: false, gate3Passed: false }, null, 2)+'\n');
  console.log('PASS: genuine profile, agents, original tool/approval/terminal registry, real PTY and persisted recovery; HOST ONLY');
} finally { await Promise.allSettled([...clients].map(client => client.close())); await fs.rm(root, { recursive: true, force: true }); }
