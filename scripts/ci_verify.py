"""Run the real suite from a temporary source-only copy, never personal data."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="trustshield-ci-") as folder:
        target = Path(folder)
        for name in ("src", "tests", "config", "docs", ".streamlit"):
            shutil.copytree(root / name, target / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copyfile(root / "dashboard.py", target / "dashboard.py")
        for command in (["src/split_v02_synthetic.py"], ["src/build_v02_hard_examples.py"],
                        ["-W", "error::ResourceWarning", "-m", "unittest", "discover", "-s", "tests", "-v"],
                        ["-m", "src.demo"]):
            subprocess.run([sys.executable, *command], cwd=target, check=True)


if __name__ == "__main__":
    main()
