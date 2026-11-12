// Bounded diagnostics for the original JSONL prerequisites; never a session-store replacement.
import fs from 'node:fs/promises';
import path from 'node:path';

export function describeFailure(error, depth = 0) {
  if (depth > 3) return { message: 'Nested diagnostic limit' };
  const result = { name: error?.name ?? 'Error', message: String(error?.message ?? error).slice(0, 2048) };
  for (const key of ['code', 'errno', 'syscall', 'path', 'dest']) {
    if (typeof error?.[key] === 'string' || typeof error?.[key] === 'number') result[key] = error[key];
  }
  if (error?.cause) result.cause = describeFailure(error.cause, depth + 1);
  if (Array.isArray(error?.errors)) result.errors = error.errors.slice(0, 4).map(item => describeFailure(item, depth + 1));
  return result;
}

export async function storagePrerequisites(base) {
  const directory = await fs.mkdtemp(path.join(base, 'storage-check-'));
  let stage = 'directory-sync';
  try {
    const syncDirectory = async () => {
      const handle = await fs.open(directory, 'r');
      try { await handle.sync(); } finally { await handle.close(); }
    };
    await syncDirectory();
    stage = 'file-sync';
    const pending = path.join(directory, 'pending');
    const published = path.join(directory, 'published');
    const handle = await fs.open(pending, 'wx', 0o600);
    try { await handle.writeFile('harness-storage-proof\n'); await handle.sync(); }
    finally { await handle.close(); }
    stage = 'exclusive-hardlink-publish';
    await fs.link(pending, published);
    const original = await fs.stat(pending);
    const linked = await fs.stat(published);
    if (original.ino !== linked.ino || original.dev !== linked.dev) throw new Error('Published inode differs');
    let rejected = false;
    try { await fs.link(pending, published); }
    catch (error) { if (error.code !== 'EEXIST') throw error; rejected = true; }
    if (!rejected) throw new Error('Exclusive publication overwrote an existing path');
    await syncDirectory();
    await fs.unlink(pending);
    if (await fs.readFile(published, 'utf8') !== 'harness-storage-proof\n') throw new Error('Published bytes differ');
    return { directorySync: true, fileSync: true, exclusiveHardlinkPublish: true, existingPathRejected: true };
  } catch (error) {
    error.storageStage = stage;
    throw error;
  } finally { await fs.rm(directory, { recursive: true, force: true }); }
}

export async function sessionInventory(root) {
  const result = { root, entries: [] };
  async function visit(directory, depth) {
    if (depth > 3 || result.entries.length >= 48) return;
    let entries;
    try { entries = await fs.readdir(directory, { withFileTypes: true }); }
    catch (error) { result.entries.push({ path: path.relative(root, directory) || '.', failure: describeFailure(error) }); return; }
    for (const entry of entries.slice(0, 16)) {
      if (result.entries.length >= 48) return;
      const full = path.join(directory, entry.name);
      const stat = await fs.lstat(full);
      result.entries.push({ path: path.relative(root, full), bytes: stat.size,
        direntDirectory: entry.isDirectory(), statDirectory: stat.isDirectory(), symbolicLink: stat.isSymbolicLink() });
      if (stat.isDirectory() && !stat.isSymbolicLink()) await visit(full, depth + 1);
    }
  }
  await visit(root, 0);
  return result;
}

export async function shutdownConfirmed(client) {
  // Unlike close()'s best-effort exchange, this reply must not be suppressed.
  await client.request('shutdown', undefined, 15000);
  await client.close();
}
