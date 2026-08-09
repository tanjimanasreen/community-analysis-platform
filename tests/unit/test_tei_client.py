from __future__ import annotations

from src.themes.tei_client import TEIClient


class _Response:
    status_code = 200
    text = ""

    @staticmethod
    def json():
        return [[1.0, 0.0]]


class _Session:
    def __init__(self):
        self.calls = []
        self.closed = False

    def post(self, endpoint, *, json, headers, timeout):
        self.calls.append((endpoint, json, headers, timeout))
        return _Response()

    def close(self):
        self.closed = True


def test_tei_client_preserves_normalized_similarity_default():
    session = _Session()
    client = TEIClient(session=session)

    result = client.encode(["theme"])

    assert result.shape == (1, 2)
    assert session.calls[0][1]["normalize"] is True


def test_tei_client_can_disable_normalization_for_euclidean_clustering():
    session = _Session()
    client = TEIClient(session=session, normalize=False)

    client.encode(["theme"])

    assert session.calls[0][1]["normalize"] is False
