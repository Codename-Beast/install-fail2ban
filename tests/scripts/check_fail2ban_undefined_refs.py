#!/usr/bin/env python3
"""Check install-fail2ban Jinja references for missing defaults.

Usage:
  python3 tests/scripts/check_fail2ban_undefined_refs.py

The script scans {{ ... }} expressions in role templates, tasks and handlers for
fail2ban_* references. A reference is accepted when it is defined in defaults,
created locally by register/set_fact/vars/loop_var, or guarded in the expression
with a Jinja default(...) fallback.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
ROLE = ROOT / "roles" / "install-fail2ban"
DEFAULTS = ROLE / "defaults" / "main.yml"
SCAN_DIRS = [ROLE / "templates", ROLE / "tasks", ROLE / "handlers"]
TASK_DIR = ROLE / "tasks"


def collect_runtime_vars() -> set[str]:
    runtime: set[str] = set()
    for path in TASK_DIR.glob("*.yml"):
        text = path.read_text(errors="ignore")
        runtime.update(re.findall(r"register:\s*(fail2ban_[A-Za-z0-9_]+)", text))
        runtime.update(re.findall(r"loop_var:\s*(fail2ban_[A-Za-z0-9_]+)", text))
        # set_fact and vars keys commonly appear at two or four spaces in role tasks.
        runtime.update(re.findall(r"(?m)^\s{2}(fail2ban_[A-Za-z0-9_]+):\s*", text))
        runtime.update(re.findall(r"(?m)^\s{4}(fail2ban_[A-Za-z0-9_]+):\s*", text))
    return runtime


def expression_has_default(expr: str, variable: str) -> bool:
    suffix = expr[expr.find(variable):]
    return "| default(" in suffix or "|default(" in suffix


def main() -> int:
    defaults = yaml.safe_load(DEFAULTS.read_text()) or {}
    default_vars = {key for key in defaults if key.startswith("fail2ban_")}
    runtime_vars = collect_runtime_vars()

    findings: list[str] = []
    for directory in SCAN_DIRS:
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
                for expr in re.findall(r"{{(.*?)}}", line):
                    for variable in sorted(set(re.findall(r"\bfail2ban_[A-Za-z0-9_]+\b", expr))):
                        if variable in default_vars or variable in runtime_vars:
                            continue
                        if not expression_has_default(expr, variable):
                            rel = path.relative_to(ROOT)
                            findings.append(f"UNDEFINED_OHNE_DEFAULT: {rel}:{lineno}: {variable}")

    if findings:
        print("\n".join(findings))
        return 1

    print("KEINE UNGESICHERTEN JINJA-REFERENZEN GEFUNDEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
