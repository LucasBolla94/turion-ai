from __future__ import annotations

from config.settings import Settings
from channels.whatsapp_gateway import WhatsAppConfig, WhatsAppGateway
from channels.base import InboundMessage
from core.brain import Brain


def run_loop(settings: Settings) -> None:
    print("Agent iniciado. Modo:", settings.mode)

    brain = Brain.build(settings)

    def _on_message(msg: InboundMessage) -> None:
        reply = brain.handle(settings.memory_user_id, msg.text)
        wa.send(msg.sender, reply)

    wa = WhatsAppGateway(
        WhatsAppConfig(
            gateway_url=settings.whatsapp_gateway_url or "http://127.0.0.1:3001",
            api_key=settings.whatsapp_api_key,
        ),
        on_message=_on_message,
    )
    wa.start()

    # Mantém o processo vivo
    import time

    while True:
        time.sleep(2)
