"""Summarize host Web test syscall traces; this does not define an Android runtime image."""
import argparse
import ast
import glob
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
TIMESTAMP = r'(?:\d+(?:\.\d+)?|(?:\d{2}:){2}\d{2}(?:\.\d+)?)'
RECORD = re.compile(r'^(?:\[pid\s+(\d+)\]\s+)?(?:(%s)\s+)?([A-Za-z_][A-Za-z0-9_]*)\((.*)\)\s+=\s+(.+?)\s*$' % TIMESTAMP)
UNFINISHED = re.compile(r'^(?:\[pid\s+(\d+)\]\s+)?(?:(%s)\s+)?([A-Za-z_][A-Za-z0-9_]*)\((.*)<unfinished \.\.\.>\s*$' % TIMESTAMP)
RESUMED = re.compile(r'^(?:\[pid\s+(\d+)\]\s+)?(?:(%s)\s+)?<\.\.\.\s+([A-Za-z_][A-Za-z0-9_]*) resumed>(.*)$' % TIMESTAMP)
FD_RESULT = re.compile(r'^\s*(\d+)(?:<([^>]*)>)?')
ERROR_RESULT = re.compile(r'^\s*-1\s+([A-Z][A-Z0-9_]*)\b')
USER_FUNCTION = re.compile(r'\b(dlopen|dlmopen|realpath)\s*\(')
OPEN_PATHS = {'open': (0, None), 'openat': (1, 0), 'openat2': (1, 0)}
METADATA_PATHS = {
    'stat': (0, None), 'lstat': (0, None), 'stat64': (0, None), 'lstat64': (0, None),
    'statx': (1, 0), 'statfs': (0, None), 'statvfs': (0, None), 'access': (0, None),
    'faccessat': (1, 0), 'faccessat2': (1, 0), 'newfstatat': (1, 0), 'fstatat64': (1, 0),
}
READLINK_PATHS = {'readlink': (0, None), 'readlinkat': (1, 0)}
EXEC_PATHS = {'execve': (0, None), 'execveat': (1, 0)}
METADATA_SYSCALLS = set(METADATA_PATHS) | {'fstat', 'fstat64', 'fstatat64', 'fstatfs', 'statvfs', 'fstatvfs'}
ACCESS_SYSCALLS = {'access', 'faccessat', 'faccessat2'}
DIR_SYSCALLS = {'getdents', 'getdents64'}
PROCESS_SYSCALLS = {'clone', 'clone3', 'fork', 'vfork'}
MODULE_KINDS = {'resolve', 'resolve-failed', 'dlopen', 'realpath'}
MODULE_OPTIONAL_FIELDS = {'specifier', 'parentURL', 'resolvedURL', 'format', 'errorCode', 'filename', 'path', 'resolvedPath'}


def split_arguments(text):
    """Split syscall arguments without splitting quoted or nested commas."""
    values, start, quote, escaped, stack = [], 0, False, False, []
    pairs = {')': '(', ']': '[', '}': '{', '>': '<'}
    for index, char in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quote = False
            continue
        if char == '"':
            quote = True
        elif char in '([{<':
            stack.append(char)
        elif char in ')]}>':
            if stack and stack[-1] == pairs[char]:
                stack.pop()
        elif char == ',' and not stack:
            values.append(text[start:index].strip())
            start = index + 1
    tail = text[start:].strip()
    if tail or text.strip():
        values.append(tail)
    return values


def decode_string(argument):
    try:
        value = ast.literal_eval(argument.strip())
    except (SyntaxError, ValueError):
        return None
    return value if isinstance(value, str) else None


def descriptor_reference(argument):
    match = re.match(r'^\s*(AT_FDCWD|-?\d+)(?:<([^>]*)>)?', argument)
    return (match.group(1), match.group(2)) if match else (None, None)


def result_status(result):
    error = ERROR_RESULT.match(result)
    if error:
        return 'error', error.group(1)
    if result.strip().startswith('?'):
        return 'unknown', None
    return 'success', None


