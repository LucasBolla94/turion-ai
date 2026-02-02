from __future__ import annotations

import asyncio
import json
import os
import sys
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


async def _listen_events(gateway_url: str, api_key: str | None) -> None:
    ws_url = gateway_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}/events"
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key

    async with websockets.connect(ws_url, extra_headers=headers) as ws:
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
                return


def _wait_gateway_ready(gateway_url: str, api_key: str | None, timeout_sec: int = 30) -> bool:
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    start = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else None
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


def _run_qr_flow(settings: Settings) -> None:
    print("Conecte o WhatsApp escaneando o QR abaixo.\n")

    gateway_url = settings.whatsapp_gateway_url or ""
    if not _wait_gateway_ready(gateway_url, settings.whatsapp_api_key):
        print("Gateway não respondeu no /health. Verifique o serviço:")
        print("  sudo systemctl status bot-ai-gateway.service")
        print("  sudo journalctl -u bot-ai-gateway.service -f")

    # Tenta obter QR via HTTP, com retry simples
    for _ in range(5):
        qr_text = _fetch_qr(gateway_url, settings.whatsapp_api_key)
        if qr_text:
            _render_qr(qr_text)
            break
        time.sleep(2)

    try:
        asyncio.run(_listen_events(gateway_url, settings.whatsapp_api_key))
    except Exception:
        print("Não foi possível escutar eventos do gateway. Verifique o serviço.")


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

    _run_qr_flow(settings)

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
