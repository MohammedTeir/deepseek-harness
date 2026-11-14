/*
 * Test-only Web Profile observation hook. NODE_OPTIONS loads this only when
 * the Android host-trace harness explicitly requests a module trace. It emits
 * JSONL and returns the original Node resolution/dlopen/realpath results.
 */
import fs from 'node:fs'
import { registerHooks, syncBuiltinESMExports } from 'node:module'
import { fileURLToPath } from 'node:url'

const tracePath = process.env.ANDROID_WEB_PROFILE_MODULE_TRACE
if (!tracePath) throw new Error('ANDROID_WEB_PROFILE_MODULE_TRACE is required by the module observer')
const traceFd = fs.openSync(tracePath, 'a')
const processIdentity = { pid: process.pid, parentPid: process.ppid }

function pathValue(value) {
  if (typeof value === 'string') return value
  if (Buffer.isBuffer(value)) return value.toString()
  if (value instanceof URL && value.protocol === 'file:') return fileURLToPath(value)
  return null
}

function safeUrl(value) {
  if (typeof value !== 'string') return null
  try {
    const url = new URL(value)
    if (url.protocol === 'file:') return fileURLToPath(url)
    if (url.protocol === 'node:') return url.href
    if (url.protocol === 'data:') return 'data:'
    return `${url.protocol}//${url.host}${url.pathname}`
  } catch {
    return value
  }
}

function safeSpecifier(value) {
  if (typeof value !== 'string') return String(value)
  if (/^(?:file|node|data|https?):/u.test(value)) return safeUrl(value)
  return value
}

function emit(record) {
  const line = `${JSON.stringify({ schemaVersion: 1, ...processIdentity, ...record })}\n`
  fs.writeSync(traceFd, line)
}

function codeOf(error) {
  return typeof error?.code === 'string' ? error.code : error?.name ?? 'Error'
}

registerHooks({
  resolve(specifier, context, nextResolve) {
    try {
      const result = nextResolve(specifier, context)
      emit({
        kind: 'resolve',
        specifier: safeSpecifier(specifier),
        parentURL: safeUrl(context.parentURL),
        resolvedURL: safeUrl(result.url),
        format: typeof result.format === 'string' ? result.format : null,
      })
      return result
    } catch (error) {
      emit({
        kind: 'resolve-failed',
        specifier: safeSpecifier(specifier),
        parentURL: safeUrl(context.parentURL),
        errorCode: codeOf(error),
      })
      throw error
    }
  },
})

const originalDlopen = process.dlopen
if (typeof originalDlopen === 'function') {
  process.dlopen = function (module, filename, ...args) {
    const observation = { kind: 'dlopen', filename: pathValue(filename) }
    try {
      const result = Reflect.apply(originalDlopen, this, [module, filename, ...args])
      emit({ ...observation, outcome: 'success' })
      return result
    } catch (error) {
      emit({ ...observation, outcome: 'error', errorCode: codeOf(error) })
      throw error
    }
  }
}

function recordRealpath(path, resolvedPath, error) {
  const record = { kind: 'realpath', path: pathValue(path) }
  if (error) {
    emit({ ...record, outcome: 'error', errorCode: codeOf(error) })
  } else {
    emit({ ...record, outcome: 'success', resolvedPath: pathValue(resolvedPath) })
  }
}

const originalRealpath = fs.realpath
fs.realpath = function (...args) {
  const callbackIndex = args.length - 1
  const callback = args[callbackIndex]
  if (typeof callback !== 'function') return Reflect.apply(originalRealpath, this, args)
  const path = args[0]
  const wrapped = function (...callbackArgs) {
    recordRealpath(path, callbackArgs[1], callbackArgs[0])
    return Reflect.apply(callback, this, callbackArgs)
  }
  const forwarded = [...args]
  forwarded[callbackIndex] = wrapped
  return Reflect.apply(originalRealpath, this, forwarded)
}

function wrapRealpathSync(original) {
  return function (...args) {
    const path = args[0]
    try {
      const resolved = Reflect.apply(original, this, args)
      recordRealpath(path, resolved)
      return resolved
    } catch (error) {
      recordRealpath(path, null, error)
      throw error
    }
  }
}

const originalRealpathSync = fs.realpathSync
const wrappedRealpathSync = wrapRealpathSync(originalRealpathSync)
if (typeof originalRealpathSync.native === 'function') {
  wrappedRealpathSync.native = wrapRealpathSync(originalRealpathSync.native)
}
fs.realpathSync = wrappedRealpathSync

const promiseRealpath = fs.promises.realpath
fs.promises.realpath = async function (...args) {
  const path = args[0]
  try {
    const resolved = await Reflect.apply(promiseRealpath, this, args)
    recordRealpath(path, resolved)
    return resolved
  } catch (error) {
    recordRealpath(path, null, error)
    throw error
  }
}

syncBuiltinESMExports()
