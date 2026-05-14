"""Comprobaciones de dependencias para /api/health."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
import psycopg
import redis.asyncio as aioredis

from app.core.config import Settings


@dataclass(frozen=True)
class DependencyResult:
    name: str
    ok: bool
    detail: str | None = None
    latency_ms: float | None = None


def _to_psycopg_conninfo(database_url: str) -> str:
    return (
        database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        .replace("postgresql+asyncpg://", "postgresql://", 1)
    )


async def check_postgres(settings: Settings) -> DependencyResult:
    started = time.perf_counter()
    conninfo = _to_psycopg_conninfo(settings.database_url)
    try:
        async with await psycopg.AsyncConnection.connect(
            conninfo,
            connect_timeout=int(settings.health_http_timeout_seconds),
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()
        latency_ms = (time.perf_counter() - started) * 1000
        return DependencyResult(name="postgres", ok=True, latency_ms=round(latency_ms, 2))
    except Exception as exc:  # noqa: BLE001 — health: cualquier fallo cuenta
        latency_ms = (time.perf_counter() - started) * 1000
        return DependencyResult(
            name="postgres",
            ok=False,
            detail=str(exc),
            latency_ms=round(latency_ms, 2),
        )


async def check_redis(settings: Settings) -> DependencyResult:
    started = time.perf_counter()
    client = aioredis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.health_http_timeout_seconds,
    )
    try:
        await client.ping()
        latency_ms = (time.perf_counter() - started) * 1000
        return DependencyResult(name="redis", ok=True, latency_ms=round(latency_ms, 2))
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.perf_counter() - started) * 1000
        return DependencyResult(
            name="redis",
            ok=False,
            detail=str(exc),
            latency_ms=round(latency_ms, 2),
        )
    finally:
        try:
            await client.aclose()
        except Exception:
            pass


async def check_qdrant(settings: Settings) -> DependencyResult:
    started = time.perf_counter()
    url = f"{settings.qdrant_http_url.rstrip('/')}/healthz"
    timeout = httpx.Timeout(settings.health_http_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
        latency_ms = (time.perf_counter() - started) * 1000
        return DependencyResult(name="qdrant", ok=True, latency_ms=round(latency_ms, 2))
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.perf_counter() - started) * 1000
        return DependencyResult(
            name="qdrant",
            ok=False,
            detail=str(exc),
            latency_ms=round(latency_ms, 2),
        )


async def check_ollama(settings: Settings) -> DependencyResult:
    started = time.perf_counter()
    url = f"{settings.ollama_http_url.rstrip('/')}/api/version"
    timeout = httpx.Timeout(settings.health_http_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
        latency_ms = (time.perf_counter() - started) * 1000
        return DependencyResult(name="ollama", ok=True, latency_ms=round(latency_ms, 2))
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.perf_counter() - started) * 1000
        return DependencyResult(
            name="ollama",
            ok=False,
            detail=str(exc),
            latency_ms=round(latency_ms, 2),
        )


async def run_dependency_checks(settings: Settings) -> list[DependencyResult]:
    results = [
        await check_postgres(settings),
        await check_redis(settings),
        await check_qdrant(settings),
        await check_ollama(settings),
    ]
    return results


def results_to_payload(results: list[DependencyResult]) -> dict[str, Any]:
    return {
        r.name: {
            "ok": r.ok,
            "latency_ms": r.latency_ms,
            "detail": r.detail,
        }
        for r in results
    }
