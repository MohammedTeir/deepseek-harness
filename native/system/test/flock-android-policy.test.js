/** Host-only Android loader policy tests; simulated metadata is not Android ABI evidence. */
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

function run(body, flags = []) {
  const result = spawnSync(process.execPath, [...flags, '--input-type=module', '-e', `
    import assert from 'node:assert/strict';
    Object.defineProperty(process, 'platform', { value: 'android' });
    Object.defineProperty(process, 'arch', { value: 'arm64' });
    ${body}
  `], { encoding: 'utf8', timeout: 10000, cwd: new URL('..', import.meta.url) });
  assert.ifError(result.error);
  assert.equal(result.signal, null, result.stderr);
  assert.equal(result.status, 0, result.stderr);
}

test('Android entry imports lazily and rejects when native addons are disabled', () => {
  run(`
    const { tryLockExclusive } = await import('./packages/entry/lib/flock.js');
    await assert.rejects(tryLockExclusive(-1), { code: 'ERR_DLOPEN_DISABLED' });
  `, ['--no-addons']);
});

test('Android loader uses only its fixed SONAME and retains flock errno semantics', () => {
  run(`
    let loads = 0;
    process.dlopen = (module, filename) => {
      loads++;
      assert.equal(filename, 'libharness_system.so');
      module.exports.tryLock = (fd, callback) => setImmediate(callback, fd === 7 ? 0 : 11);
    };
    const { tryLockExclusive } = await import('./packages/entry/lib/flock.js');
    assert.equal(await tryLockExclusive(7), undefined);
    await assert.rejects(tryLockExclusive(8), { code: 'EAGAIN', errno: 11, syscall: 'flock' });
    assert.equal(loads, 1);
  `);
});

test('Android missing bindings reject acquisition without caching a failed load', () => {
  run(`
    let loads = 0;
    process.dlopen = () => { loads++; throw Object.assign(new Error('missing'), { code: 'ERR_DLOPEN_FAILED' }); };
    const { tryLockExclusive } = await import('./packages/entry/lib/flock.js');
    await assert.rejects(tryLockExclusive(7), { code: 'ERR_DLOPEN_FAILED' });
    await assert.rejects(tryLockExclusive(7), { code: 'ERR_DLOPEN_FAILED' });
    assert.equal(loads, 2);
  `);
});

test('unqualified Android architectures reject before native loading', () => {
  run(`
    Object.defineProperty(process, 'arch', { value: 'x64' });
    process.dlopen = () => { throw new Error('must not load'); };
    const { tryLockExclusive } = await import('./packages/entry/lib/flock.js');
    await assert.rejects(tryLockExclusive(7), { code: 'ERR_FLOCK_UNSUPPORTED_PLATFORM', syscall: 'flock' });
  `);
});
