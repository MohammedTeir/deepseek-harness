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
OPEN = re.compile(r'openat\([^,]+, ("(?:[^"\\]|\\.)*"), ([^)]*)\)\s+=\s+(\d+)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace-glob', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    traces = sorted(glob.glob(args.trace_glob))
    if not traces:
        raise ValueError('No traces found')
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
        'scope': 'Linux host test process tree including Vitest and its actual Web profile; not an Android dependency graph',
        'traceFiles': len(traces),
        'traceDigestSetSha256': hashlib.sha256(''.join(sorted(digests)).encode()).hexdigest(),
        'distinctSuccessfulAbsoluteCheckoutPaths': len(paths),
        'observedNativeAddons': sorted(native),
        'relativePathsAndOtherSyscallsIncluded': False,
        'runnerAndProfileNotSeparated': True,
        'androidExecuted': False,
        'completeAndroidGraph': False,
        'gate4Passed': False,
    }
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
