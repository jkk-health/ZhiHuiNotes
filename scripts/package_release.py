"""Package current sources, evidence and offline wheels without private data."""
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '.venv', '.venv-original', '__pycache__', '.pytest_cache', 'node_modules', 'test-results', '.tools'}


def package():
    output = ROOT / 'release'
    output.mkdir(exist_ok=True)
    target = output / '智汇笔记-一键启动版.zip'
    manifest = []
    with ZipFile(target, 'w', ZIP_DEFLATED) as archive:
        roots = [ROOT / n for n in ('backend', 'frontend', 'docs', 'deliverables', 'scripts')]
        files = [p for root in roots for p in root.rglob('*') if p.is_file()]
        files += [ROOT / n for n in ('README.md', '.gitignore', '.python-version', 'setup.ps1', 'start-demo.ps1', '一键启动.bat', '停止运行.bat', '一键启动说明.txt')]
        wheel_root = ROOT / 'offline-wheels'
        if not wheel_root.is_dir():
            wheel_root = output / 'offline-wheels'
        if not list(wheel_root.glob('*.whl')):
            raise RuntimeError('缺少离线依赖 offline-wheels')
        files += list(wheel_root.glob('*.whl'))
        default_runtime = ROOT / 'python-runtime'
        if not (default_runtime / 'python.exe').is_file():
            default_runtime = Path('D:/CodexDependencies/python/cpython-3.11.16-windows-x86_64-none')
        runtime = Path(os.getenv('ZH_PYTHON_RUNTIME', str(default_runtime)))
        if not (runtime / 'python.exe').is_file():
            raise RuntimeError('缺少便携 Python 3.11；请设置 ZH_PYTHON_RUNTIME')
        runtime_files = [p for p in runtime.rglob('*') if p.is_file()]
        for file in runtime_files:
            relative = file.relative_to(runtime)
            if '__pycache__' in relative.parts or file.suffix == '.pyc':
                continue
            name = 'python-runtime/' + relative.as_posix()
            data = file.read_bytes()
            archive.writestr('智汇笔记/' + name, data)
            manifest.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        for file in sorted(files):
            relative = file.relative_to(ROOT)
            if any(part in EXCLUDED or part.startswith('.venv-') for part in relative.parts):
                continue
            if file.name == '.env' or file.suffix in {'.db', '.pyc', '.log'} or any(file.name.endswith(suffix) for suffix in ('.db-journal', '.db-wal', '.db-shm')):
                continue
            name = str(relative).replace('\\', '/')
            if name.startswith('release/offline-wheels/'):
                name = name.removeprefix('release/')
            data = file.read_bytes()
            archive.writestr('智汇笔记/' + name, data)
            manifest.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        archive.writestr('智汇笔记/MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{target}: {len(manifest)} files, {target.stat().st_size} bytes')


if __name__ == '__main__':
    package()
