import json
import socket
from typing import Callable, Dict, Any
from dataclasses import dataclass


@dataclass
class Method:
    name: str
    description: str
    parameters: Dict[str, str]
    handler: Callable


class MCPServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self.methods: Dict[str, Method] = {}
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = False

    def register(self, name: str, description: str, parameters: Dict[str, str]):
        def decorator(func: Callable):
            self.methods[name] = Method(name, description, parameters, func)
            return func
        return decorator

    def get_methods(self) -> Dict[str, dict]:
        result = {}
        for name, method in self.methods.items():
            result[name] = {
                "description": method.description,
                "parameters": method.parameters
            }
        return result

    def handle_request(self, request: dict) -> dict:
        method_name = request.get("method")

        if method_name == "__describe__":
            return {"result": self.get_methods()}

        if method_name not in self.methods:
            return {"error": f"Method {method_name} not found"}

        method = self.methods[method_name]
        params = request.get("params", {})

        try:
            result = method.handler(**params)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    def run(self):
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        self.running = True
        print(f"MCP Server running on {self.host}:{self.port}")

        while self.running:
            try:
                self.socket.settimeout(1.0)
                conn, addr = self.socket.accept()
                try:
                    data = conn.recv(4096).decode()
                    if not data:
                        continue
                    request = json.loads(data)
                    response = self.handle_request(request)
                    conn.sendall(json.dumps(response).encode())
                except Exception as e:
                    print(f"Error: {e}")
                finally:
                    conn.close()
            except socket.timeout:
                continue

    def stop(self):
        self.running = False
        self.socket.close()