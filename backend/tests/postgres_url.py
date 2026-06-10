"""Resolver TEST_DATABASE_URL alcanzable desde el host (WSL + Docker Desktop)."""

from __future__ import annotations

import os
import socket
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.exc import OperationalError


def _wsl_windows_host_candidates() -> list[str]:
    """IPs extra típicas cuando 127.0.0.1 no enruta al puerto publicado por Docker Desktop."""
    hosts: list[str] = []
    resolv = Path("/etc/resolv.conf")
    if resolv.is_file():
        for line in resolv.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "nameserver":
                ip = parts[1].strip()
                if ip and ip not in hosts:
                    hosts.append(ip)
    return hosts


def postgres_host_candidates(preferred: str | None = None) -> list[str]:
    ordered: list[str] = []
    for h in (preferred, "127.0.0.1", "localhost"):
        if h and h not in ordered:
            ordered.append(h)
    for h in _wsl_windows_host_candidates():
        if h not in ordered:
            ordered.append(h)
    return ordered


def _tcp_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _sqlalchemy_ping(url: URL) -> bool:
    # Usar la misma base del DSN de tests (p. ej. rag_test); evita depender solo de "postgres".
    ping_db = url.database or "postgres"
    trial_url = url.set(database=ping_db)
    engine = create_engine(trial_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False
    finally:
        engine.dispose()


def resolve_postgres_url(url: str) -> str | None:
    """Devuelve un DSN equivalente con un host que responda, o None si ninguno conecta."""
    base = make_url(url)
    port = base.port or 5432
    hosts = postgres_host_candidates(base.host)
    for host in hosts:
        if not _tcp_open(host, port):
            continue
        trial = base.set(host=host)
        if _sqlalchemy_ping(trial):
            return str(trial)
    return None


def ensure_test_database_url_env() -> str | None:
    """Normaliza os.environ['TEST_DATABASE_URL'] al primer host alcanzable."""
    raw = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not raw:
        return None
    resolved = resolve_postgres_url(raw)
    if resolved is None:
        return None
    os.environ["TEST_DATABASE_URL"] = resolved
    return resolved
