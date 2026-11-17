#!/usr/bin/env python3
"""Build and package the existing macOS app with standalone CLT + SwiftPM."""
import argparse
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parent.parent
CLT = Path('/Library/Developer/CommandLineTools')


def run(*args, capture=False):
    result = subprocess.run([str(arg) for arg in args], check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def setting(project, name):
    values = re.findall(r'^\s+' + re.escape(name) + r':\s*"?([^"\n]+)"?\s*$', project, re.M)
    if not values or len(set(values)) != 1:
        raise SystemExit('Missing or ambiguous project setting: ' + name)
    return values[0].strip()


def copy_swift(source, destination):
    if source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    else:
        for path in source.rglob('*.swift'):
            copy_swift(path, destination / path.relative_to(source))


def main():
    project = (ROOT / 'project.yml').read_text()
    app_name = setting(project, 'PRODUCT_NAME')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp') / (app_name + '-build') / 'clt')
    parser.add_argument('--configuration', choices=['debug', 'release'], default='release')
    parser.add_argument('--version', default=setting(project, 'MARKETING_VERSION'))
    parser.add_argument('--build-number', default=setting(project, 'CURRENT_PROJECT_VERSION'))
    parser.add_argument('--sdk', type=Path, help='Optional compatible SDK inside the CLT SDKs directory.')
    args = parser.parse_args()
    if not re.fullmatch(r'\d+(\.\d+){1,2}', args.version) or not args.build_number.isdigit():
        parser.error('Use a numeric version and integer build number.')
    if not (CLT / 'usr/bin/swift').is_file():
        parser.error('Install Command Line Tools with xcode-select --install first.')

    # Do not inherit Xcode SDK/toolchain selections from the invoking shell.
    os.environ['DEVELOPER_DIR'] = str(CLT)
    for key in ('SDKROOT', 'TOOLCHAINS', 'SWIFT_EXEC', 'SWIFT_EXEC_MANIFEST',
                'SWIFT_DRIVER_SWIFT_EXEC', 'SWIFTPM_CUSTOM_LIBS_DIR', 'CC', 'CXX'):
        os.environ.pop(key, None)
    os.environ['PATH'] = str(CLT / 'usr/bin') + ':/usr/bin:/bin:/usr/sbin:/sbin'
    run('/usr/bin/xcrun', '--find', 'swift')
    run('/usr/bin/xcrun', 'swift', '--version')
    run('/usr/bin/xcrun', '--sdk', 'macosx', '--show-sdk-path')

    output = args.output.expanduser().resolve()
    if output == ROOT or ROOT in output.parents or output in ROOT.parents:
        parser.error('--output must be outside the source repository.')
    marker = output / '.kq-dir-clt-build'
    if output.exists() and any(output.iterdir()) and not marker.is_file():
        parser.error('--output is not an empty directory or a previous CLT build directory.')
    output.mkdir(parents=True, exist_ok=True)
    marker.touch()
    os.environ['SWIFTPM_MODULECACHE_OVERRIDE'] = str(output / 'module-cache')
    probe = output / 'SwiftUIProbe.swift'
    probe.write_text('import SwiftUI\nstruct CLTProbe: View {\n'
                     ' @State private var count = 0\n'
                     ' var body: some View { Button("Test") { count += 1 } }\n}\n')
    sdk_root = (CLT / 'SDKs').resolve()
    if args.sdk:
        candidates = [args.sdk.expanduser().resolve()]
        if sdk_root not in candidates[0].parents:
            parser.error('--sdk must be an SDK supplied by standalone Command Line Tools.')
    else:
        candidates = []
        for path in sdk_root.glob('MacOSX*.sdk'):
            match = re.fullmatch(r'MacOSX(\d+(?:\.\d+)*)\.sdk', path.resolve().name)
            if match and int(match[1].split('.')[0]) >= 14:
                candidates.append(path.resolve())
        candidates = sorted(set(candidates), key=lambda p: tuple(
            int(n) for n in re.findall(r'\d+', p.name)), reverse=True)
    sdk = None
    for candidate in candidates:
        result = subprocess.run(['/usr/bin/xcrun', 'swiftc', '-typecheck', '-swift-version', '5',
                                 '-target', platform.machine() + '-apple-macos14.0',
                                 '-sdk', str(candidate), str(probe)], capture_output=True, text=True)
        (output / (candidate.name + '-probe.log')).write_text(result.stderr)
        if result.returncode == 0:
            sdk = candidate
            break
        print('SwiftUI probe failed with ' + str(candidate) + '; see its probe log.', flush=True)
    if sdk is None:
        raise SystemExit('No compatible CLT macOS SDK could compile SwiftUI @State. '
                         'Install a compatible CLT release; see the SDK probe logs in ' + str(output))
    print('Selected standalone CLT SDK: ' + str(sdk), flush=True)
    # Some upgraded CLT installs retain Swift 5.x private interfaces next to
    # newer public interfaces/libraries. Use a temporary copy in that case;
    # never edit the system CLT installation or borrow anything from Xcode.
    runtime = CLT / 'usr/lib/swift/pm'
    stale = []
    for interface in runtime.glob('*API/*.swiftmodule/*.private.swiftinterface'):
        public = interface.with_name(interface.name.replace('.private.swiftinterface', '.swiftinterface'))
        if public.is_file():
            private_version = re.search(r'swiftlang-[^ )]+', interface.read_text())
            public_version = re.search(r'swiftlang-[^ )]+', public.read_text())
            if private_version and public_version and private_version[0] != public_version[0]:
                stale.append(interface.relative_to(runtime))
    if stale:
        runtime_copy = output / 'swiftpm-libs'
        if runtime_copy.exists():
            shutil.rmtree(runtime_copy)
        for directory in ('ManifestAPI', 'PluginAPI'):
            shutil.copytree(runtime / directory, runtime_copy / directory)
        for relative in stale:
            (runtime_copy / relative).unlink()
        os.environ['SWIFTPM_CUSTOM_LIBS_DIR'] = str(runtime_copy)
        print('Using a temporary SwiftPM library copy without stale CLT private interfaces.', flush=True)
    package = output / 'package'
    package.mkdir(exist_ok=True)
    for directory in ('Sources', 'Tests'):
        path = package / directory
        if path.exists():
            shutil.rmtree(path)
    copy_swift(ROOT / 'Sources/mq-dir', package / 'Sources/App')
    copy_swift(ROOT / 'Sources/mqdirCore', package / 'Sources/App/Core')

    resolution = json.loads((ROOT / 'Config/Package.resolved').read_text())
    pins = resolution['pins']
    dependencies = ',\n'.join(
        '        .package(url: ' + json.dumps(pin['location']) + ', exact: ' +
        json.dumps(pin['state']['version']) + ')' for pin in pins
    )
    manifest = '''// swift-tools-version:5.10
import PackageDescription
let package = Package(
    name: "KqDirCLT",
    platforms: [.macOS(.v14)],
    products: [.executable(name: APP_NAME, targets: ["KqDirApp"])],
    dependencies: [
DEPENDENCIES
    ],
    targets: [
        .executableTarget(name: "KqDirApp", dependencies: [
            .product(name: "MarkdownUI", package: "swift-markdown-ui")
        ], path: "Sources/App", swiftSettings: [.unsafeFlags(["-strict-concurrency=complete"])])
    ]
)
'''.replace('APP_NAME', json.dumps(app_name)).replace('DEPENDENCIES', dependencies)
    (package / 'Package.swift').write_text(manifest)
    # SwiftPM supports this lockfile format on the project's Swift 5.10 minimum.
    (package / 'Package.resolved').write_text(json.dumps({'pins': pins, 'version': 2}, indent=2) + '\n')
    swift = ['/usr/bin/xcrun', 'swift']
    common = ['--package-path', package, '--sdk', sdk]
    run(*swift, 'package', *common, 'resolve')
    resolved = json.loads((package / 'Package.resolved').read_text())
    actual = {pin['identity']: pin['state']['revision'] for pin in resolved['pins']}
    expected = {pin['identity']: pin['state']['revision'] for pin in pins}
    if actual != expected:
        raise SystemExit('Resolved dependencies differ from Config/Package.resolved; stopping.')
    # Keep each dependency's declared language mode with SwiftPM's native backend.
    build_options = ['--build-system', 'native']
    run(*swift, 'build', *common, *build_options, '--force-resolved-versions', '-c', args.configuration,
        '--product', app_name)
    binary_dir = Path(run(*swift, 'build', *common, *build_options, '-c', args.configuration,
                          '--show-bin-path', capture=True))

    app = output / (app_name + '.app')
    if app.exists():
        shutil.rmtree(app)
    contents = app / 'Contents'
    resources = contents / 'Resources'
    (contents / 'MacOS').mkdir(parents=True)
    resources.mkdir()
    shutil.copy2(binary_dir / app_name, contents / 'MacOS' / app_name)
    for localized in (ROOT / 'Resources').glob('*.lproj'):
        shutil.copytree(localized, resources / localized.name)
    iconset = output / 'AppIcon.iconset'
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir()
    for png in (ROOT / 'Resources/Assets.xcassets/AppIcon.appiconset').glob('*.png'):
        shutil.copy2(png, iconset / png.name)
    run('/usr/bin/iconutil', '-c', 'icns', iconset, '-o', resources / 'AppIcon.icns')
    with (ROOT / 'Sources/mq-dir/Info.plist').open('rb') as file:
        info = plistlib.load(file)
    info.update(CFBundleExecutable=app_name, CFBundleName=app_name,
                CFBundleDisplayName=app_name, CFBundleDevelopmentRegion='en',
                CFBundleIdentifier=setting(project, 'PRODUCT_BUNDLE_IDENTIFIER'),
                CFBundleShortVersionString=args.version, CFBundleVersion=args.build_number,
                CFBundleIconFile='AppIcon.icns')
    if '$(' in str(info):
        raise SystemExit('Unresolved build settings in Info.plist; stopping.')
    with (contents / 'Info.plist').open('wb') as file:
        plistlib.dump(info, file)
    (contents / 'PkgInfo').write_bytes(b'APPL????')
    licenses = resources / 'Licenses'
    licenses.mkdir()
    shutil.copy2(ROOT / 'LICENSE', licenses / 'kq-dir-MIT.txt')
    for name, filename in [('swift-markdown-ui', 'LICENSE'), ('NetworkImage', 'LICENSE'),
                           ('swift-cmark', 'COPYING')]:
        shutil.copy2(package / '.build/checkouts' / name / filename, licenses / (name + '.txt'))
    run('/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime',
        '--timestamp=none', app)
    run('/usr/bin/codesign', '--verify', '--deep', '--strict', '--verbose=2', app)
    run('/usr/bin/lipo', '-info', contents / 'MacOS' / app_name)
    print('\nBuilt with Command Line Tools: ' + str(app))
    print('Ad-hoc signed; not notarized. Company execution policies still apply.')


if __name__ == '__main__':
    main()
