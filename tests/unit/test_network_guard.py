import socket
import urllib.request
import pytest
import threading

def test_network_guard_blocks_external_http():
    """
    Negative control test: Ensure the network guard blocks external connections.
    """
    with pytest.raises(Exception, match="Network access blocked") as exc_info:
        urllib.request.urlopen("http://example.com", timeout=1)
    assert "BlockedSocketError" in str(type(exc_info.value))

def test_network_guard_allows_loopback():
    """
    Control test: Ensure loopback connects are permitted.
    """
    # Start a temporary local TCP server bound to 127.0.0.1
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("127.0.0.1", 0))
    server_socket.listen(1)
    port = server_socket.getsockname()[1]
    
    def server_accept():
        try:
            conn, _ = server_socket.accept()
            conn.close()
        except Exception:
            pass

    server_thread = threading.Thread(target=server_accept, daemon=True)
    server_thread.start()

    try:
        # Connect to that actual listening port and prove connection succeeds
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", port))
        s.close()
    except Exception as e:
        if "BlockedSocketError" in str(type(e)):
            pytest.fail("Network guard improperly blocked a loopback connection.")
        raise
    finally:
        server_socket.close()

def test_network_guard_socket_methods():
    """
    Test that external access through socket.socket.connect(...) and socket.socket.connect_ex(...) is blocked.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with pytest.raises(Exception, match="Network access blocked") as exc_info:
        s.connect(("8.8.8.8", 53))
    assert "BlockedSocketError" in str(type(exc_info.value))
    
    with pytest.raises(Exception, match="Network access blocked") as exc_info:
        s.connect_ex(("8.8.8.8", 53))
    assert "BlockedSocketError" in str(type(exc_info.value))
    s.close()