def category_for(syscall):
    if syscall in OPEN_PATHS:
        return 'open'
    if syscall in METADATA_SYSCALLS:
        return 'access' if syscall in ACCESS_SYSCALLS else 'metadata'
    if syscall in DIR_SYSCALLS:
        return 'directory_read'
    if syscall in READLINK_PATHS:
        return 'readlink'
    if syscall in EXEC_PATHS:
        return 'exec'
    if syscall in PROCESS_SYSCALLS:
        return 'process'
    if syscall in {'chdir', 'fchdir', 'close', 'dup', 'dup2', 'dup3', 'fcntl', 'close_range'}:
        return 'descriptor_state'
    return 'other_syscall'


def _state(cwd=None, fds=None, uncertainties=None):
    reasons = list(uncertainties or ['initial descriptor state was not observed'])
    if cwd is None and 'initial cwd was not observed' not in reasons:
        reasons.append('initial cwd was not observed')
    return {'cwd': cwd, 'fds': dict(fds or {}), 'uncertainties': reasons}


def _mark_uncertain(state, reason):
    if reason not in state.setdefault('uncertainties', []):
        state['uncertainties'].append(reason)


def _has_fd_cloexec(arguments):
    return any('FD_CLOEXEC' in value or value.strip() == '1' for value in arguments)


def _fd_path(state, descriptor, annotation=None):
    if annotation and annotation.startswith('/'):
        return annotation
    entry = state.get('fds', {}).get(descriptor)
    return entry.get('path') if entry else None


def _resolve_path(path, dirfd, state):
    if path.startswith('/'):
        return {'path': path, 'resolution': 'absolute'}
    base = state.get('cwd') if dirfd is None else None
    if dirfd is not None:
        descriptor, annotation = descriptor_reference(dirfd)
        if annotation and annotation.startswith('/'):
            base = annotation
        elif descriptor == 'AT_FDCWD':
            base = state.get('cwd')
        elif descriptor is not None:
            base = _fd_path(state, descriptor)
    if not base or not base.startswith('/'):
        return {'path': None, 'resolution': 'unresolved'}
    return {'path': os.path.normpath(os.path.join(base, path)), 'resolution': 'resolved'}


def _event_for(line, pid, trace_name, line_number, state):
    match = RECORD.match(line)
    if not match:
        return None
    line_pid, _timestamp, syscall, raw_arguments, result = match.groups()
    if syscall in {'dlopen', 'dlmopen', 'realpath'}:
        return None
    args = split_arguments(raw_arguments)
    outcome, error = result_status(result)
    event = {'pid': int(line_pid) if line_pid else pid, 'traceFile': Path(trace_name).name,
             'line': line_number, 'syscall': syscall, 'category': category_for(syscall),
             'outcome': outcome, 'result': result.strip(), 'arguments': args, 'paths': [], 'descriptors': []}
    if error:
        event['errno'] = error
    for index, argument in enumerate(args):
        descriptor, annotation = descriptor_reference(argument)
        if descriptor is not None:
            item = {'argument': index, 'descriptor': descriptor}
            if annotation:
                item['annotation'] = annotation
            elif descriptor != 'AT_FDCWD':
                tracked = _fd_path(state, descriptor)
                if tracked:
                    item['trackedPath'] = tracked
            event['descriptors'].append(item)
    spec = OPEN_PATHS.get(syscall) or METADATA_PATHS.get(syscall) or READLINK_PATHS.get(syscall) or EXEC_PATHS.get(syscall)
    if spec:
        index, dirfd_index = spec
        if index < len(args):
            raw = args[index]
            decoded = decode_string(raw)
            item = {'argument': index, 'raw': raw}
            if decoded is None:
                item['resolution'] = 'unknown'
            else:
                item['decodedPath'] = decoded
                base_arg = args[dirfd_index] if dirfd_index is not None and dirfd_index < len(args) else None
                item.update(_resolve_path(decoded, base_arg, state))
                if syscall in OPEN_PATHS and outcome == 'success':
                    returned_fd = FD_RESULT.match(result)
                    returned_path = returned_fd.group(2) if returned_fd else None
                    if returned_path and returned_path.startswith('/'):
                        item['path'] = returned_path
                        if not decoded.startswith('/') and item.get('resolution') == 'unresolved':
                            item['resolution'] = 'descriptor_annotation'
            event['paths'].append(item)
    if syscall in READLINK_PATHS and outcome == 'success':
        target_index = 2 if syscall == 'readlinkat' else 1
        if target_index < len(args):
            target = decode_string(args[target_index])
            if target is not None:
                event['linkTarget'] = target
                first = result.strip().split()[0]
                event['linkTargetLength'] = int(first) if first.isdigit() else None
    if syscall in DIR_SYSCALLS and args:
        descriptor, annotation = descriptor_reference(args[0])
        if descriptor is not None:
            path = _fd_path(state, descriptor, annotation)
            if path:
                event['paths'].append({'argument': 0, 'decodedPath': path, 'path': path,
                    'resolution': 'descriptor_annotation' if annotation else 'tracked_descriptor'})
            else:
                event['paths'].append({'argument': 0, 'raw': args[0], 'path': None, 'resolution': 'unresolved'})
    return event


