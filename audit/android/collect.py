"""Read-only lockfile graph and installed-payload audit; never executes dependencies."""
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
lock = yaml.safe_load((ROOT / 'pnpm-lock.yaml').read_text())
importers = lock['importers']
snapshots = lock['snapshots']
packages = lock['packages']
nodes = {}
edges = []
errors = []
for name, data in importers.items():
    manifest = json.loads((ROOT / name / 'package.json').read_text())
    nodes['workspace:' + name] = {'kind': 'workspace', 'path': name, 'manifest': manifest}
for name, data in snapshots.items():
    key = name.split('(')[0]
    if key not in packages:
        errors.append({'snapshot': name, 'missingMetadata': key})
    nodes['package:' + name] = {'kind': 'package', 'key': key, 'metadata': packages.get(key),
                              'transitivePeerDependencies': data.get('transitivePeerDependencies', [])}
for prefix, source in [('workspace:', importers), ('package:', snapshots)]:
    for name, data in source.items():
        for kind in ['dependencies', 'devDependencies', 'optionalDependencies']:
            for dep, value in data.get(kind, {}).items():
                version = value['version'] if isinstance(value, dict) else value
                if version.startswith('link:'):
                    path = os.path.normpath(os.path.join(name if prefix == 'workspace:' else '.', version[5:]))
                    target = 'workspace:' + path
                else:
                    target = 'package:' + (version if version in snapshots else dep + '@' + version)
                if target not in nodes:
                    errors.append({'from': prefix + name, 'dependency': dep, 'version': version, 'target': target})
                edges.append({'from': prefix + name, 'to': target, 'name': dep, 'kind': kind})
# Peers are declarations, not fabricated extra install edges. Resolved peer contexts
# remain in snapshot IDs and pnpm's resolved dependency entries.
installed = collections.defaultdict(list)
store = ROOT / 'node_modules/.pnpm'
for pattern in ['*/node_modules/*/package.json', '*/node_modules/@*/*/package.json']:
    for path in store.glob(pattern):
        if path.parent.is_symlink():
            continue
        manifest = json.loads(path.read_text())
        if manifest.get('name') and manifest.get('version'):
            installed[manifest['name'] + '@' + manifest['version']].append((path.parent, manifest))
records = {}
for key, metadata in packages.items():
    name, version = key.rsplit('@', 1)
    candidates = installed.get(name + '@' + metadata.get('version', version), [])
    record = {'metadata': metadata, 'installed': bool(candidates), 'signals': [], 'payloads': [], 'manifests': []}
    if not candidates:
        record['inspection'] = 'NOT INSTALLED: lock metadata only; payload unverified'
    for directory, manifest in candidates:
        record['manifests'].append({k: manifest[k] for k in ['name', 'version', 'scripts', 'bin', 'os', 'cpu', 'libc', 'gypfile', 'binary', 'bundledDependencies', 'bundleDependencies', 'dependencies', 'optionalDependencies', 'peerDependencies', 'license'] if k in manifest})
        for parent, dirs, files in os.walk(directory, followlinks=False):
            dirs[:] = [d for d in dirs if d != '.git' and not (Path(parent) / d).is_symlink()]
            for filename in files:
                file = Path(parent) / filename
                if file.is_symlink():
                    continue
                relative = str(file.relative_to(directory))
                if file.suffix in {'.c', '.cc', '.cpp', '.h', '.rs', '.gyp', '.gypi', '.s', '.S', '.asm', '.m', '.mm'} or filename in {'CMakeLists.txt', 'Cargo.toml', 'binding.gyp'}:
                    record['signals'].append(relative)
                with file.open('rb') as stream:
                    magic = stream.read(4)
                binary = {b'\x7fELF': 'ELF', b'\x00asm': 'WASM', b'\xcf\xfa\xed\xfe': 'Mach-O', b'\xfe\xed\xfa\xcf': 'Mach-O'}.get(magic)
                if magic[:2] == b'MZ':
                    binary = 'PE'
                if binary or file.suffix in {'.node', '.so', '.dll', '.dylib', '.exe', '.a', '.lib'}:
                    item = {'path': relative, 'format': binary or 'extension-only', 'size': file.stat().st_size}
                    if binary == 'ELF':
                        report = subprocess.run(['readelf', '-h', '-l', '-d', '-W', str(file)],capture_output=True,text=True)
                        if report.returncode:
                            errors.append({'readelf': relative, 'error': report.stderr})
                        else:
                            item['machine'] = re.findall(r'Machine:\s*(.*)', report.stdout)
                            item['interpreter'] = re.findall(r'Requesting program interpreter: (.*?)\]',report.stdout)
                            item['needed'] = re.findall(r'\(NEEDED\).*\[(.*?)\]',report.stdout)
                    record['payloads'].append(item)
        record['signals'] = sorted(set(record['signals']))
    records[key] = record
adj = collections.defaultdict(list)
for edge in edges:
    if edge['kind'] != 'devDependencies': adj[edge['from']].append(edge['to'])
closures = {}
for root in ['apps/cli', 'apps/web', 'apps/desktop', 'apps/desktop-host', 'packages/bundle/base', 'packages/bundle/sdk-minimal', 'packages/bundle/web-app']:
    seen=set(); todo=['workspace:'+root]
    while todo:
        n=todo.pop()
        if n in seen: continue
        seen.add(n);todo.extend(adj[n])
    closures[root]=sorted(seen)
native_nodes = {}
native_edges = []
for key, record in records.items():
    for binary in record['payloads']:
        identity = key + '::' + binary['path']
        native_nodes[identity] = {'package': key, **binary}
        for needed in binary.get('needed', []):
            native_edges.append({'from': identity, 'library': needed,
                                 'resolution': 'loader/OS dependent; not established for Android'})
(OUT / 'native-library-graph.json').write_text(json.dumps(
    {'nodes': native_nodes, 'neededEdges': native_edges}, indent=2, sort_keys=True) + '\n')
workspace = yaml.safe_load((ROOT / 'pnpm-workspace.yaml').read_text())
(OUT / 'workspace-policy.json').write_text(json.dumps({
    'allowBuilds': workspace['allowBuilds'], 'overrides': lock['overrides'],
    'patchedDependencies': lock['patchedDependencies'], 'workspaceGlobs': workspace['packages']
}, indent=2, sort_keys=True) + '\n')
summary={'importers':len(importers),'packageMetadata':len(packages),'resolvedSnapshots':len(snapshots),'edges':len(edges),'unresolved':len(errors),'installedPackageIdentities':sum(v['installed'] for v in records.values()),'platformGated':sum(bool(v.get('os') or v.get('cpu') or v.get('libc')) for v in packages.values()),'closures':{k:len(v) for k,v in closures.items()}}
for filename, data in [('dependency-graph.json',{'lockfileSha256':hashlib.sha256((ROOT/'pnpm-lock.yaml').read_bytes()).hexdigest(),'nodes':nodes,'edges':edges,'closures':closures,'errors':errors}),('package-inspection.json',records),('graph-summary.json',summary)]:
    (OUT/filename).write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
print(json.dumps(summary,indent=2))
if errors: print(json.dumps(errors[:15],indent=2));raise SystemExit(1)
