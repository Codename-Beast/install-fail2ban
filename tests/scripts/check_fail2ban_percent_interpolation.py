#!/usr/bin/env python3
"""Check Fail2Ban filter configs for unsafe literal percent signs.

Usage:
  python3 tests/scripts/check_fail2ban_percent_interpolation.py

Fail2Ban reads filter files through ConfigParser interpolation. Literal percent
signs in .conf/.conf.j2 files must be doubled as %% unless they intentionally
start a ConfigParser interpolation token such as %(name)s. The script prints all
percent occurrences and fails on lone unsafe percent signs.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
ROLE = ROOT / "roles" / "install-fail2ban"
FILTERS = sorted((ROLE / "files").glob("*.conf")) + sorted((ROLE / "templates").glob("*.conf.j2"))


def classify(line: str, idx: int) -> str:
    prev_char = line[idx - 1] if idx > 0 else ""
    next_char = line[idx + 1] if idx + 1 < len(line) else ""
    if prev_char == "%":
        return "ESCAPED_SECOND_PERCENT"
    if next_char == "%":
        return "ESCAPED_LITERAL_PERCENT"
    if prev_char == "{" or next_char == "}":
        return "JINJA_CONTROL_DELIMITER"
    if next_char == "(":
        return "CONFIGPARSER_INTERPOLATION"
    return "UNSAFE_SINGLE_PERCENT"


def main() -> int:
    findings: list[str] = []
    unsafe: list[str] = []
    for path in FILTERS:
        for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
            for idx, char in enumerate(line):
                if char != "%":
                    continue
                kind = classify(line, idx)
                if kind in {"ESCAPED_SECOND_PERCENT", "JINJA_CONTROL_DELIMITER"}:
                    continue
                rel = path.relative_to(ROOT)
                entry = f"{rel}:{lineno}: {kind}"
                findings.append(entry)
                if kind == "UNSAFE_SINGLE_PERCENT":
                    unsafe.append(entry)

    if findings:
        print("PROZENT-FUNDSTELLEN:")
        print("\n".join(findings))
    else:
        print("KEINE PROZENTZEICHEN IN FILTERDATEIEN GEFUNDEN")

    if unsafe:
        print("UNSICHERE EINZEL-PROZENTZEICHEN GEFUNDEN")
        return 1

    print("KEINE UNSICHEREN EINZEL-PROZENTZEICHEN GEFUNDEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
