from __future__ import annotations

import os
import socket
import threading
import time

SOCKET_PATH = "/var/run/bot-ai.sock"


def _handle_client(conn: socket.socket) -> None:
    try:
        data = conn.recv(4096).decode("utf-8", errors="ignore").strip()
        if not data:
            return
        if data == "ping":
            conn.sendall(b"pong\n")
        else:
            conn.sendall(b"ok\n")
    finally:
        conn.close()


def run_server() -> None:
    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o666)
    server.listen(5)

    while True:
        conn, _ = server.accept()
        t = threading.Thread(target=_handle_client, args=(conn,), daemon=True)
        t.start()


def main() -> None:
    print("Daemon iniciado")
    run_server()


if __name__ == "__main__":
    main()
