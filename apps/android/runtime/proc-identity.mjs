import fs from 'node:fs';

/** Read identity from this process's kernel status; missing data fails closed. */
export function readProcIdentity() {
  const status = fs.readFileSync('/proc/self/status', 'utf8');
  const pid = /^Pid:\s+(\d+)$/m.exec(status);
  const parent = /^PPid:\s+(\d+)$/m.exec(status);
  const uid = /^Uid:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$/m.exec(status);
  if (!pid || !parent || !uid) throw new Error('Kernel process identity is unavailable');
  const ids = uid.slice(1).map(Number);
  if (ids.some(value => value !== ids[0]) || ids[0] === 0) throw new Error('Expected one non-root app identity');
  const result = { pid: Number(pid[1]), parentPid: Number(parent[1]), uid: ids[0], source: '/proc/self/status' };
  if (result.pid !== process.pid || result.parentPid !== process.ppid) throw new Error('Kernel/Node PID mismatch');
  return result;
}
