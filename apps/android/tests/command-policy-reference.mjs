// Isolated hook unit test, not a Harness composition or Android execution claim.
import assert from 'node:assert/strict';
import { apply } from '../runtime/command-plugin.mjs';
const previous = { session: process.env.HARNESS_COMMAND_SESSION, calls: process.env.HARNESS_COMMAND_CALLS };
process.env.HARNESS_COMMAND_SESSION = 'unit-policy';
process.env.HARNESS_COMMAND_CALLS = '["unit-deny","unit-allow"]';
try {
  const hooks = new Map();
  apply({ tools: { register() {} }, commands: { register() {} }, provide() {}, on(name, callback) { hooks.set(name, callback); } });
  const hook = hooks.get('tools/pre-execute');
  for (const kind of ['deny', 'cancel', 'ask']) {
    const original = { kind, reason: 'downstream original policy' };
    let consulted = false;
    const value = await hook({ name: 'android_qualified_pwd' }, async () => { consulted = true; return original; });
    assert.equal(consulted, true);
    assert.equal(value, original);
  }
  assert.equal((await hook({ name: 'android_qualified_pwd' }, async () => ({ kind: 'allow' }))).kind, 'ask');
  assert.equal((await hook({ name: 'other' }, async () => ({ kind: 'allow' }))).kind, 'allow');
  await assert.rejects(hook({ name: 'android_qualified_pwd' }, async () => { throw new Error('policy failed'); }), /policy failed/);
  console.log('PASS: original downstream deny/cancel/ask and failures preserved; only allow adds native ask');
} finally {
  for (const [name, value] of [['HARNESS_COMMAND_SESSION', previous.session], ['HARNESS_COMMAND_CALLS', previous.calls]]) {
    if (value === undefined) delete process.env[name]; else process.env[name] = value;
  }
}
