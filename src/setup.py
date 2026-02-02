from __future__ import annotations

import asyncio
import json
import os
import sys
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

import requests
import segno
import websockets

from config.settings import Settings
from memory.store import MemoryConfig, MemoryService
from memory.types import UserProfile


@dataclass
class SetupAnswers:
    user_id: str
    assistant_name: str
    user_name: str
    style: str
    preferences: str
    language: str
    llm_api_key: str


def _print_banner() -> None:
    print("\n=== Turion Setup ===\n")


def _ask(prompt: str, default: str | None = None) -> str:
    if default:
        raw = input(f"{prompt} [{default}]: ").strip()
        return raw or default
    return input(f"{prompt}: ").strip()


def _render_qr(qr_text: str) -> None:
    qr = segno.make(qr_text)
    print(qr.terminal(compact=True))


def _fetch_qr(gateway_url: str, api_key: str | None) -> Optional[str]:
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    try:
        resp = requests.get(f"{gateway_url}/qr", headers=headers, timeout=5)
        if resp.ok:
            return resp.json().get("qr")
    except Exception:
        return None
    return None


def _wait_for_connected() -> None:
    print("Aguardando conexão do WhatsApp...")


async def _listen_events(gateway_url: str, api_key: str | None) -> bool:
    ws_url = gateway_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}/events"
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key

    # websockets API differs across versions (additional_headers vs extra_headers)
    try:
        ws_cm = websockets.connect(ws_url, additional_headers=headers)
    except TypeError:
        ws_cm = websockets.connect(ws_url, extra_headers=headers)

    async with ws_cm as ws:
        async for message in ws:
            try:
                payload = json.loads(message)
            except Exception:
                continue

            if payload.get("type") == "qr":
                qr_text = payload.get("data")
                if qr_text:
                    _render_qr(qr_text)
                    print("Leia o QR no WhatsApp para conectar.")
            if payload.get("type") == "status" and payload.get("data") == "connected":
                print("WhatsApp conectado.\n")
                return True
    return False


def _wait_gateway_ready(gateway_url: str, api_key: str | None, timeout_sec: int = 30) -> bool:
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    elapsed = 0.0
    while elapsed <= timeout_sec:
        try:
            resp = requests.get(f"{gateway_url}/health", headers=headers, timeout=5)
            if resp.ok:
                return True
        except Exception:
            pass
        time.sleep(2)
        elapsed += 2
    return False


def _fetch_status(gateway_url: str, api_key: str | None) -> Optional[str]:
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    try:
        resp = requests.get(f"{gateway_url}/status", headers=headers, timeout=5)
        if resp.ok:
            return resp.json().get("status")
    except Exception:
        return None
    return None


def _post_reset(gateway_url: str, api_key: str | None) -> bool:
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    try:
        resp = requests.post(f"{gateway_url}/reset", headers=headers, timeout=5)
        return resp.ok
    except Exception:
        return False


def _service_active(name: str) -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", name],
            check=False,
            text=True,
            capture_output=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def _service_start(name: str) -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "start", name],
            check=False,
            text=True,
            capture_output=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def _service_logs(name: str, lines: int = 120) -> str:
    try:
        result = subprocess.run(
            ["journalctl", "-u", name, "-n", str(lines), "--no-pager"],
            check=False,
            text=True,
            capture_output=True,
        )
        return result.stdout.strip() or result.stderr.strip()
    except Exception:
        return ""


def _preflight_services() -> bool:
    ok = True
    for svc in ["bot-ai.service", "bot-ai-gateway.service"]:
        if not _service_active(svc):
            ok = False
    return ok