def _update_process_state(event, state, states):
    syscall, args = event['syscall'], event['arguments']
    if syscall == 'chdir' and event['outcome'] == 'success' and args:
        path = decode_string(args[0])
        resolved = _resolve_path(path, None, state) if path is not None else {'path': None}
        if resolved['path']:
            state['cwd'] = resolved['path']
        else:
            _mark_uncertain(state, 'successful chdir target could not be safely resolved')
    elif syscall == 'fchdir' and event['outcome'] == 'success' and args:
        fd, annotation = descriptor_reference(args[0])
        path = _fd_path(state, fd, annotation)
        if path:
            state['cwd'] = path
        else:
            _mark_uncertain(state, 'successful fchdir used an unobserved directory descriptor')
    elif syscall in OPEN_PATHS and event['outcome'] == 'success':
        result = FD_RESULT.match(event['result'])
        if result:
            fd, annotation = result.groups()
            path_record = event['paths'][0] if event['paths'] else {}
            path = annotation if annotation and annotation.startswith('/') else path_record.get('path')
            state['fds'][fd] = {'path': path if path and path.startswith('/') else None,
                                'closeOnExec': 'O_CLOEXEC' in ','.join(args)}
            if not path:
                _mark_uncertain(state, f'{syscall} returned fd {fd} without a resolved path')
    elif syscall == 'close' and event['outcome'] == 'success' and args:
        fd, _ = descriptor_reference(args[0])
        if fd is not None:
            if fd not in state['fds']:
                _mark_uncertain(state, f'close of fd {fd} whose prior state was unobserved')
            state['fds'].pop(fd, None)
    elif syscall in {'dup', 'dup2', 'dup3'} and event['outcome'] == 'success' and args:
        source, annotation = descriptor_reference(args[0])
        result = FD_RESULT.match(event['result'])
        if result:
            dest = result.group(1)
            if syscall == 'dup2' and source == dest:
                return
            path = result.group(2) or _fd_path(state, source, annotation)
            cloexec = syscall == 'dup3' and len(args) > 2 and 'O_CLOEXEC' in args[2]
            state['fds'][dest] = {'path': path if path and path.startswith('/') else None, 'closeOnExec': cloexec}
            if path is None:
                _mark_uncertain(state, f'{syscall} duplicated an fd with unknown state')
    elif syscall == 'fcntl' and event['outcome'] == 'success' and len(args) >= 2:
        source, annotation = descriptor_reference(args[0])
        command = args[1].split()[0]
        entry = state['fds'].get(source)
        if command == 'F_SETFD':
            if entry is None:
                _mark_uncertain(state, f'fcntl F_SETFD on unobserved fd {source}')
            else:
                entry['closeOnExec'] = _has_fd_cloexec(args[2:])
        elif command in {'F_DUPFD', 'F_DUPFD_CLOEXEC'}:
            result = FD_RESULT.match(event['result'])
            if result:
                dest = result.group(1)
                path = result.group(2) or _fd_path(state, source, annotation)
                state['fds'][dest] = {'path': path, 'closeOnExec': command == 'F_DUPFD_CLOEXEC'}
                if path is None:
                    _mark_uncertain(state, f'fcntl {command} duplicated an fd with unknown state')
    elif syscall == 'close_range' and event['outcome'] == 'success' and len(args) >= 2:
        try:
            low, high = int(args[0], 0), int(args[1], 0)
        except ValueError:
            low = high = None
        if low is None:
            _mark_uncertain(state, 'close_range bounds could not be interpreted')
        else:
            set_cloexec = len(args) > 2 and 'CLOSE_RANGE_CLOEXEC' in args[2]
            if len(args) > 2 and 'CLOSE_RANGE_UNSHARE' in args[2]:
                _mark_uncertain(state, 'close_range requested FD-table unsharing')
            for fd in list(state['fds']):
                if low <= int(fd) <= high:
                    if set_cloexec:
                        state['fds'][fd]['closeOnExec'] = True
                    else:
                        del state['fds'][fd]
    if syscall in EXEC_PATHS and event['outcome'] == 'success':
        closed = [fd for fd, value in state['fds'].items() if value.get('closeOnExec')]
        for fd in closed:
            del state['fds'][fd]
        if closed:
            event['closedOnExecDescriptors'] = sorted(closed, key=int)
    if syscall in PROCESS_SYSCALLS and event['outcome'] == 'success':
        result = FD_RESULT.match(event['result'])
        if result:
            child = int(result.group(1))
            event['childPid'] = child
            event['inheritedFds'] = [{'fd': fd, 'path': value.get('path'), 'closeOnExec': value.get('closeOnExec', False)}
                                     for fd, value in sorted(state['fds'].items(), key=lambda pair: int(pair[0]))]
            event['fdGraphUncertain'] = True
            reasons = list(state.get('uncertainties', []))
            if syscall in {'clone', 'clone3'}:
                reasons.append('clone FD-table sharing/inheritance semantics cannot be fully inferred from this record')
                _mark_uncertain(state, reasons[-1])
            states.setdefault(child, _state(state.get('cwd'), state['fds'], reasons))


