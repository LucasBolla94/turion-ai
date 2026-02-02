from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Callable

import requests
import websockets

from channels.base import Channel, InboundMessage


@dataclass
class WhatsAppConfig:
    gateway_url: str
    api_key: str | None = None


class WhatsAppGateway(Channel):
    def __init__(self, config: WhatsAppConfig, on_message: Callable[[InboundMessage], None] | None = None) -> None:
        self.config = config
        self.on_message = on_message
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def send(self, recipient: str, text: str) -> None:
        headers = {}
        if self.config.api_key:
            headers["x-api-key"] = self.config.api_key
        requests.post(
            f"{self.config.gateway_url}/send",
            json={"to": recipient, "text": text},
            headers=headers,
            timeout=10,
        )

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._listen()
            except Exception:
                time.sleep(2)

    def _listen(self) -> None:
        ws_url = self.config.gateway_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/events"
        headers = {}
        if self.config.api_key:
            headers["x-api-key"] = self.config.api_key

        async def _inner() -> None:
            # websockets API differs across versions (additional_headers vs extra_headers)
            try:
                ws_cm = websockets.connect(ws_url, additional_headers=headers)
            except TypeError:
                ws_cm = websockets.connect(ws_url, extra_headers=headers)
            async with ws_cm as ws:
                async for message in ws:
                    payload = json.loads(message)
                    if payload.get("type") == "qr":
                        print("[whatsapp] QR recebido")
                        print(payload.get("data", ""))
                    if payload.get("type") == "message":
                        if not self.on_message:
                            continue
                        incoming = InboundMessage(
                            channel="whatsapp",
                            sender=payload.get("from", ""),
                            text=payload.get("text", ""),
                        )
                        self.on_message(incoming)

        import asyncio

        asyncio.run(_inner())
