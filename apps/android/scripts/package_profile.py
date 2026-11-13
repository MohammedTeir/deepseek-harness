"""Package observed original-profile startup/session files, not a complete runtime distribution.

Only successful read opens in a fresh multi-process strace are admitted. Native
Linux flock is retained solely for a separate host validation tree, never the APK.
The existing full dependency audit remains authoritative for broader features.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[3]
ANDROID = ROOT / 'apps/android'
HOST_NATIVE = {'native/system/packages/linux-x64/bin/glibc/system.node',
    'node_modules/.pnpm/node-addon-require-builtin-linux-x64-gnu@0.1.9/node_modules/node-addon-require-builtin-linux-x64-gnu/prebuilt/linux-x64-gnu-napi-v9.node'}
OPEN = re.compile(r'openat\([^,]+, ("(?:[^"\\]|\\.)*"), ([^)]*)\)\s+=\s+(\d+)')
LINK = re.compile(r'readlink(?:at)?\((?:[^,]+, )?("(?:[^"\\]|\\.)*"), ("(?:[^"\\]|\\.)*")')


def relative(path, root):
    """Reject reads/links outside the source tree, including resolved aliases."""
    return path.relative_to(root).as_posix()


def collect(root, traces):
    """Return canonical successful-read files and contained relative symlinks."""
    files = set()
    links = {}
    for trace in traces:
        for line in trace.read_text().splitlines():
            opened = OPEN.search(line)
            if opened and 'O_RDONLY' in opened[2]:
                path = Path(ast.literal_eval(opened[1]))
                if path.is_absolute() and path.is_relative_to(root) and path.is_file():
                    if path.name.startswith('.env') or path.name == '.credentials.yaml':
                        raise ValueError('Credential files must not enter the interpreted image')
                    canonical = path.resolve(strict=True)
                    name = relative(canonical, root)
                    if canonical.suffix not in {'.js', '.mjs', '.cjs', '.json', '.yaml', '.yml', '.wasm', '.map', '.node'}:
                        raise ValueError(f'Unreviewed file type read by profile: {name}')
                    files.add(name)
            linked = LINK.search(line)
            if linked:
                path = Path(ast.literal_eval(linked[1]))
                if not path.is_absolute() or not path.is_relative_to(root):
                    continue
                # Canonicalize the parent only; preserve this final symlink.
                source = path.parent.resolve(strict=True) / path.name
                target = path.resolve(strict=True)
                key = relative(source, root)
                destination = relative(target, root)
                if key in links and links[key] != destination:
                    raise ValueError(f'Symlink changed during observation: {key}')
                links[key] = destination
    if not files or not links:
        raise ValueError('No profile files or links observed')
    return files, links


def validate_archive(archive, manifest):
    """Reject path escape, extra files, changed bytes and native code in the image."""
    expected = manifest['files']
    with zipfile.ZipFile(archive) as zip:
        names = zip.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected) | {'image-manifest.json'}:
            raise ValueError('Archive entries differ from manifest')
        if json.loads(zip.read('image-manifest.json')) != manifest:
            raise ValueError('Archive manifest differs from inspected metadata')
        if 'apps/android/tests/command-profile-reference.mjs' in expected:
            raise ValueError('Host approval fixture must not enter Android image')
        for name, digest in expected.items():
            if name.startswith('/') or '\\' in name or any(p in {'', '.', '..'} for p in name.split('/')):
                raise ValueError('Unsafe archive path')
            data = zip.read(name)
            if data.startswith(b'\x7fELF') or hashlib.sha256(data).hexdigest() != digest:
                raise ValueError('Native or changed interpreted image file')


def validate_host_qualification(directory):
    """Reject missing/stale relocation proof before normal APK preparation."""
    marker=json.loads((directory/'profile-qualification.json').read_text())
    image=directory/'profile-image.zip'
    if marker.get('imageSha256') != hashlib.sha256(image.read_bytes()).hexdigest():
        raise ValueError('Host profile qualification does not match image')
    for name,key in [('relocated-result.json','sessionRecoveredAcrossRuntimeRestart'),
                     ('relocated-repeat-result.json','previousRunSessionRecovered')]:
        data=(directory/name).read_bytes()
        if marker.get('resultSha256',{}).get(name) != hashlib.sha256(data).hexdigest():
            raise ValueError('Host profile qualification result changed')
        result=json.loads(data)
        if result.get('platform') != 'linux' or not result.get('harnessStarted') or not result.get(key):
            raise ValueError('Real host profile qualification incomplete')
    command_result = (directory/'command-relocated-result.json').read_bytes()
    if marker.get('resultSha256', {}).get('command-relocated-result.json') != hashlib.sha256(command_result).hexdigest():
        raise ValueError('Command qualification digest mismatch')
    command_proof = json.loads(command_result)
    if not command_proof.get('originalRegistryAndPipeline') or not command_proof.get('sessionRecoveredAcrossRuntimeRestart') or command_proof.get('hostQualification', {}).get('processLaunches') != 1:
        raise ValueError('Original command qualification missing')
    relocation=json.loads((directory/'relocation.json').read_text())
    if not relocation.get('imageOutsideCheckout') or not relocation.get('stateOutsideCheckout'):
        raise ValueError('Host profile must qualify outside checkout')


def build(output):
    """Trace the real public SDK reference and package its bounded dependency image."""
    if output.exists():
        raise ValueError('Output must be a new directory')
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='android-profile-trace-') as temporary:
        temp = Path(temporary)
        prefix = temp / 'access'
        command = ['strace', '-ff', '-qq', '-s', '4096', '-e', 'trace=openat,readlink,readlinkat',
                   '-o', str(prefix), 'node', str(ANDROID / 'tests/host-profile-reference.mjs'),
                   str(temp / 'reference.json'), '--no-execution']
        observed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        (output / 'trace-run.txt').write_text(observed.stdout + observed.stderr)
        if observed.returncode:
            raise RuntimeError(f'Original profile trace failed: {observed.stderr}')
        command_prefix = temp / 'command-access'
        command_trace = ['strace', '-ff', '-qq', '-s', '4096', '-e', 'trace=openat,readlink,readlinkat',
                         '-o', str(command_prefix), 'node', str(ANDROID/'tests/command-profile-reference.mjs'),
                         str(temp/'command-reference.json')]
        command_observed = subprocess.run(command_trace, cwd=ROOT, capture_output=True, text=True, timeout=120)
        (output/'command-trace-run.txt').write_text(command_observed.stdout + command_observed.stderr)
        if command_observed.returncode:
            raise RuntimeError(f'Original command profile trace failed: {command_observed.stderr}')
        command_files, command_links = collect(ROOT, sorted(temp.glob('command-access.*')))
        files, links = collect(ROOT, sorted(temp.glob('access.*')))
        files |= command_files
        for key, value in command_links.items():
            if key in links and links[key] != value:
                raise ValueError(f'Command alias differs: {key}')
            links[key] = value
        # Host tooling is not a phone executable. Android uses the APK's Bionic binding.
        natives = {name for name in files if name.endswith('.node')}
        if natives != HOST_NATIVE:
            raise ValueError(f'Unreviewed native dependency set: {sorted(natives)}')
        files -= natives
        files |= {'LICENSE', 'THIRD_PARTY_NOTICES.md', 'apps/android/runtime/profile/no-execution.patch.yml',
                  'apps/android/runtime/profile-smoke.mjs', 'apps/android/runtime/proc-identity.mjs',
                  'apps/android/runtime/session-diagnostics.mjs', 'native/system/packages/entry/lib/publish.js',
                  'native/system/packages/entry/package.json', 'apps/android/runtime/profile/command-proof.patch.yml',
                  'apps/android/runtime/command-smoke.mjs', 'apps/android/runtime/command-plugin.mjs', 'apps/android/runtime/android-subprocess.mjs',
                  'apps/android/runtime/command-wire.mjs'}
        # Automated host decision fixture is not an Android execution component.
        files.discard('apps/android/tests/command-profile-reference.mjs')
        packages = set()
        for name in list(files):
            directory = (ROOT / name).parent
            while directory != ROOT.parent:
                manifest = directory / 'package.json'
                if manifest.is_file():
                    files.add(relative(manifest, ROOT))
                    packages.add(relative(manifest, ROOT))
                    for pattern in ('LICENSE*', 'LICENCE*', 'NOTICE*', 'COPYING*'):
                        for notice in directory.glob(pattern):
                            if notice.is_file():
                                files.add(relative(notice.resolve(strict=True), ROOT))
                    break
                directory = directory.parent
        payload = output / 'image'
        payload.mkdir()
        digests = {}
        for name in sorted(files):
            source = ROOT / name
            data = source.read_bytes()
            if data.startswith(b'\x7fELF'):
                raise ValueError(f'Native executable is forbidden in interpreted image: {name}')
            destination = payload / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            digests[name] = hashlib.sha256(data).hexdigest()
        carrier = ANDROID/'runtime/require-builtin-carrier'
        for source in sorted(carrier.iterdir()):
            name='node_modules/node-addon-require-builtin-android-arm64/'+source.name
            data=source.read_bytes()
            destination=payload/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(data)
            files.add(name)
            digests[name]=hashlib.sha256(data).hexdigest()
        manifest = dict(schemaVersion=1,scope='Observed original sdk-minimal startup/session and fixed-command qualification; not full distribution',
                        completeDependencyDistribution=False,files=dict(sorted(digests.items())),links=dict(sorted(links.items())),
                        directories=sorted({target for target in links.values() if (ROOT/target).is_dir()}),
                        packageManifests=sorted(packages),excludedHostNative=sorted(HOST_NATIVE),
                        modelRequestExecuted=False,androidVerified=False,gate2Passed=False)
        (output / 'image-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        archive = output / 'profile-image.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zip:
            for name in sorted(files):
                entry=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
                entry.compress_type=zipfile.ZIP_DEFLATED
                zip.writestr(entry,(payload/name).read_bytes())
            entry=zipfile.ZipInfo('image-manifest.json',date_time=(1980,1,1,0,0,0))
            entry.compress_type=zipfile.ZIP_DEFLATED
            zip.writestr(entry,json.dumps(manifest,separators=(',',':'),sort_keys=True))
        validate_archive(archive,manifest)
        shutil.copy2(temp/'reference.json',output/'host-reference.json')
        host = temp / 'host-validation'
        if host.resolve().is_relative_to(ROOT):
            raise ValueError('Relocation validation must run outside the checkout')
        state = temp / 'state'
        state.mkdir()
        shutil.copytree(payload,host)
        for name in sorted(natives):
            destination = host/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/name,destination)
        import os
        for name, target in sorted(links.items()):
            destination=host/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.symlink_to(os.path.relpath(host/target,destination.parent),target_is_directory=(ROOT/target).is_dir())
        env={key:value for key,value in os.environ.items() if key in {'PATH','TMPDIR','LANG'}}
        result=subprocess.run(['node',str(host/'apps/android/runtime/profile-smoke.mjs'),str(state/'result.json')],
                              cwd=host,env=env,capture_output=True,text=True,timeout=100)
        (output/'relocated-run.txt').write_text(result.stdout+result.stderr)
        if result.returncode:
            raise RuntimeError(f'Relocated original profile failed: {result.stderr}')
        shutil.copy2(state/'result.json',output/'relocated-result.json')
        recovered=json.loads((state/'result.json').read_text())
        if not recovered.get('harnessStarted') or not recovered.get('sessionRecoveredAcrossRuntimeRestart'):
            raise ValueError('Relocated profile/session evidence incomplete')
        repeat=subprocess.run(['node',str(host/'apps/android/runtime/profile-smoke.mjs'),str(state/'repeat-result.json')],
                              cwd=host,env=env,capture_output=True,text=True,timeout=100)
        (output/'relocated-repeat-run.txt').write_text(repeat.stdout+repeat.stderr)
        if repeat.returncode or not json.loads((state/'repeat-result.json').read_text()).get('previousRunSessionRecovered'):
            raise RuntimeError(f'Relocated prior-run recovery failed: {repeat.stderr}')
        shutil.copy2(state/'repeat-result.json',output/'relocated-repeat-result.json')
        command_relocated = subprocess.run(['node', str(ANDROID/'tests/command-profile-reference.mjs'),
                                           str(output/'command-relocated-result.json'),
                                           str(host/'apps/android/runtime/command-smoke.mjs')],
                                          cwd=host, env=env, capture_output=True, text=True, timeout=120)
        (output/'command-relocated-run.txt').write_text(command_relocated.stdout+command_relocated.stderr)
        if command_relocated.returncode:
            raise RuntimeError(f'Relocated original command profile failed: {command_relocated.stderr}')
        (output/'relocation.json').write_text(json.dumps(dict(imageOutsideCheckout=True,stateOutsideCheckout=True,
            inheritedEnvironmentAllowlist=['PATH','TMPDIR','LANG'],originalHostNativeLibrariesOnly=True,androidNativeExecuted=False),indent=2)+'\n')
        qualification=dict(schemaVersion=1,hostOnly=True,androidVerified=False,
            imageSha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
            resultSha256={name:hashlib.sha256((output/name).read_bytes()).hexdigest()
                          for name in ['relocated-result.json','relocated-repeat-result.json','command-relocated-result.json']})
        (output/'profile-qualification.json').write_text(json.dumps(qualification,indent=2)+'\n')
        validate_host_qualification(output)
        print(json.dumps(dict(files=len(files),links=len(links),packages=len(packages),archiveBytes=archive.stat().st_size)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    build(parser.parse_args().output.resolve())
