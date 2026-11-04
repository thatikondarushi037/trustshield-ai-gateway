"""Inspect actual image layers, including files hidden by a later deletion."""
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile


def main():
    with tempfile.TemporaryDirectory(prefix='trustshield-image-') as folder:
        archive = Path(folder) / 'image.tar'
        subprocess.run(['docker', 'image', 'save', '-o', str(archive), 'trustshield:1.0.0-rc1'], check=True)
        checked, problems = 0, []
        with tarfile.open(archive) as outer:
            manifest = json.load(outer.extractfile('manifest.json'))
            for layer in manifest[0]['Layers']:
                checked += 1
                with tarfile.open(fileobj=outer.extractfile(layer)) as inner:
                    for member in inner:
                        name = member.name.lstrip('./')
                        if not member.isfile() or not name.startswith('app/'):
                            continue
                        path = Path(name)
                        if (path.suffix in {'.csv', '.db', '.sqlite', '.sqlite3', '.pem', '.key', '.log'}
                                or path.name.startswith('.env') or set(path.parts) & {'.secrets', 'holdout', 'models', '.git'}):
                            problems.append(name)
        assert not problems, problems
        print(json.dumps({'image': 'trustshield:1.0.0-rc1', 'layers_checked': checked,
                          'forbidden_application_files': problems, 'status': 'PASS'}))


if __name__ == '__main__':
    main()
