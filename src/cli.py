from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable

import psycopg2
import requests

from config.settings import Settings


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True)


def _which(name: str) -> bool:
    return shutil.which(name) is not None


def _systemctl_is_active(service: str) -> tuple[bool, str]:
    if not _which("systemctl"):
        return False, "systemctl não encontrado"
    result = _run(["systemctl", "is-active", service])
    ok = result.returncode == 0
    return ok, result.stdout.strip() or result.stderr.strip()


def _check_gateway(url: str) -> tuple[bool, str]:
    try:
        resp = requests.get(f"{url}/health", timeout=5)
        if resp.ok:
            return True, "/health ok"
        return False, f"/health status {resp.status_code}"
    except Exception as exc:  # pragma: no cover - best effort
        return False, str(exc)


def _check_db(settings: Settings) -> tuple[bool, str]:
    if not settings.db_password:
        return False, "DB_PASSWORD vazio"
    try:
        conn = psycopg2.connect(
            host=settings.db_host,
            port=settings.db_port,
            dbname=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            connect_timeout=5,
        )
        with conn.cursor() as cur:
            cur.execute("select to_regclass('public.memory_items')")
            has_memory = cur.fetchone()[0] is not None
            cur.execute("select to_regclass('public.user_profiles')")
            has_profile = cur.fetchone()[0] is not None
        conn.close()
        if not has_memory or not has_profile:
            return False, "schema incompleto"
        return True, "conexão ok e schema ok"
    except Exception as exc:
        return False, str(exc)


def doctor() -> int:
    settings = Settings.load()
    results: list[CheckResult] = []

    py_ok = sys.version_info >= (3, 10)
    results.append(CheckResult("python >= 3.10", py_ok, sys.version.split()[0]))

    if _which("node"):
        node_v = _run(["node", "-v"]).stdout.strip()
        results.append(CheckResult("node", True, node_v))
    else:
        results.append(CheckResult("node", False, "não encontrado"))

    if _which("npm"):
        npm_v = _run(["npm", "-v"]).stdout.strip()
        results.append(CheckResult("npm", True, npm_v))
    else:
        results.append(CheckResult("npm", False, "não encontrado"))

    if _which("psql"):
        psql_v = _run(["psql", "-V"]).stdout.strip()
        results.append(CheckResult("psql", True, psql_v))
    else:
        results.append(CheckResult("psql", False, "não encontrado"))

    venv_ok = os.path.exists("/opt/bot-ai/.venv/bin/python")
    results.append(CheckResult("venv", venv_ok, "/opt/bot-ai/.venv/bin/python"))

    daemon_ok, daemon_detail = _systemctl_is_active("bot-ai.service")
    results.append(CheckResult("bot-ai.service", daemon_ok, daemon_detail))

    gw_ok, gw_detail = _systemctl_is_active("bot-ai-gateway.service")
    results.append(CheckResult("bot-ai-gateway.service", gw_ok, gw_detail))

    if settings.whatsapp_gateway_url:
        health_ok, health_detail = _check_gateway(settings.whatsapp_gateway_url)
        results.append(CheckResult("gateway health", health_ok, health_detail))

    db_ok, db_detail = _check_db(settings)
    results.append(CheckResult("db", db_ok, db_detail))

    ok_all = True
    for r in results:
        status = "OK" if r.ok else "FAIL"
        print(f"[{status}] {r.name}: {r.detail}")
        if not r.ok:
            ok_all = False

    return 0 if ok_all else 1


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="turion")
    sub = parser.add_subparsers(dest="cmd")
    sub.required = True

    sub.add_parser("doctor", help="verifica dependências e serviços")

    args = parser.parse_args(argv)
    if args.cmd == "doctor":
        return doctor()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
