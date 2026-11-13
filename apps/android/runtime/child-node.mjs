import { readProcIdentity } from './proc-identity.mjs';

// Fixed child program; no caller-provided command, code, or file operations.
process.stdout.write(JSON.stringify({ ...readProcIdentity(), node: process.version,
  platform: process.platform, arch: process.arch, execPath: process.execPath, cwd: process.cwd() }));
