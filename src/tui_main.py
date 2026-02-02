from __future__ import annotations

import socket

SOCKET_PATH = "/var/run/bot-ai.sock"


def main() -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(SOCKET_PATH)
        s.sendall(b"ping\n")
        print(s.recv(4096).decode("utf-8", errors="ignore"))


if __name__ == "__main__":
    main()
