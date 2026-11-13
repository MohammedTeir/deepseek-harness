// Component contract tests use doubles; genuine positive Agent/PTY evidence is a separate profile test.
import assert from 'node:assert/strict';
import { createTerminalAllocationAuthority, relayTerminalApproval } from '../runtime/terminal-authorization.mjs';
const configuration = { sessionId: 'session', backend: 'android-fixed-pty-v1', executable: '/installed/libharness_pty_fixture.so', cwd: '/private/workspace', uid: 1000 };
const fields = { sessionId: 'session', callId: 'call', ownerId: 'session', terminalId: 'pty-1', backend: configuration.backend,
  executable: configuration.executable, arguments: ['--tty-child'], cwd: configuration.cwd, columns: 80, rows: 24 };
let prepares = 0;
const relay = { configuration, callIds: ['call'], toolName: 'terminal', requestNative: async () => { prepares++; return { ok: true, outcome: 'allowed-once' }; } };
for (const change of [{ terminalId: 'other' }, { ownerId: 'other' }, { callId: 'other' }, { executable: '/system/bin/sh' },
  { cwd: '/' }, { arguments: ['--wait'] }, { columns: 81 }, { rows: 25 }, { uid: 0 }]) {
  await assert.rejects(relayTerminalApproval({ sessionId: 'session', callId: 'call', toolName: 'terminal', reason: JSON.stringify({ ...fields, ...change }) }, relay), { code: 'TERMINAL_REQUEST_CHANGED' });
}
assert.equal(prepares, 0);
await assert.rejects(relayTerminalApproval({ sessionId: 'session', callId: 'other', toolName: 'terminal', reason: JSON.stringify(fields) }, relay), { code: 'TERMINAL_REQUEST_CHANGED' });
const agent = { id: 'session' }; // Negative component fixture only; never labelled an authentic Agent.
const spec = { owner: agent, sessionId: 'pty-1', cwd: configuration.cwd, type: 'fixture' };
const base = { configuration, callIds: ['call'], toolName: 'terminal', registryType: 'fixture', exec: { agent, callId: 'call' } };
for (const mode of ['changed-receipt', 'used', 'cancelled', 'missing-answerer']) {
  let consumes = 0, cancels = 0;
  const ctx = { agents: { get: () => agent }, approval: { request: async () => mode === 'missing-answerer' ? 'unavailable' : 'allowed-once' } };
  const authority = createTerminalAllocationAuthority({ ...base, ctx, requestNative: async (action, binding) => {
    if (action === 'cancel') { cancels++; return { ok: true }; }
    consumes++;
    if (mode === 'used') return { ok: false, code: 'USED' };
    return { ok: true, allocation: { ...binding, terminalId: 'pty-2', uid: configuration.uid } };
  } });
  const abort = new AbortController(); if (mode === 'cancelled') abort.abort(new Error('before allocation'));
  await assert.rejects(authority.authorize(spec, abort.signal));
  assert.throws(() => authority.take(spec)); await authority.close();
  assert.equal(consumes, mode === 'missing-answerer' || mode === 'cancelled' ? 0 : 1);
  assert.equal(cancels, mode === 'cancelled' ? 0 : 1);
}
let release, cancelled = 0, consumed = 0;
const ctx = { agents: { get: () => agent }, approval: { request: () => new Promise(resolve => { release = resolve; }) } };
const authority = createTerminalAllocationAuthority({ ...base, ctx, requestNative: async action => {
  if (action === 'cancel') { cancelled++; return { ok: true }; }
  consumed++; throw new Error('must not consume');
} });
const pending = authority.authorize(spec, new AbortController().signal);
await authority.close(); release('allowed-once');
await assert.rejects(pending, { code: 'TERMINAL_AUTHORITY_REVOKED' });
assert.equal(cancelled, 1); assert.equal(consumed, 0); assert.throws(() => authority.take(spec));
for (const mode of ['revoked-after-receipt', 'owner-disposed-before-take']) {
  let live = true, cancels = 0;
  const mutableConfiguration = { ...configuration }, ids = ['call'];
  const ctx = { agents: { get: () => live ? agent : undefined }, approval: { request: async () => 'allowed-once' } };
  const authority = createTerminalAllocationAuthority({ ...base, ctx, configuration: mutableConfiguration, callIds: ids,
    requestNative: async (action, binding) => {
      if (action === 'cancel') { cancels++; return { ok: true }; }
      return { ok: true, allocation: { ...binding, uid: 1000 } };
    } });
  mutableConfiguration.uid = 0; ids[0] = 'changed-after-composition';
  await authority.authorize(spec, new AbortController().signal);
  if (mode === 'revoked-after-receipt') await authority.close();
  else live = false;
  assert.throws(() => authority.take(spec)); await authority.close();
  assert.equal(cancels, 1);
}
console.log('PASS: terminal authority negative contract cases; doubles only, no Android evidence');
