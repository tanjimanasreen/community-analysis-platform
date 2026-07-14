import socket
import threading
import urllib.error
import urllib.request

import pytest

from conftest import BlockedSocketError


def _contains_blocked_error(exc: BaseException) -> bool:
    current = exc
    while current is not None:
        if isinstance(current, BlockedSocketError):
            return True
        current = current.__cause__ or current.__context__
    return "Network access blocked" in repr(exc)


def test_network_guard_blocks_external_http():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with pytest.raises(Exception) as exc_info:
        opener.open("http://93.184.216.34", timeout=1)
    assert _contains_blocked_error(exc_info.value)


def test_network_guard_allows_real_loopback_connection():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        server_socket.listen(1)
        port = server_socket.getsockname()[1]

        accepted = threading.Event()

        def server_accept():
            connection, _ = server_socket.accept()
            with connection:
                accepted.set()

        server_thread = threading.Thread(target=server_accept, daemon=True)
        server_thread.start()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect(("127.0.0.1", port))

        assert accepted.wait(timeout=1)
        server_thread.join(timeout=1)


def test_network_guard_blocks_connect_and_connect_ex():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        with pytest.raises(BlockedSocketError, match="Network access blocked"):
            client.connect(("8.8.8.8", 53))

        with pytest.raises(BlockedSocketError, match="Network access blocked"):
            client.connect_ex(("8.8.8.8", 53))
