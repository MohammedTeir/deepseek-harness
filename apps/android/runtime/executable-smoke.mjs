import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';
import { readProcIdentity } from './proc-identity.mjs';

let stage = 'kernel-identity';
let activeChild;
// The Android owner sends TERM first; reap the owned child before exiting.
process.once('SIGTERM', () => {
  if (activeChild?.pid) {
    activeChild.once('close', () => process.exit(143));
    activeChild.kill('SIGKILL');
  } else process.exit(143);
});

async function main() {
  const output = process.argv[2];
  if (!output || !path.isAbsolute(output)) throw new Error('Absolute output path required');
  const identity = readProcIdentity();
  stage = 'child-node';
  const childScript = path.join(path.dirname(fileURLToPath(import.meta.url)), 'child-node.mjs');
  const childResult = await new Promise((resolve, reject) => {
    activeChild = execFile(process.execPath, [childScript],
      { timeout: 10000, maxBuffer: 16384, killSignal: 'SIGKILL' }, (error, stdout, stderr) => {
        activeChild = undefined;
        if (error) reject(new Error(`Child Node failed: ${error.message}\n${stderr}`));
        else resolve({ exitCode: 0, stdout, stderr });
      });
  });
  const child = JSON.parse(childResult.stdout);
  if (child.pid === identity.pid || child.parentPid !== identity.pid || child.uid !== identity.uid
    || child.execPath !== process.execPath || child.node !== process.version
    || child.platform !== process.platform || child.arch !== process.arch || child.cwd !== process.cwd()) {
    throw new Error('Child Node identity/runtime mismatch');
  }
  stage = 'original-api-probe';
  const { probeCompletion } = await import('./smoke.mjs');
  await probeCompletion;
  if (process.exitCode) return;
  stage = 'combined-result';
  const result = JSON.parse(fs.readFileSync(output, 'utf8'));
  Object.assign(result, { executionStrategy: 'packaged-executable', kernelIdentity: identity,
    childNodeLaunch: 'passed', childNode: child, childResult });
  fs.writeFileSync(output + '.pending', JSON.stringify(result), { mode: 0o600 });
  fs.renameSync(output + '.pending', output);
}
main().catch(error => {
  console.error(error.stack ?? String(error));
  const output = process.argv[2];
  if (output && path.isAbsolute(output)) {
    try {
      fs.writeFileSync(output + '.pending', JSON.stringify({ schemaVersion: 1, stage,
        failure: error.message ?? String(error), harnessStarted: false }), { mode: 0o600 });
      fs.renameSync(output + '.pending', output);
    } catch (writeError) { console.error(writeError.message); }
  }
  process.exitCode = 1;
});
