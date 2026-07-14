import socket
import pytest

_orig_connect = socket.socket.connect

class BlockedSocketError(Exception):
    pass

def guarded_connect(self, address):
    # address can be a tuple (host, port) or a string (for unix sockets)
    host = address[0] if isinstance(address, tuple) else address

    # Allow local unix sockets and localhost
    if isinstance(host, str) and (
        host == "127.0.0.1"
        or host == "localhost"
        or host == "::1"
        or host.startswith("/") # Unix domain socket
    ):
        return _orig_connect(self, address)
    raise BlockedSocketError(f"Network access blocked in tests. Tried to connect to: {address}")

@pytest.fixture(autouse=True)
def block_network_access(monkeypatch):
    """
    Blocks all outbound network connections during tests to ensure
    no HTTP requests or model downloads occur silently.
    Allows loopback (127.0.0.1, localhost) for local database tests.
    """
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
