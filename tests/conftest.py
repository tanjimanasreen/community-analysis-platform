import socket
import pytest

_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex

class BlockedSocketError(Exception):
    pass

def _is_allowed(address):
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, str) and (
        host == "127.0.0.1"
        or host == "localhost"
        or host == "::1"
        or host.startswith("/") # Unix domain socket
    ):
        return True
    return False

def guarded_connect(self, address):
    if _is_allowed(address):
        return _orig_connect(self, address)
    raise BlockedSocketError(f"Network access blocked in tests. Tried to connect to: {address}")

def guarded_connect_ex(self, address):
    if _is_allowed(address):
        return _orig_connect_ex(self, address)
    raise BlockedSocketError(f"Network access blocked in tests. Tried to connect to: {address}")

@pytest.fixture(autouse=True)
def block_network_access(monkeypatch):
    """
    Blocks all outbound network connections during tests to ensure
    no HTTP requests or model downloads occur silently.
    Allows loopback (127.0.0.1, localhost) for local database tests.
    """
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
