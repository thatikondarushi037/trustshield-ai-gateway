"""Explicit local development utilities; never print secrets."""
import argparse
import json
import os
import secrets
from src.settings import ROOT
from src.report_registry import refresh_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("container-secret", "reports", "protected-check"))
    args = parser.parse_args()
    if args.action == "container-secret":
        path = ROOT / ".secrets/audit_token"
        path.parent.mkdir(exist_ok=True)
        if not path.exists():
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(secrets.token_urlsafe(32))
        print("Local container secret is configured; value withheld. Protect host file permissions.")
    elif args.action == "reports":
        result = refresh_manifest()
        print(json.dumps({"verified_report_files": len(result["reports"])}))
    else:
        from src.report_registry import file_hash
        expected = json.loads((ROOT / ".cache/release-protected.json").read_text())
        assert all(file_hash(ROOT / path) == checksum for path, checksum in expected.items())
        print(json.dumps({"protected_files_unchanged": len(expected)}))


if __name__ == "__main__":
    main()
