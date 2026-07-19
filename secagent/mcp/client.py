import json
import socket
from typing import Dict, Any


class MCPClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port

    def call(self, method: str, **params) -> Dict[str, Any]:
        request = {
            "method": method,
            "params": params
        }

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.host, self.port))
            sock.sendall(json.dumps(request).encode())
            data = sock.recv(4096).decode()
            return json.loads(data)

    def describe(self) -> Dict[str, Any]:
        return self.call("__describe__")