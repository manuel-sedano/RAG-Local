"""Tests de filtros Fail2ban (regex sobre líneas de log de ejemplo)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FILTERS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "docker" / "fail2ban" / "data" / "filter.d"
)


def _load_failregex(name: str) -> list[re.Pattern[str]]:
    text = (FILTERS_DIR / name).read_text(encoding="utf-8")
    lines: list[str] = []
    in_failregex = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("failregex"):
            in_failregex = True
            rest = line.split("=", 1)[-1].strip()
            if rest:
                lines.append(rest)
            continue
        if in_failregex:
            if not line or line.startswith("[") or line.startswith("ignoreregex"):
                break
            if line.startswith("^"):
                lines.append(line)
    if not lines:
        msg = f"No failregex en {name}"
        raise ValueError(msg)
    return [re.compile(ln.replace("<HOST>", r"(?P<host>\S+)")) for ln in lines]


@pytest.mark.parametrize(
    ("filter_file", "line", "should_match"),
    [
        (
            "traefik-auth.conf",
            '203.0.113.50 - - [20/May/2026:10:00:01 +0000] "POST /api/auth/login HTTP/1.1" 401 42 "-" "-" 0 "-" "-" 0ms',
            True,
        ),
        (
            "traefik-auth.conf",
            '203.0.113.50 - - [20/May/2026:10:00:02 +0000] "POST /api/auth/login HTTP/1.1" 429 12 "-" "-" 0 "-" "-" 0ms',
            True,
        ),
        (
            "traefik-auth.conf",
            '203.0.113.50 - - [20/May/2026:10:00:03 +0000] "GET /api/health HTTP/1.1" 200 19 "-" "-" 0 "-" "-" 0ms',
            False,
        ),
        (
            "traefik-forbidden.conf",
            '198.51.100.9 - - [20/May/2026:10:01:00 +0000] "GET /api/kbs HTTP/1.1" 403 0 "-" "-" 0 "-" "-" 0ms',
            True,
        ),
        (
            "rag-backend-security.conf",
            "SECURITY_ACCESS client_ip=10.0.0.5 method=POST path=/api/auth/login status=401",
            True,
        ),
    ],
)
def test_fail2ban_filter_lines(filter_file: str, line: str, should_match: bool) -> None:
    patterns = _load_failregex(filter_file)
    matched = any(p.search(line) for p in patterns)
    assert matched is should_match
