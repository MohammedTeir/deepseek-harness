/** Prepared-file publication; Android consumes staging, other platforms retain its hardlink. */
import { link } from 'node:fs/promises'
import { basename, dirname, isAbsolute, normalize } from 'node:path'

interface PublishBinding {
  publish(parent: string, source: string, target: string, callback: (errno: number, operation: string) => void): void
}

/**
 * Publish a fully prepared file without replacing an occupied destination.
 * Android ARM64 uses the carrier's fixed native binding and one pinned private directory;
 * other platforms retain the original fs.link behavior. The caller synchronizes file data
 * before calling, then the destination directory, and removes its staging name with ENOENT tolerated.
 * No sync or rollback is performed here; a failure can follow visible publication.
 * Trusted staging ownership is required; this is not isolation from hostile same-UID writers.
 * @param source - Owned staging file; consumed on Android success and retained elsewhere.
 * @param destination - Absent destination. Android requires the same normalized parent and safe basenames.
 * @returns Resolution after publication only. EEXIST and unsupported/syscall/loader failures reject without fallback.
 */
export async function publishPreparedFileExclusive(source: string, destination: string): Promise<void> {
  if (process.platform !== 'android') return link(source, destination)
  if (process.arch !== 'arm64') {
    throw Object.assign(new Error('Android publication requires ARM64'), { code: 'ERR_ATOMIC_PUBLISH_UNSUPPORTED_PLATFORM' })
  }
  const parent = dirname(source)
  if (!isAbsolute(source) || !isAbsolute(destination) || normalize(source) !== source || normalize(destination) !== destination
    || parent !== dirname(destination)) {
    throw Object.assign(new Error('Android publication requires one normalized absolute parent directory'), { code: 'EINVAL' })
  }
  const nativeModule = { exports: {} }
  process.dlopen(nativeModule, 'libharness_atomic.so')
  const native = nativeModule.exports as PublishBinding
  const { getSystemErrorName } = await import('node:util')
  await new Promise<void>((resolve, reject) => {
    native.publish(parent, basename(source), basename(destination), (errno, operation) => {
      if (errno === 0) { resolve(); return }
      const code = getSystemErrorName(-errno)
      reject(Object.assign(new Error(`${code}: ${operation} failed during exclusive publication`), {
        code, errno: -errno, syscall: operation, path: source, dest: destination,
      }))
    })
  })
}
