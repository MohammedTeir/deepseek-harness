// Real Linux Node-API wrapper qualification, never Android compatibility evidence.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fork } from 'node:child_process';
import { getSystemErrorName } from 'node:util';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const binary = process.argv[2];
const binding = require(binary);
const publish = (parent, source, target) => new Promise((resolve,reject) => binding.publish(parent,source,target,(error,operation) => {
  if (error === 0) resolve();
  else reject(Object.assign(new Error(getSystemErrorName(-error)), { code:getSystemErrorName(-error), syscall:operation }));
}));
const sync = async directory => { const handle=await fs.open(directory,'r'); try { await handle.sync(); } finally { await handle.close(); } };
const stage = async (directory,name,bytes) => { const handle=await fs.open(path.join(directory,name),'wx',0o600); try { await handle.writeFile(bytes); await handle.sync(); } finally { await handle.close(); } };
if (process.argv[3] === 'child') {
  const directory=process.argv[4], id=process.argv[5];
  await stage(directory,'stage-'+id,'complete publisher '+id+'\n');
  process.send({ready:true,pid:process.pid});
  process.once('message',async () => {
    try { await publish(directory,'stage-'+id,'final'); await sync(directory); process.send({pid:process.pid,code:'OK'}); }
    catch(error) { process.send({pid:process.pid,code:error.code}); }
    process.disconnect();
  });
} else {
  const root=await fs.mkdtemp(path.join(os.tmpdir(),'harness-atomic-addon-'));
  const children=new Set();
  try {
    await stage(root,'pending','original\n');
    const before=await fs.stat(path.join(root,'pending'));
    await publish(root,'pending','final'); await sync(root);
    assert.equal(await fs.readFile(path.join(root,'final'),'utf8'),'original\n');
    assert.equal((await fs.stat(path.join(root,'final'))).ino,before.ino);
    await assert.rejects(fs.stat(path.join(root,'pending')),{code:'ENOENT'});
    await stage(root,'second','must not replace\n');
    const identity=await fs.stat(path.join(root,'final'),{bigint:true});
    await assert.rejects(publish(root,'second','final'),{code:'EEXIST',syscall:'renameat2'});
    const after=await fs.stat(path.join(root,'final'),{bigint:true});
    for(const key of ['ino','dev','mode','uid','gid','size','mtimeNs','ctimeNs']) assert.equal(after[key],identity[key]);
    assert.equal(await fs.readFile(path.join(root,'second'),'utf8'),'must not replace\n');
    await assert.rejects(publish(root,'missing','new'),{code:'ENOENT',syscall:'fstatat'});
    await fs.symlink('final',path.join(root,'alias'));
    await assert.rejects(publish(root,'alias','new'),{code:'EINVAL'});
    await assert.rejects(publish(root,'second','alias'),{code:'EEXIST'});
    await assert.rejects(publish(root,'../escape','new'),{code:'EINVAL'});
    await assert.rejects(publish(root,'second','a/b'),{code:'EINVAL'});
    await assert.rejects(publish(root,'second','second'),{code:'EINVAL'});
    await assert.rejects(publish(root+'/.','second','new'),{code:'EINVAL'});
    await assert.rejects(publish(root,'bad\0name','new'),{code:'EINVAL'});
    await fs.chmod(root,0o500);
    try { await assert.rejects(publish(root,'second','new'),{code:'EACCES'}); }
    finally { await fs.chmod(root,0o700); }
    const rounds=[];
    for(let round=0;round<4;round++) {
      const directory=path.join(root,'round-'+round); await fs.mkdir(directory,{mode:0o700});
      const launched=[];
      const ready=[];
      const results=[];
      for(let id=0;id<8;id++) {
        const child=fork(fileURLToPath(import.meta.url),[binary,'child',directory,String(id)],{stdio:['ignore','ignore','inherit','ipc']});
        children.add(child); launched.push(child);
        ready.push(new Promise((resolve,reject) => {
          child.on('message',message => {if(message.ready) resolve(message);});
          child.once('error',reject); child.once('exit',code => {if(code!==0) reject(new Error('Publisher exited '+code));});
        }));
        results.push(new Promise((resolve,reject) => {
          child.on('message',message => {if(message.code) resolve(message);});
          child.once('error',reject); child.once('exit',code => {if(code!==0) reject(new Error('Publisher exited '+code));});
        }));
      }
      const pids=(await Promise.all(ready)).map(value=>value.pid); assert.equal(new Set(pids).size,8);
      for(const child of launched) child.send('publish');
      const values=await Promise.all(results);
      await Promise.all(launched.map(child=>new Promise((resolve,reject)=>{
        if(child.exitCode!==null) { children.delete(child); resolve(); return; }
        child.once('exit',code=>{ children.delete(child); code===0?resolve():reject(new Error('Publisher exit '+code)); });
      })));
      assert.equal(values.filter(x=>x.code==='OK').length,1);
      assert.equal(values.filter(x=>x.code==='EEXIST').length,7);
      assert.match(await fs.readFile(path.join(directory,'final'),'utf8'),/^complete publisher [0-7]\n$/);
      rounds.push({round,pids,successes:1,collisions:7});
    }
    const result={schemaVersion:1,platform:process.platform,node:process.version,realNodeApiWrapper:true,
      publication:true,sourceConsumed:true,collisionProtected:true,errorsPropagated:true,rounds,
      androidVerified:false,gate2Passed:false};
    await fs.writeFile(process.argv[3],JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify(result));
  } finally {
    await Promise.all([...children].map(child=>new Promise(resolve=>{
      child.once('exit',resolve);child.kill('SIGKILL');
    })));
    await fs.rm(root,{recursive:true,force:true});
  }
}
