// Compile local adapters only; runtime libraries retain their original class identities.
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs/promises';
import crypto from 'node:crypto';
const root = fileURLToPath(new URL('../../../', import.meta.url));
const require = createRequire(await fs.realpath(path.join(root, 'node_modules/tsx/package.json')));
const { build } = require('esbuild');
const directory = 'apps/android/runtime/node-pty-proof';
const result = await build({ absWorkingDir: root, entryPoints: {
  'terminal-backend.bundle': directory + '/terminal-backend.ts', 'terminal-handle.bundle': directory + '/terminal-handle.ts',
}, outdir: directory, outExtension: { '.js': '.mjs' }, bundle: true, format: 'esm', platform: 'node', target: 'node24', packages: 'external', metafile: true });
const files = [...Object.keys(result.metafile.inputs), ...Object.keys(result.metafile.outputs)];
const hashes = {};
for (const name of files) hashes[name] = crypto.createHash('sha256').update(await fs.readFile(path.join(root, name))).digest('hex');
console.log(JSON.stringify({ scope: 'local fixed adapters only', filesSha256: hashes }, null, 2));
