import socket

import pytest


_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex


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
        host in {"127.0.0.1", "localhost", "::1"}
        or host.startswith("/")
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
