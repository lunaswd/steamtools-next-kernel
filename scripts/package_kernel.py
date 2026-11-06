"""Create deterministic binary + complete corresponding-source release assets."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import struct
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP_TIME = (2000, 1, 1, 0, 0, 0)
DLL_NAMES = ('OpenSteamTool.dll', 'dwmapi.dll', 'xinput1_4.dll', 'version.dll.disabled')
LICENSE_FILES = {
    'detours': ('LICENSE', 'LICENSE-Detours.txt'),
    'protobuf': ('LICENSE', 'LICENSE-Protobuf.txt'),
    'spdlog': ('LICENSE', 'LICENSE-spdlog.txt'),
    'tomlplusplus': ('LICENSE', 'LICENSE-tomlplusplus.txt'),
}


def git(*args: str, root: Path = ROOT) -> str:
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def file_record(name: str, data: bytes) -> dict:
    return {'name': name, 'sizeBytes': len(data), 'sha256': digest(data)}


def write_zip(path: Path, entries: dict[str, bytes]) -> None:
    if path.exists():
        raise ValueError(f'Release asset already exists: {path}')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(entries):
            if not name or name.startswith('/') or '\\' in name or '..' in name.split('/'):
                raise ValueError(f'Invalid archive entry: {name}')
            info = zipfile.ZipInfo(name, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, entries[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def require_x64_dll(data: bytes, name: str) -> None:
    if len(data) < 64 or data[:2] != b'MZ':
        raise ValueError(f'Not a PE DLL: {name}')
    offset = struct.unpack_from('<I', data, 0x3c)[0]
    if offset + 24 > len(data) or data[offset:offset + 4] != b'PE\0\0':
        raise ValueError(f'Invalid PE header: {name}')
    machine = struct.unpack_from('<H', data, offset + 4)[0]
    characteristics = struct.unpack_from('<H', data, offset + 22)[0]
    if machine != 0x8664 or not characteristics & 0x2000:
        raise ValueError(f'Expected Windows x64 DLL: {name}')


def dependency_entries(deps: Path) -> tuple[dict[str, bytes], dict[str, bytes]]:
    lock = json.loads((ROOT / 'dependency-lock.json').read_text(encoding='utf-8-sig'))
    notices, sources = {}, {}
    for dep in lock['dependencies']:
        name = dep['name']
        source = deps / f'{name}-src'
        if not source.is_dir():
            raise ValueError(f'Missing complete dependency sources: {name}')
        if 'commit' in dep and git('rev-parse', 'HEAD', root=source) != dep['commit']:
            raise ValueError(f'Dependency revision mismatch: {name}')
        if name in LICENSE_FILES:
            source_name, output_name = LICENSE_FILES[name]
            notices[output_name] = (source / source_name).read_bytes()
        elif name == 'lua':
            html = (source / 'doc/readme.html').read_text(encoding='utf-8')
            start = html.index('Copyright &copy;')
            end = html.index('THE SOFTWARE.', start) + len('THE SOFTWARE.')
            text = html[start:end].replace('&copy;', '(c)').replace('&ndash;', '-')
            text = re.sub(r'<[^>]+>', '', text)
            notices['LICENSE-Lua.txt'] = (text.strip() + '\n').encode('utf-8')
            tarballs = list(deps.glob('lua-subbuild/**/lua-5.5.0.tar.gz'))
            if not tarballs or digest(tarballs[0].read_bytes()) != dep['sha256']:
                raise ValueError('Lua source archive hash mismatch or absent')
        for path in sorted(source.rglob('*')):
            rel = path.relative_to(source)
            if '.git' in rel.parts:
                continue
            if path.is_symlink():
                raise ValueError(f'Dependency source symlink is not allowed: {path}')
            if path.is_file():
                sources[f'vendor/{name}/{rel.as_posix()}'] = path.read_bytes()
    notices['LICENSE-fmt.txt'] = (deps / 'spdlog-src/include/spdlog/fmt/bundled/fmt.license.rst').read_bytes()
    return notices, sources


def package(build: Path, output: Path, deps: Path, release_tag: str) -> dict:
    version = re.search(r'project\(OpenSteamTool VERSION ([0-9]+(?:\.[0-9]+){3})',
                        (ROOT / 'src/CMakeLists.txt').read_text(encoding='utf-8')).group(1)
    if release_tag != f'v{version}':
        raise ValueError(f'Release tag must match source version: v{version}')
    if git('status', '--porcelain', '--untracked-files=normal'):
        raise ValueError('Release packaging requires committed, clean sources')
    commit = git('rev-parse', 'HEAD')
    info = json.loads((build / 'kernel-build.json').read_text(encoding='utf-8-sig'))
    if (info['sourceCommit'], info['version'], info['configuration'], info['platform']) != (
            commit, version, 'Release', 'windows-x64'):
        raise ValueError('Build provenance differs from the checked-out release source')
    expected = {item['name']: item for item in info['files']}
    entries = {}
    for name in DLL_NAMES:
        data = (build / 'Release' / name).read_bytes()
        require_x64_dll(data, name)
        if file_record(name, data) != expected.get(name):
            raise ValueError(f'Build output hash changed since compilation: {name}')
        entries[name] = data
    entries['version.dll'] = entries['version.dll.disabled']
    for name in ('LICENSE', 'opensteamtool.example.toml', 'THIRD-PARTY-NOTICES.md'):
        entries[name] = (ROOT / name).read_bytes()
    notices, dependency_sources = dependency_entries(deps)
    entries.update(notices)
    entries['BUILD_INFO.json'] = encode_json(info)
    sums = [file_record(name, entries[name]) for name in sorted(entries)]
    entries['SHA256SUMS.json'] = encode_json({'schemaVersion': 1, 'algorithm': 'SHA-256',
        'files': [{'path': r['name'], 'sizeBytes': r['sizeBytes'], 'sha256': r['sha256']} for r in sums]})
    entries['SHA256SUMS.txt'] = ''.join(f"{r['sha256']}  {r['name']}\n" for r in sums).encode('utf-8')
    files = [file_record(name, entries[name]) for name in sorted(entries)]
    output.mkdir(parents=True, exist_ok=True)
    binary_name = f'steamtools-next-kernel-{version}-windows-x64.zip'
    binary_path = output / binary_name
    write_zip(binary_path, entries)
    source_entries = {}
    # Tracked kernel files are exactly the current commit. Generated caches,
    # credentials, ignored files and the local .git directory never enter it.
    archived = subprocess.check_output(['git', '-C', str(ROOT), 'archive', '--format=zip', commit])
    with zipfile.ZipFile(io.BytesIO(archived)) as archive:
        for item in archive.infolist():
            if item.is_dir():
                continue
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f'Kernel source symlink is not allowed: {item.filename}')
            source_entries[item.filename] = archive.read(item)
    source_entries.update(dependency_sources)
    source_entries['SOURCE_INFO.json'] = encode_json({'schemaVersion': 1, 'sourceCommit': commit,
        'version': version, 'releaseTag': release_tag, 'dependencies': json.loads((ROOT / 'dependency-lock.json').read_text())})
    source_path = output / f'steamtools-next-kernel-{version}-source.zip'
    write_zip(source_path, source_entries)
    manifest = {'schemaVersion': 1, 'version': version, 'releaseTag': release_tag,
        'sourceCommit': commit, 'platform': 'windows-x64', 'asset': file_record(binary_name, binary_path.read_bytes()),
        'files': files}
    (output / 'kernel-release.json').write_bytes(encode_json(manifest))
    (output / 'release-SHA256SUMS.txt').write_text(
        ''.join(f'{digest(p.read_bytes())}  {p.name}\n' for p in (binary_path, source_path, output / 'kernel-release.json')),
        encoding='utf-8')
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, default=ROOT / 'build-release')
    parser.add_argument('--deps-dir', type=Path, default=ROOT / '.deps')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist')
    parser.add_argument('--release-tag', required=True)
    args = parser.parse_args()
    manifest = package(args.build_dir.resolve(), args.output_dir.resolve(), args.deps_dir.resolve(), args.release_tag)
    print(json.dumps({'version': manifest['version'], 'sourceCommit': manifest['sourceCommit'],
                      'asset': manifest['asset'], 'outputDirectory': str(args.output_dir.resolve())}, indent=2))


if __name__ == '__main__':
    main()

