/** Real host publication and simulated Android loader policy; no Android ABI evidence. */
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtemp, writeFile, readFile, stat, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { publishPreparedFileExclusive } from '../packages/entry/lib/publish.js';

function android(body, flags=[]) {
  const result=spawnSync(process.execPath,[...flags,'--input-type=module','-e',`
    import assert from 'node:assert/strict';
    Object.defineProperty(process,'platform',{value:'android'});
    Object.defineProperty(process,'arch',{value:'arm64'});
    ${body}
  `],{encoding:'utf8',timeout:10000,cwd:new URL('..',import.meta.url)});
  assert.ifError(result.error); assert.equal(result.signal,null,result.stderr); assert.equal(result.status,0,result.stderr);
}

test('non-Android publication retains staging and rejects an existing destination',async()=>{
  const root=await mkdtemp(join(tmpdir(),'harness-publish-'));
  try {
    const source=join(root,'source'),destination=join(root,'destination');
    await writeFile(source,'complete'); await publishPreparedFileExclusive(source,destination);
    assert.equal((await stat(source)).ino,(await stat(destination)).ino);
    await writeFile(join(root,'second'),'different');
    await assert.rejects(publishPreparedFileExclusive(join(root,'second'),destination),{code:'EEXIST'});
    assert.equal(await readFile(destination,'utf8'),'complete');
  } finally { await rm(root,{recursive:true,force:true}); }
});

test('Android importing is lazy and disabled native loading rejects',()=>android(`
  const {publishPreparedFileExclusive}=await import('./packages/entry/lib/publish.js');
  await assert.rejects(publishPreparedFileExclusive('/private/source','/private/final'),{code:'ERR_DLOPEN_DISABLED'});
`,['--no-addons']));

test('Android rejects cross-directory and unqualified architectures before loading',()=>android(`
  process.dlopen=()=>{throw new Error('must not load');};
  const {publishPreparedFileExclusive}=await import('./packages/entry/lib/publish.js');
  await assert.rejects(publishPreparedFileExclusive('/a/source','/b/final'),{code:'EINVAL'});
  Object.defineProperty(process,'arch',{value:'x64'});
  await assert.rejects(publishPreparedFileExclusive('/a/source','/a/final'),{code:'ERR_ATOMIC_PUBLISH_UNSUPPORTED_PLATFORM'});
`));

test('Android uses a fixed SONAME and propagates unsupported and collision errno without fallback',()=>android(`
  let error=17;let calls=0;
  process.dlopen=(module,name)=>{assert.equal(name,'libharness_atomic.so');module.exports.publish=(parent,source,target,callback)=>{
    calls++;assert.equal(parent,'/private');assert.equal(source,'source');assert.equal(target,'final');setImmediate(callback,error,'renameat2');
  };};
  const {publishPreparedFileExclusive}=await import('./packages/entry/lib/publish.js');
  for(const [errno,code] of [[17,'EEXIST'],[38,'ENOSYS'],[22,'EINVAL'],[95,'ENOTSUP']]) {
    error=errno;await assert.rejects(publishPreparedFileExclusive('/private/source','/private/final'),{code,errno:-errno,syscall:'renameat2'});
  }
  error=0;await publishPreparedFileExclusive('/private/source','/private/final');assert.equal(calls,5);
`));
