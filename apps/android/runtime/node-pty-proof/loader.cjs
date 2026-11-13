// Dedicated qualification process only: adapt the original CJS native-loader seam.
// Synchronous initialization restores the original loader immediately afterward.
const path = require('node:path');
const fs = require('node:fs');
module.exports = function loadOriginalNodePty(packageRoot, addonPath) {
  if (!path.isAbsolute(packageRoot) || !path.isAbsolute(addonPath)) throw new Error('Absolute native-owned paths required');
  const root = fs.realpathSync(packageRoot);
  const addon = fs.realpathSync(addonPath);
  const utils = require(path.join(root, 'lib/utils.js'));
  const original = utils.loadNativeModule;
  const container = { exports: {} };
  process.dlopen(container, addon);
  utils.loadNativeModule = name => {
    if (name !== 'pty') throw new Error('Only the fixed pty binding is permitted');
    return { module: container.exports, dir: path.dirname(addon) };
  };
  try { return require(path.join(root, 'lib/index.js')); }
  finally { utils.loadNativeModule = original; }
};