def _normalized_lines(lines, trace_name, pid):
    """Pair unfinished and resumed calls by PID/syscall; preserve unmatched records as incomplete."""
    pending, output, incomplete = {}, [], []
    for number, line in enumerate(lines, 1):
        resumed = RESUMED.match(line)
        if resumed:
            pid_text, _timestamp, syscall, tail = resumed.groups()
            actual_pid = int(pid_text) if pid_text else pid
            key = (actual_pid, syscall)
            previous = pending.pop(key, None)
            if previous is None:
                incomplete.append({'pid': actual_pid, 'traceFile': Path(trace_name).name, 'line': number,
                    'recordType': 'unmatched_resumed_syscall', 'outcome': 'unknown', 'syscall': syscall, 'raw': line})
            else:
                prefix, start = previous
                output.append((prefix + tail, start, actual_pid))
            continue
        unfinished = UNFINISHED.match(line)
        if unfinished:
            pid_text, _timestamp, syscall, partial = unfinished.groups()
            actual_pid = int(pid_text) if pid_text else pid
            key = (actual_pid, syscall)
            if key in pending:
                old_prefix, old_start = pending.pop(key)
                incomplete.append({'pid': actual_pid, 'traceFile': Path(trace_name).name, 'line': old_start,
                    'recordType': 'unmatched_unfinished_syscall', 'outcome': 'unknown', 'syscall': syscall,
                    'raw': old_prefix + '<unfinished ...>'})
            prefix = line[:line.index(syscall)] + syscall + '(' + partial
            pending[key] = (prefix, number)
            continue
        output.append((line, number, pid))
    for (_actual_pid, syscall), (prefix, number) in pending.items():
        pid_match = re.search(r'\[pid\s+(\d+)\]', prefix)
        actual_pid = int(pid_match.group(1)) if pid_match else pid
        incomplete.append({'pid': actual_pid, 'traceFile': Path(trace_name).name, 'line': number,
            'recordType': 'unmatched_unfinished_syscall', 'outcome': 'unknown', 'syscall': syscall,
            'raw': prefix + '<unfinished ...>'})
    return output, incomplete


def parse_trace(name, pid, states):
    key = pid if pid is not None else ('trace', Path(name).name)
    state = states.setdefault(key, _state())
    events, incomplete, loaders = [], [], []
    lines = Path(name).read_text(errors='replace').splitlines()
    normalized, pair_errors = _normalized_lines(lines, name, pid)
    incomplete.extend(pair_errors)
    for number, line in enumerate(lines, 1):
        loader = USER_FUNCTION.search(line)
        if loader and not RECORD.match(line):
            fn = loader.group(1)
            loaders.append({'pid': pid, 'traceFile': Path(name).name, 'line': number,
                'recordType': 'user_space_path_resolution' if fn == 'realpath' else 'user_space_loader',
                'function': fn, 'observation': line.strip()})
    for text, number, _line_pid in normalized:
        if text.strip() and (event := _event_for(text, pid, name, number, state)) is not None:
            _update_process_state(event, state, states)
            events.append(event)
        elif text.strip() and not any(item['line'] == number for item in loaders):
            incomplete.append({'pid': pid, 'traceFile': Path(name).name, 'line': number,
                'recordType': 'unrecognized_record', 'outcome': 'unknown', 'raw': text})
    return events, incomplete, loaders


