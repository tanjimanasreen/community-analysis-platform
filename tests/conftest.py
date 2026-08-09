import socket as _socket_module
import socket

import pytest

_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex


def _loopback_socket_available() -> bool:
    """Return True if this process can bind a loopback TCP socket."""
    try:
        with _socket_module.socket(
            _socket_module.AF_INET, _socket_module.SOCK_STREAM
        ) as s:
            s.bind(("127.0.0.1", 0))
        return True
    except OSError:
        return False


_LOOPBACK_AVAILABLE: bool = _loopback_socket_available()


@pytest.fixture(autouse=True)
def _skip_if_no_loopback(request):
    """Auto-skip tests marked requires_loopback when socket binding is unavailable."""
    if request.node.get_closest_marker("requires_loopback") and not _LOOPBACK_AVAILABLE:
        pytest.skip("loopback socket binding not available in this environment")


class BlockedSocketError(Exception):
    pass


def _host_from_address(address):
    if isinstance(address, tuple):
        return address[0]
    return address


def _is_allowed_host(host):
    if isinstance(host, bytes):
        host = host.decode("utf-8", errors="ignore")
    return isinstance(host, str) and (
        host in {"127.0.0.1", "localhost", "::1"} or host.startswith("/")
    )


def guarded_connect(self, address):
    if _is_allowed_host(_host_from_address(address)):
        return _orig_connect(self, address)
    raise BlockedSocketError(
        f"Network access blocked in tests. Tried to connect to: {address}"
    )


def guarded_connect_ex(self, address):
    if _is_allowed_host(_host_from_address(address)):
        return _orig_connect_ex(self, address)
    raise BlockedSocketError(
        f"Network access blocked in tests. Tried to connect to: {address}"
    )


@pytest.fixture(autouse=True)
def block_network_access(monkeypatch):
    """Block external traffic while allowing Prefect/local loopback sockets."""
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
