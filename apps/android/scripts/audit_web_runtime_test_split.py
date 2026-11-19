#!/usr/bin/env python3
"""Partition Web Profile production package inputs from host test/build inputs.

This emits a manifest-backed package-role report plus an observation partition.
It is not an Android image builder or proof that every observed file is needed.
"""
from collections import Counter
import gzip
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'apps/android/evidence'
# The preserved P3A-002 host captures record absolute paths from this checkout.
CAPTURED_REPOSITORY_ROOTS = (Path('/tmp/deepseek-harness-feature'),)
MANIFESTS = {
    'cli': 'apps/cli/package.json',
    'webProfileBundle': 'packages/bundle/web-app/package.json',
    'webFrontend': 'apps/web/package.json',
}
CAPTURES = {
    'bootstrap': {
        'summary': 'apps/android/evidence/original-web-profile-p3a001-host-observations.json',
        'inventory': 'apps/android/evidence/original-web-profile-p3a002-path-inventory.json.gz',
    },
    'bounded': {
        'summary': 'apps/android/evidence/original-web-bounded-p3a001-host-observations.json',
        'inventory': 'apps/android/evidence/original-web-bounded-p3a002-path-inventory.json.gz',
    },
}
INSTRUMENTATION_PATHS = {
    'apps/android/scripts/capture_web_host_trace.py',
    'apps/android/scripts/audit_web_host_trace.py',
    'apps/android/scripts/web_profile_module_observer.mjs',
    'apps/android/tests/web-bootstrap.host.spec.mjs',
    'apps/android/tests/web-bounded-profile.host.spec.mjs',
    'apps/android/tests/vitest.web-host.config.mjs',
    'apps/android/tests/fixtures/web-host-bounded.patch.yml',
    'apps/cli/tests/profiles/web/tests/default-web-process.ts',
    'apps/cli/tests/profiles/web/tests/runtime-roster.ts',
    'apps/cli/tests/profiles/web/tests/fixtures/runtime-roster-observer.ts',
}
TEST_PACKAGE_NAMES = {
    'vitest', '@vitest/coverage-v8', '@vitest/expect', '@vitest/mocker',
    '@vitest/pretty-format', '@vitest/runner', '@vitest/snapshot',
    '@vitest/spy', '@vitest/utils', 'playwright', 'jsdom',
}
BUILD_OR_TEST_TOOL_NAMES = TEST_PACKAGE_NAMES | {
    'tsx', 'typescript', 'vite', '@vitejs/plugin-react', 'http-server',
    '@testing-library/dom', '@testing-library/react',
    '@deepseek-ai/dsh-agent-loop-testkit', '@deepseek-ai/dsh-tool-testkit',
    '@deepseek-ai/dsh-client-test-runtime', '@deepseek-ai/dsh-llm-mock-server',
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(path.read_bytes())


def load_json(path):
    return json.loads(path.read_text())


def dependency_names(manifest, section):
    value = manifest.get(section, {})
    if not isinstance(value, dict):
        raise ValueError(f'Manifest section {section!r} is not an object')
    return set(value)


def resolve_dependency_manifest(owner_dir, name, root=ROOT):
    parts = name.split('/')
    if not parts or any(part in {'', '.', '..'} for part in parts):
        return None
    root = root.resolve()
    cursor = owner_dir.resolve()
    while cursor == root or root in cursor.parents:
        candidate = cursor / 'node_modules' / Path(*parts) / 'package.json'
        if candidate.is_file():
            return candidate.resolve()
        if cursor == root:
            break
        cursor = cursor.parent
    return None


def production_tree(role, manifest_path, root=ROOT):
    """Walk only dependencies/optional/peers; never traverse devDependencies."""
    root_manifest = load_json(manifest_path)
    queue = []
    for section in ('dependencies', 'optionalDependencies', 'peerDependencies'):
        for name in dependency_names(root_manifest, section):
            queue.append((manifest_path.parent, name, section, root_manifest))
    seen_paths = set()
    packages = {}
    unresolved = Counter()
    unresolved_examples = set()
    while queue:
        owner_dir, name, section, parent_manifest = queue.pop()
        package_json = resolve_dependency_manifest(owner_dir, name, root)
        if package_json is None:
            optional_peer = section == 'peerDependencies' and parent_manifest.get(
                'peerDependenciesMeta', {}).get(name, {}).get('optional') is True
            kind = 'missingOptionalPeer' if optional_peer else ('missingOptionalDependency' if section == 'optionalDependencies' else 'missingRequiredDependency')
            unresolved[kind] += 1
            unresolved_examples.add(f'{name} ({kind})')
            continue
        key = package_json.as_posix()
        if key in seen_paths:
            continue
        seen_paths.add(key)
        manifest = load_json(package_json)
        actual_name = manifest.get('name')
        if actual_name != name:
            unresolved['packageNameMismatch'] += 1
            unresolved_examples.add(f'{name} resolved to {actual_name!r}')
            continue
        version = manifest.get('version', 'unknown')
        packages[key] = {'name': actual_name, 'version': version}
        for child_section in ('dependencies', 'optionalDependencies', 'peerDependencies'):
            for child_name in dependency_names(manifest, child_section):
                queue.append((package_json.parent, child_name, child_section, manifest))

    if unresolved['missingRequiredDependency'] or unresolved['packageNameMismatch']:
        examples = sorted(unresolved_examples)[:20]
        raise ValueError(f'{role} production manifest graph has unresolved required packages: {examples}')
    identities = sorted({f"{item['name']}@{item['version']}" for item in packages.values()})
    package_names = {item['name'] for item in packages.values()}
    return {
        'role': role,
        'rootManifest': manifest_path.relative_to(root).as_posix(),
        'rootPackage': root_manifest.get('name'),
        'directProductionDependencies': sorted(set().union(*(
            dependency_names(root_manifest, section)
            for section in ('dependencies', 'optionalDependencies', 'peerDependencies')
        ))),
        'installedPackageManifestCount': len(packages),
        'uniquePackageIdentityCount': len(identities),
        'packageIdentities': identities,
        'packageIdentitySetSha256': sha256_bytes('\n'.join(identities).encode()),
        'unresolvedOptionalOrPeerDeclarations': sorted(unresolved_examples),
        'unresolvedOptionalOrPeerCounts': dict(sorted(
            (key, value) for key, value in unresolved.items()
            if key not in {'missingRequiredDependency', 'packageNameMismatch'}
        )),
    }, package_names


def manifest_review():
    records = {}
    productions = {}
    development = {}
    for role, relative in MANIFESTS.items():
        path = ROOT / relative
        manifest = load_json(path)
        production = set().union(*(
            dependency_names(manifest, section)
            for section in ('dependencies', 'optionalDependencies', 'peerDependencies')
        ))
        dev = dependency_names(manifest, 'devDependencies')
        productions[role] = production
        development[role] = dev
        records[role] = {
            'path': relative,
            'package': manifest.get('name'),
            'sha256': sha256_file(path),
            'directProductionDependencies': sorted(production),
            'directDevelopmentDependencies': sorted(dev),
            'devOnlyDirectDependencies': sorted(dev - production),
        }
    trees = {}
    runtime_names = {}
    for role in ('cli', 'webProfileBundle'):
        record, names = production_tree(role, ROOT / MANIFESTS[role])
        trees[role] = record
        runtime_names[role] = names
    return records, productions, development, trees, runtime_names


def package_name_from_path(relative_path):
    """Resolve the nearest package manifest, including pnpm symlink paths."""
    candidate = ROOT / relative_path
    try:
        candidate = candidate.resolve(strict=False)
    except OSError:
        pass
    if candidate.is_file():
        candidate = candidate.parent
    while candidate != ROOT and ROOT in candidate.parents:
        package_json = candidate / 'package.json'
        if package_json.is_file():
            try:
                name = json.loads(package_json.read_text()).get('name')
            except (OSError, json.JSONDecodeError):
                name = None
            if isinstance(name, str):
                return name
        candidate = candidate.parent
    return None


def repo_relative(absolute):
    path = Path(absolute)
    for root in (ROOT, *CAPTURED_REPOSITORY_ROOTS):
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            continue
    return None


def path_from_module_url(value):
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    if parsed.scheme == 'file':
        return unquote(parsed.path)
    if not parsed.scheme and value.startswith('/'):
        return value
    return None


def is_test_path(relative_path):
    parts = PurePosixPath(relative_path).parts
    if any(part in {'tests', '__tests__', 'fixtures'} for part in parts):
        return True
    if relative_path.endswith(('.spec.ts', '.spec.js', '.spec.mjs', '.test.ts', '.test.js', '.test.mjs')):
        return True
    return PurePosixPath(relative_path).name.startswith('vitest.')


def classify_package_name(package_name, production_names, development_names):
    if package_name in production_names['webProfileBundle']:
        return 'web_profile_production_package_tree'
    if package_name in production_names['cli']:
        return 'cli_launcher_production_package_tree'
    if package_name in development_names['webFrontend']:
        return 'frontend_build_dependency'
    if package_name in development_names['webProfileBundle'] or package_name in development_names['cli']:
        return 'development_or_test_only_package'
    if package_name in TEST_PACKAGE_NAMES:
        return 'test_runner_or_test_module'
    return 'other_observed_package_or_asset'


def classify_path(relative_path, production_names, development_names):
    if is_test_path(relative_path):
        return 'host_test_or_fixture'
    if relative_path in INSTRUMENTATION_PATHS:
        return 'trace_instrumentation'
    lower = relative_path.lower()
    if lower.endswith('.map') or '/preview/' in lower or lower.endswith('/preview.html'):
        return 'preview_or_source_map_excluded'
    if relative_path.startswith('apps/web/dist/') or relative_path == 'apps/web/dist/index.html':
        return 'production_frontend_asset_candidate'
    if relative_path.startswith('apps/web/src/') or relative_path.startswith('apps/web/scripts/'):
        return 'frontend_build_source'
    if relative_path == 'apps/cli' or relative_path.startswith('apps/cli/lib/') or relative_path == 'apps/cli/package.json':
        return 'cli_launcher_application_code'
    if relative_path == 'packages/bundle/web-app' or relative_path.startswith('packages/bundle/web-app/lib/'):
        return 'web_profile_bundle_application_code'

    package_name = package_name_from_path(relative_path)
    if package_name is None:
        return 'observed_path_unclassified'
    return classify_package_name(package_name, production_names, development_names)


class AssetReferences(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for attribute in ('src', 'href'):
            value = values.get(attribute)
            if isinstance(value, str):
                self.values.append((tag, attribute, value))


def resolve_dist_reference(raw):
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    stack = ['apps', 'web', 'dist']
    for part in PurePosixPath(unquote(parsed.path)).parts:
        if part in {'', '.'}:
            continue
        if part == '..':
            if len(stack) <= 3:
                raise ValueError(f'Frontend asset reference escapes dist: {raw}')
            stack.pop()
        else:
            stack.append(part)
    result = PurePosixPath(*stack).as_posix()
    if not result.startswith('apps/web/dist/'):
        raise ValueError(f'Frontend asset reference escapes dist: {raw}')
    return result


def frontend_asset_review():
    dist = ROOT / 'apps/web/dist'
    index = dist / 'index.html'
    if not index.is_file():
        raise FileNotFoundError('Built frontend index is missing; build @deepseek-ai/dsh-web-frontend first')
    parser = AssetReferences()
    parser.feed(index.read_text())
    references = []
    for tag, attribute, raw in parser.values:
        name = resolve_dist_reference(raw)
        if name is None:
            continue
        target = ROOT / name
        if not target.is_file():
            raise FileNotFoundError(f'Local frontend asset reference is missing: {name}')
        references.append({'tag': tag, 'attribute': attribute, 'reference': raw,
                           'path': name, 'sha256': sha256_file(target)})

    production_assets = []
    excluded_assets = []
    for path in sorted(dist.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if path.suffix == '.map' or relative.startswith('apps/web/dist/preview/') or path.name == 'preview.html':
            excluded_assets.append({'path': relative, 'reason': 'source map or preview asset'})
        else:
            production_assets.append({'path': relative, 'sha256': sha256_file(path)})
    if not production_assets:
        raise ValueError('Frontend build has no production assets')
    if 'apps/web/dist/index.html' not in {item['path'] for item in production_assets}:
        raise ValueError('Built frontend index is not classified as a production asset')
    referenced_paths = {item['path'] for item in references}
    return {
        'scope': 'Built static frontend payload only; not the Node backend runtime image',
        'indexSha256': sha256_file(index),
        'localIndexReferences': references,
        'unreferencedByIndexButIncludedInBuildOutput': sorted(
            item['path'] for item in production_assets
            if item['path'] not in referenced_paths and item['path'] != 'apps/web/dist/index.html'
        ),
        'productionAssetCount': len(production_assets),
        'productionAssets': production_assets,
        'excludedPreviewOrSourceMapCount': len(excluded_assets),
        'excludedPreviewOrSourceMaps': excluded_assets,
        'analysisLimit': 'Index-local HTML references and complete built-output inventory; not a recursive JavaScript module graph or lazy client-plugin closure.',
    }


def inventory_paths(inventory):
    operations = inventory.get('observedPathOperations', {}).get('operations', [])
    paths = set()
    for row in operations:
        for key in ('resolvedPath', 'pathLiteral'):
            value = row.get(key)
            if isinstance(value, str):
                relative = repo_relative(value)
                if relative is not None:
                    paths.add(relative)
    return operations, sorted(paths)


def classify_capture(role, operations, files, production_names, development_names, summary):
    path_roles = Counter(classify_path(path, production_names, development_names) for path in files)
    examples = {}
    for category in sorted(path_roles):
        examples[category] = [
            path for path in files if classify_path(path, production_names, development_names) == category
        ][:8]
    urls = summary.get('userSpaceLoaderSummary', {}).get('uniqueResolvedModuleUrls', [])
    observer_urls = []
    test_urls = []
    runner_urls = []
    for url in urls:
        path = path_from_module_url(url)
        relative = repo_relative(path) if path else None
        package_name = package_name_from_path(relative) if relative else None
        if relative in INSTRUMENTATION_PATHS:
            observer_urls.append(url)
        if (relative and is_test_path(relative)) or (path and (
            'dsh-web-default-isolation-' in path or '/fixtures/runtime-roster-observer.' in path
        )):
            test_urls.append(url)
        if package_name in TEST_PACKAGE_NAMES:
            runner_urls.append(url)
    metadata = summary.get('captureMetadata', {})
    return {
        'profile': 'web',
        'spec': metadata.get('spec'),
        'summarySha256': sha256_file(ROOT / CAPTURES[role]['summary']),
        'inventorySha256': sha256_file(ROOT / CAPTURES[role]['inventory']),
        'observedPathOperationRows': len(operations),
        'uniqueCheckoutPaths': len(files),
        'pathRoleCounts': dict(sorted(path_roles.items())),
        'representativePathsByRole': examples,
        'boundedOverlayFixtureObserved': 'apps/android/tests/fixtures/web-host-bounded.patch.yml' in files,
        'testOnlyRuntimeRosterObserverIncludedByHostHelper': metadata.get('testOnlyRuntimeRosterObserverIncluded'),
        'moduleObserverInjectedByCapture': metadata.get('moduleObserverPath'),
        'moduleObserverResolvedUrlCount': len(observer_urls),
        'testOnlyResolvedModuleUrlCount': len(test_urls),
        'testOnlyResolvedModuleUrlExamples': sorted(set(test_urls))[:8],
        'testRunnerResolvedModuleUrlCount': len(runner_urls),
        'selectedProfileResolvedModuleUrlCount': len(urls),
        'moduleInterpretation': 'Resolution does not prove evaluation or necessity. The test helper injects a temporary runtime-roster observer; the capture metadata names the separate module-observer preload.',
    }


def build_report():
    manifests, direct_production, direct_development, trees, production_names = manifest_review()
    frontend = frontend_asset_review()
    production_tool_conflicts = {
        role: sorted(names & BUILD_OR_TEST_TOOL_NAMES)
        for role, names in production_names.items()
    }
    if any(production_tool_conflicts.values()):
        raise ValueError(f'Test/build tools entered production package tree: {production_tool_conflicts}')
    captures = {}
    for role, paths in CAPTURES.items():
        summary_path = ROOT / paths['summary']
        inventory_path = ROOT / paths['inventory']
        summary = load_json(summary_path)
        inventory = json.loads(gzip.decompress(inventory_path.read_bytes()))
        operations, files = inventory_paths(inventory)
        captures[role] = classify_capture(
            role, operations, files, production_names, direct_development, summary,
        )

    dev_roots = (direct_development['cli'] | direct_development['webProfileBundle']) - (
        production_names['cli'] | production_names['webProfileBundle']
    )
    return {
        'schemaVersion': 1,
        'assessment': {
            'status': 'test-and-build-inputs-separated-from-declared-production-package-trees; file-closure-not-assessed',
            'androidWebRuntimeImageBuilt': False,
            'androidExecuted': False,
            'completeDependencyClosureProven': False,
            'gate4Passed': False,
        },
        'manifestReview': manifests,
        'productionPackageTrees': trees,
        'dependencyRoles': {
            'webProfileRuntimePackageNames': sorted(production_names['webProfileBundle']),
            'cliLauncherRuntimePackageNames': sorted(production_names['cli']),
            'devOnlyDirectDependenciesOutsideBothProductionTrees': sorted(dev_roots),
            'frontendBuildDependencyNames': sorted(direct_development['webFrontend']),
            'frontendBuildDependenciesNotInEitherNodeRuntimeTree': sorted(
                direct_development['webFrontend'] - production_names['cli'] - production_names['webProfileBundle']
            ),
            'testAndBuildToolNamesAbsentFromProductionTrees': sorted(BUILD_OR_TEST_TOOL_NAMES),
            'testAndBuildToolConflictsByProductionTree': production_tool_conflicts,
            'frontendDistIsSeparateStaticAssetPayload': True,
            'interpretation': 'The two package trees follow only dependencies, optionalDependencies and peerDependencies; devDependencies are never traversed. The CLI tree is broader than the Web Profile alone. Package inclusion is not file-level necessity or Android compatibility.',
        },
        'frontendStaticAssetAnalysis': frontend,
        'hostTracePartitions': captures,
        'explicitProductionImageExclusions': {
            'hostTestSpecsAndVitestConfiguration': [
                'apps/android/tests/web-bootstrap.host.spec.mjs',
                'apps/android/tests/web-bounded-profile.host.spec.mjs',
                'apps/android/tests/vitest.web-host.config.mjs',
                'apps/android/tests/fixtures/web-host-bounded.patch.yml',
                'apps/cli/tests/profiles/web/tests/default-web-process.ts',
                'apps/cli/tests/profiles/web/tests/runtime-roster.ts',
                'apps/cli/tests/profiles/web/tests/fixtures/runtime-roster-observer.ts',
            ],
            'traceAndModuleObservationTools': [
                'apps/android/scripts/capture_web_host_trace.py',
                'apps/android/scripts/audit_web_host_trace.py',
                'apps/android/scripts/web_profile_module_observer.mjs',
            ],
            'excludedFrontendOutputClasses': ['apps/web/dist/preview/**', '*.map'],
            'frontendBuildInputs': 'Frontend source, Vite and the apps/web devDependencies build the static dist payload; they are not Node backend runtime package roots.',
        },
        'inputs': {
            relative: sha256_file(ROOT / relative)
            for relative in [
                'package.json', 'pnpm-lock.yaml', *MANIFESTS.values(),
                *[p for pair in CAPTURES.values() for p in pair.values()],
            ]
        },
        'limits': [
            'P3A-002 path rows are observations, not a required-file verdict; successful lookup/open does not prove content read or necessity.',
            'P3A-001 module resolution does not prove evaluation or dependency necessity; capture metadata confirms a test-only runtime-roster observer was injected by the host helper.',
            'The Web Profile bundle production tree follows manifest-declared production edges; the CLI launcher tree includes all CLI production dependencies and is broader than the Web Profile-specific closure.',
            'The report does not infer that every observed path is required, nor does it resolve every dynamic import, client plugin batch, provider or runtime-generated file.',
            'Static frontend analysis inventories built files and index.html references; it does not prove the dynamic browser plugin graph or end-to-end UI behavior.',
            'Linux host evidence does not establish Android ARM64/Bionic compatibility, native dependency closure, Android startup, secure transport or Gate 4 acceptance.',
        ],
    }


def main():
    output = EVIDENCE / 'original-web-p3a003-runtime-test-separation.json'
    check = '--check' in sys.argv[1:]
    if output.exists() and not check:
        raise SystemExit(f'Refusing to overwrite existing evidence: {output}')
    report = build_report()
    rendered = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if check:
        if not output.is_file() or output.read_text() != rendered:
            raise SystemExit('P3A-003 evidence is missing or stale; rerun after preserving the prior report')
        print(f'P3A-003 evidence current: {output.relative_to(ROOT)}')
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered)
        print(f'Wrote {output.relative_to(ROOT)} ({len(rendered.encode())} bytes)')


if __name__ == '__main__':
    main()