def _child_pids(trace_name):
    lines = Path(trace_name).read_text(errors='replace').splitlines()
    normalized, _ = _normalized_lines(lines, trace_name, None)
    children = []
    for line, _number, _pid in normalized:
        match = re.search(r'\b(?:clone3?|vfork|fork)\(.*\)\s+=\s+(\d+)\s*$', line)
        if match:
            children.append(int(match.group(1)))
    return children


def _execve_argv_records(trace_name, pid):
    normalized, _ = _normalized_lines(Path(trace_name).read_text(errors='replace').splitlines(), trace_name, pid)
    result = []
    for line, number, _ in normalized:
        match = RECORD.match(line)
        if not match or match.group(3) != 'execve' or result_status(match.group(5))[0] != 'success':
            continue
        args = split_arguments(match.group(4))
        if len(args) < 2:
            continue
        try:
            argv = ast.literal_eval(args[1].strip())
        except (SyntaxError, ValueError):
            continue
        if isinstance(argv, (list, tuple)) and all(isinstance(value, str) for value in argv):
            result.append((number, list(argv)))
    return result


def _is_web_root_argv(argv):
    script = str(ROOT / 'apps/cli/lib/bin.js')
    return script in argv and any(argv[index:index + 2] == ['--profile', 'web'] for index in range(len(argv) - 1))


def _safe_checkout_path(path):
    if not path or not path.startswith('/'):
        return None
    try:
        return Path(os.path.realpath(path)).relative_to(ROOT).as_posix()
    except ValueError:
        return None


def _load_module_records(path):
    valid, malformed = [], []
    if path is None:
        return valid, malformed
    for number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            malformed.append({'recordType': 'malformed_module_trace_json', 'line': number,
                              'outcome': 'unknown', 'reason': str(exc), 'raw': line})
            continue
        if not isinstance(item, dict):
            malformed.append({'recordType': 'malformed_module_trace_record', 'line': number,
                              'outcome': 'unknown', 'reason': 'record must be a JSON object'})
            continue
        pid, kind = item.get('pid'), item.get('kind')
        version = item.get('schemaVersion')
        valid_item = isinstance(version, int) and not isinstance(version, bool) and version == 1
        valid_item = valid_item and isinstance(pid, int) and not isinstance(pid, bool) and isinstance(kind, str) and kind in MODULE_KINDS
        nullable_fields = {'parentURL', 'resolvedURL', 'format'}
        valid_item = valid_item and all(
            key not in item or isinstance(item[key], str) or (key in nullable_fields and item[key] is None)
            for key in MODULE_OPTIONAL_FIELDS
        )
        valid_item = valid_item and ('parentPid' not in item or (isinstance(item['parentPid'], int) and not isinstance(item['parentPid'], bool)))
        if not valid_item:
            malformed.append({'recordType': 'malformed_module_trace_record', 'pid': pid if isinstance(pid, int) and not isinstance(pid, bool) else None,
                              'line': number, 'outcome': 'unknown', 'record': item,
                              'reason': 'invalid schemaVersion, pid, kind, optional-field type, or parentPid'})
            continue
        valid.append({'pid': pid, 'recordType': 'module_trace_' + kind, 'source': 'module_trace_jsonl', 'line': number, **item})
    return valid, malformed


