"""Summarize a host Web test's openat trace; this does not define an Android runtime image."""
import argparse
import ast
import glob
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
CHILD = re.compile(r'(?:clone3?|vfork|fork)\(.*\)\s+=\s+(\d+)\s*$')
RESUMED_CHILD = re.compile(r'<\.\.\. (?:clone3?|vfork|fork) resumed>.*\)\s+=\s+(\d+)\s*$')
OPEN = re.compile(r'openat\([^,]+, ("(?:[^"\\]|\\.)*"), ([^)]*)\)\s+=\s+(\d+)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace-glob', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--root-pid', type=int, help='select the built web-profile process and traced descendants')
    parser.add_argument('--overlay', type=Path, help='require the named repository overlay in the root launch')
    args = parser.parse_args()
    traces = sorted(glob.glob(args.trace_glob))
    if not traces:
        raise ValueError('No traces found')
    isolated = args.root_pid is not None
    if args.overlay is not None and not isolated:
        raise ValueError('Overlay verification requires a root process')
    overlay = args.overlay.resolve(strict=True) if args.overlay is not None else None
    if overlay is not None:
        overlay.relative_to(ROOT)
    if isolated:
        by_pid = {}
        for name in traces:
            suffix = name.rsplit('.', 1)[-1]
            if not suffix.isdecimal():
                raise ValueError('Isolated traces must end in a numeric process identifier')
            pid = int(suffix)
            if pid in by_pid:
                raise ValueError('Duplicate process trace')
            by_pid[pid] = name
        if args.root_pid not in by_pid:
            raise ValueError('Root process trace missing')
        root_text = Path(by_pid[args.root_pid]).read_text(errors='replace')
        if not any('execve(' in line and '/apps/cli/lib/bin.js"' in line
                   and '"--profile", "web"' in line and ' = 0' in line for line in root_text.splitlines()):
            raise ValueError('Root trace does not identify a successful built web-profile launch')
        if overlay is not None and not any('execve(' in line and json.dumps(str(overlay)) in line
                                           and ' = 0' in line for line in root_text.splitlines()):
            raise ValueError('Root launch does not include the requested overlay')
        pending = [args.root_pid]
        selected = set()
        while pending:
            pid = pending.pop()
            if pid in selected:
                continue
            if pid not in by_pid:
                raise ValueError(f'Trace for child {pid} is missing')
            selected.add(pid)
            for line in Path(by_pid[pid]).read_text(errors='replace').splitlines():
                match = CHILD.search(line) or RESUMED_CHILD.search(line)
                if match:
                    pending.append(int(match[1]))
        traces = [by_pid[pid] for pid in sorted(selected)]
    paths = set()
    native = set()
    digests = []
    for name in traces:
        contents = Path(name).read_bytes()
        digests.append(hashlib.sha256(contents).hexdigest())
        for line in contents.decode('utf-8', errors='replace').splitlines():
            match = OPEN.search(line)
            if not match or 'O_RDONLY' not in match[2]:
                continue
            try:
                filename = ast.literal_eval(match[1])
            except (SyntaxError, ValueError):
                continue
            if not filename.startswith(str(ROOT) + '/'):
                continue
            paths.add(filename)
            if filename.endswith('.node'):
                canonical = Path(os.path.realpath(filename))
                native.add(canonical.relative_to(ROOT).as_posix())
    if not paths:
        raise ValueError('No successful absolute checkout reads observed')
    result = {
        'schemaVersion': 1,
        'scope': ('Linux host built Web profile process tree with test observer; not an Android dependency graph' if isolated else
                  'Linux host test process tree including Vitest and its actual Web profile; not an Android dependency graph'),
        'traceFiles': len(traces),
        'traceDigestSetSha256': hashlib.sha256(''.join(sorted(digests)).encode()).hexdigest(),
        'distinctSuccessfulAbsoluteCheckoutPaths': len(paths),
        'observedNativeAddons': sorted(native),
        'relativePathsAndOtherSyscallsIncluded': False,
        'runnerAndProfileNotSeparated': not isolated,
        'selectedRootPid': args.root_pid,
        'qualificationOverlay': None if overlay is None else {
            'path': overlay.relative_to(ROOT).as_posix(),
            'sha256': hashlib.sha256(overlay.read_bytes()).hexdigest(),
        },
        'allRecognizedChildTracesPresent': isolated,
        'androidExecuted': False,
        'completeAndroidGraph': False,
        'gate4Passed': False,
    }
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
