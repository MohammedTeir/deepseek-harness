// Android carrier for the original addon; its upstream loader validates exported metadata.
'use strict';
if (process.platform !== 'android' || process.arch !== 'arm64') {
  throw new Error('The installed require-builtin carrier supports Android ARM64 only');
}
const binding = { exports: {} };
process.dlopen(binding, 'libharness_require_builtin.so');
module.exports = binding.exports;