def _module_descendants(records, root_pid):
    known = {record['pid'] for record in records}
    if root_pid not in known:
        raise ValueError(f'Module root PID {root_pid} is missing from module trace')
    selected = {root_pid}
    changed = True
    while changed:
        changed = False
        for record in records:
            parent = record.get('parentPid')
            if parent in selected and record['pid'] not in selected:
                selected.add(record['pid'])
                changed = True
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace-glob', required=True)
    parser.add_argument('--output', type=Path, required=True)
    roots = parser.add_mutually_exclusive_group()
    roots.add_argument('--root-pid', type=int, help='select the built web-profile process and traced descendants')
    roots.add_argument('--discover-root', action='store_true', help='find the unique web-profile launch from per-PID execve argv')
    parser.add_argument('--overlay', type=Path, help='require the named repository overlay in the root launch')
    parser.add_argument('--initial-cwd', type=Path, help='seed the selected root with a cwd known from its launch harness')
    parser.add_argument('--module-trace', type=Path, help='optional observer JSONL records for user-space module resolution/loading')
    parser.add_argument('--module-root-pid', type=int, help='filter separate module-hook records to this PID and parentPid descendants')
    args = parser.parse_args()
    traces = sorted(glob.glob(args.trace_glob))
    if not traces:
        raise ValueError('No traces found')
    if args.overlay is not None and not (args.root_pid is not None or args.discover_root):
        raise ValueError('Overlay verification requires an isolated root process')
    overlay = args.overlay.resolve(strict=True) if args.overlay is not None else None
    if overlay is not None:
        overlay.relative_to(ROOT)
    isolated = args.root_pid is not None or args.discover_root
    by_pid = {}
    if isolated:
        for name in traces:
            suffix = name.rsplit('.', 1)[-1]
            if not suffix.isdecimal():
                raise ValueError('Isolated traces must end in a numeric process identifier')
            trace_pid = int(suffix)
            if trace_pid in by_pid:
                raise ValueError('Duplicate process trace')
            by_pid[trace_pid] = name
    root_pid = args.root_pid
    if args.discover_root:
        candidates = []
        for trace_pid, name in by_pid.items():
            if any(_is_web_root_argv(argv) for _line, argv in _execve_argv_records(name, trace_pid)):
                candidates.append(trace_pid)
        if len(candidates) != 1:
            raise ValueError(f'Expected exactly one successful Web-profile root argv; found {len(candidates)}')
        root_pid = candidates[0]
    selected = None
    if isolated:
        if root_pid not in by_pid:
            raise ValueError('Root process trace missing')
        root_text = Path(by_pid[root_pid]).read_text(errors='replace')
        if not any(_is_web_root_argv(argv) for _line, argv in _execve_argv_records(by_pid[root_pid], root_pid)):
            raise ValueError('Root trace does not identify a successful built web-profile launch')
        if overlay is not None and str(overlay) not in root_text:
            raise ValueError('Root launch does not include the requested overlay')
        pending, selected = [root_pid], set()
        while pending:
            pid = pending.pop()
            if pid in selected:
                continue
            if pid not in by_pid:
                raise ValueError(f'Trace for child {pid} is missing')
            selected.add(pid)
            pending.extend(_child_pids(by_pid[pid]))
        traces = [by_pid[pid] for pid in sorted(selected)]
    initial_cwd = args.initial_cwd.resolve(strict=True) if args.initial_cwd is not None else None
    if initial_cwd is not None and (not isolated or not initial_cwd.is_dir()):
        raise ValueError('--initial-cwd requires an isolated root and an existing directory')
    states, events, incomplete, loaders, digests = {}, [], [], [], []
    if initial_cwd is not None:
        states[root_pid] = _state(str(initial_cwd))
    legacy_paths, legacy_native, native_files = set(), set(), set()
    for name in traces:
        contents = Path(name).read_bytes()
        digests.append(hashlib.sha256(contents).hexdigest())
        suffix = name.rsplit('.', 1)[-1]
        trace_pid = int(suffix) if suffix.isdecimal() else None
        parsed, unknown, user_records = parse_trace(name, trace_pid, states)
        events.extend(parsed)
        incomplete.extend(unknown)
        loaders.extend(user_records)
        for event in parsed:
            # Preserve legacy metrics: successful read-only openat, literal absolute checkout path;
            # .node addon values are canonicalized as before.
            if event['syscall'] == 'openat' and event['outcome'] == 'success' and 'O_RDONLY' in ','.join(event['arguments']):
                path = event['paths'][0] if event['paths'] else {}
                filename = path.get('decodedPath')
                if path.get('resolution') == 'absolute' and filename and filename.startswith(str(ROOT) + '/'):
                    legacy_paths.add(filename)
                    if filename.endswith('.node'):
                        relative = _safe_checkout_path(filename)
                        if relative:
                            legacy_native.add(relative)
            if event['syscall'] in OPEN_PATHS and event['outcome'] == 'success':
                path = event['paths'][0] if event['paths'] else {}
                relative = _safe_checkout_path(path.get('path'))
                if relative and relative.endswith('.node'):
                    native_files.add(relative)
    module_records, module_bad = _load_module_records(args.module_trace)
    if args.module_root_pid is not None:
        if args.module_trace is None:
            raise ValueError('--module-root-pid requires --module-trace')
        module_selected = _module_descendants(module_records, args.module_root_pid)
        module_records = [item for item in module_records if item['pid'] in module_selected]
        module_bad = [item for item in module_bad if item.get('pid') is None or item.get('pid') in module_selected]
    elif isolated:
        module_records = [item for item in module_records if item['pid'] in selected]
        module_bad = [item for item in module_bad if item.get('pid') is None or item.get('pid') in selected]
    loaders.extend(module_records)
    incomplete.extend(module_bad)
    categories, relative_resolved, relative_unresolved = {}, 0, 0
    for event in events:
        categories[event['category']] = categories.get(event['category'], 0) + 1
        for path in event['paths']:
            decoded = path.get('decodedPath')
            if decoded is not None and not decoded.startswith('/'):
                if path.get('resolution') in {'resolved', 'descriptor_annotation', 'tracked_descriptor'}:
                    relative_resolved += 1
                else:
                    relative_unresolved += 1
    unrecognized = sum(item['recordType'] == 'unrecognized_record' for item in incomplete)
    unmatched = sum(item['recordType'] in {'unmatched_unfinished_syscall', 'unmatched_resumed_syscall'} for item in incomplete)
    malformed_module = sum(item['recordType'].startswith('malformed_module') for item in incomplete)
    result = {
        'schemaVersion': 2,
        'scope': ('Linux host built Web profile process tree with test observer; not an Android dependency graph' if isolated else
                  'Linux host test process tree including Vitest and its actual Web profile; not an Android dependency graph'),
        'traceFiles': len(traces),
        'traceDigestSetSha256': hashlib.sha256(''.join(sorted(digests)).encode()).hexdigest(),
        'distinctSuccessfulAbsoluteCheckoutPaths': len(legacy_paths),
        'observedNativeAddons': sorted(legacy_native),
        'observedNativeFiles': sorted(native_files),
        'observedSyscallCategories': dict(sorted(categories.items())),
        'relativePathObservations': {'resolved': relative_resolved, 'unresolved': relative_unresolved},
        'inheritedFdObservations': [event for event in events if event.get('inheritedFds') is not None],
        'fdStateUncertaintyObservations': [
            {'pid': state_pid if isinstance(state_pid, int) else None, 'trace': state_pid[1] if isinstance(state_pid, tuple) else None,
             'reasons': state_value['uncertainties']}
            for state_pid, state_value in states.items() if state_value.get('uncertainties')
        ],
        'recordCounts': {'recognizedSyscalls': len(events), 'unrecognizedTraceRecords': unrecognized,
                         'unmatchedOrMalformedTraceRecords': unmatched, 'recognizedModuleRecords': len(module_records),
                         'malformedModuleRecords': malformed_module},
        'runnerAndProfileNotSeparated': not isolated,
        'selectedRootPid': root_pid,
        'initialWorkingDirectory': None if initial_cwd is None else initial_cwd.as_posix(),
        'moduleRootPid': args.module_root_pid,
        'qualificationOverlay': None if overlay is None else {'path': overlay.relative_to(ROOT).as_posix(),
            'sha256': hashlib.sha256(overlay.read_bytes()).hexdigest()},
        'allRecognizedChildTracesPresent': isolated,
        'androidExecuted': False,
        'completeAndroidGraph': False,
        'gate4Passed': False,
        'events': events,
        'incompleteObservations': incomplete,
        'userSpaceLoaderRecords': loaders,
        'observationCompleteness': {
            'traceRecordStreamParsed': unrecognized == 0 and unmatched == 0,
            'moduleRecordStreamParsed': malformed_module == 0,
            'syscallCoverageClaimed': False,
            'fdGraphComplete': False,
            'scopeNote': 'Completeness applies only to syntactic processing of supplied records; capture coverage and the full FD/module graph are not claimed.',
        },
        'observationsComplete': not incomplete,
    }
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
