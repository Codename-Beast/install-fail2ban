#!/usr/bin/env python3
"""Check install-fail2ban defaults for operationally unused variables.

Usage:
  python3 tests/scripts/check_fail2ban_unused_defaults.py

The script compares fail2ban_* keys from roles/install-fail2ban/defaults/main.yml
against role templates, tasks and handlers. It ignores known metadata-only keys
and avoids treating variable-looking substrings inside default values as real
variables.
"""
from __future__ import annotations

from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
ROLE = ROOT / "roles" / "install-fail2ban"
DEFAULTS = ROLE / "defaults" / "main.yml"
SEARCH_DIRS = [ROLE / "templates", ROLE / "tasks", ROLE / "handlers"]
ALLOW_UNUSED = {"fail2ban_role_version"}


def main() -> int:
    defaults = yaml.safe_load(DEFAULTS.read_text()) or {}
    default_vars = {key for key in defaults if key.startswith("fail2ban_")}

    used: set[str] = set()
    for directory in SEARCH_DIRS:
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(errors="ignore")
            for variable in default_vars:
                if variable in text:
                    used.add(variable)

    unused = sorted(default_vars - used - ALLOW_UNUSED)
    if unused:
        for variable in unused:
            print(f"UNGENUTZT: {variable}")
        return 1

    print("KEINE OPERATIV UNGENUTZTEN DEFAULT-VARIABLEN GEFUNDEN")
    if ALLOW_UNUSED & default_vars:
        print("AUSGENOMMEN_METADATA: " + ", ".join(sorted(ALLOW_UNUSED & default_vars)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