def _run_qr_flow(settings: Settings) -> bool:
    if not _preflight_services():
        print("Serviços não estão ativos. Tentando iniciar...")
        _service_start("bot-ai.service")
        _service_start("bot-ai-gateway.service")
        time.sleep(2)
        if not _preflight_services():
            print("Serviços ainda não ativos. Rode: turion doctor")
            return False

    print("Conecte o WhatsApp escaneando o QR abaixo.\n")

    gateway_url = settings.whatsapp_gateway_url or ""
    if not _wait_gateway_ready(gateway_url, settings.whatsapp_api_key):
        print("Gateway não respondeu no /health. Verifique o serviço:")
        print("  sudo systemctl status bot-ai-gateway.service")
        print("  sudo journalctl -u bot-ai-gateway.service -f")
        return False

    # simple and reliable: HTTP polling only
    last_qr = None
    no_qr_cycles = 0
    while True:
        status = _fetch_status(gateway_url, settings.whatsapp_api_key)
        if status == "connected":
            print("WhatsApp conectado.\n")
            return True
        qr_text = _fetch_qr(gateway_url, settings.whatsapp_api_key)
        if qr_text and qr_text != last_qr:
            last_qr = qr_text
            _render_qr(qr_text)
            print("Leia o QR no WhatsApp para conectar.")
            no_qr_cycles = 0
        if not qr_text:
            no_qr_cycles += 1
            print("QR ainda não gerado. Últimos logs do gateway:")
            logs = _service_logs("bot-ai-gateway.service", 40)
            if logs:
                print(logs)
            if no_qr_cycles >= 5 and sys.stdin.isatty():
                ans = _ask("Nenhum QR detectado. Resetar sessão do WhatsApp? (isso apaga login)", "N")
                if ans.lower() in {"y", "yes", "s", "sim"}:
                    if _post_reset(gateway_url, settings.whatsapp_api_key):
                        print("Sessão resetada. Aguardando novo QR...")
                        no_qr_cycles = 0
                        time.sleep(3)
        time.sleep(3)


def _save_profile(settings: Settings, answers: SetupAnswers) -> None:
    memory = MemoryService(
        MemoryConfig(
            host=settings.db_host,
            port=settings.db_port,
            dbname=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            cache_ttl_sec=settings.memory_cache_ttl_sec,
        )
    )

    persona = (
        f"Você é {answers.assistant_name}, um assistente útil e humano. "
        f"Chame o usuário de {answers.user_name}."
    )
    profile = UserProfile(
        user_id=answers.user_id,
        persona=persona,
        style=answers.style,
        preferences=answers.preferences,
        language=answers.language,
    )
    memory.upsert_profile(profile)

    memory.add_message(answers.user_id, "system", f"Nome do assistente: {answers.assistant_name}")
    memory.add_message(answers.user_id, "system", f"Nome do usuário: {answers.user_name}")
    memory.add_message(answers.user_id, "system", f"Preferências: {answers.preferences}")
    memory.add_message(answers.user_id, "system", f"Idioma: {answers.language}")


def _update_env_api_key(settings: Settings, api_key: str) -> None:
    if not api_key:
        return
    env_path = os.path.join("/opt/bot-ai", ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    updated = False
    out = []
    for line in lines:
        if line.startswith("LLM_API_KEY="):
            out.append(f"LLM_API_KEY={api_key}")
            updated = True
        else:
            out.append(line)
    if not updated:
        out.append(f"LLM_API_KEY={api_key}")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def run_setup() -> int:
    if not sys.stdin.isatty():
        print("Setup requer terminal interativo.")
        return 1

    settings = Settings.load()
    _print_banner()

    if not settings.whatsapp_gateway_url:
        print("WHATSAPP_GATEWAY_URL não configurado no .env")
        return 1

    try:
        if not _run_qr_flow(settings):
            return 1
    except KeyboardInterrupt:
        print("\nSetup cancelado pelo usuário.")
        return 1

    answers = SetupAnswers(
        user_id=_ask("User ID", settings.memory_user_id),
        assistant_name=_ask("Assistant name", "Turion"),
        user_name=_ask("Your name", "Friend"),
        style=_ask("Reply style", "Clear and friendly"),
        preferences=_ask("Preferences or goals", ""),
        language=_ask("Preferred language", "English"),
        llm_api_key=_ask("Your Grok API key", ""),
    )

    if answers.llm_api_key:
        _update_env_api_key(settings, answers.llm_api_key)

    _save_profile(settings, answers)
    print("Configuração salva. Você pode começar a conversar.\n")
    return 0
