from typing import Dict, List
from .client import MCPClient


class MCPManager:
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}

    def add_server(self, name: str, host: str, port: int):
        self.clients[name] = MCPClient(host, port)

    def list_methods(self) -> Dict[str, dict]:
        all_methods = {}
        for name, client in self.clients.items():
            try:
                methods = client.describe()
                if "result" in methods:
                    all_methods[name] = methods["result"]
            except Exception:
                all_methods[name] = {"error": "Server not available"}
        return all_methods

    def call(self, server_name: str, method: str, **params) -> Dict[str, any]:
        if server_name not in self.clients:
            return {"error": f"Server {server_name} not found"}
        return self.clients[server_name].call(method, **params)