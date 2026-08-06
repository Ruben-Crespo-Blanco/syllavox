import pytest

from syllavox.api.security import ALLOWED_ORIGINS, is_allowed_origin
from syllavox.api.server import ApiServer
from syllavox.constants import API_HOST
from tests.api_helpers import make_api_context


def test_missing_origin_is_allowed() -> None:
    assert is_allowed_origin(None) is True


def test_localhost_origins_are_allowed() -> None:
    for origin in ALLOWED_ORIGINS:
        assert is_allowed_origin(origin) is True


def test_unknown_origin_is_rejected() -> None:
    assert is_allowed_origin("https://example.com") is False


def test_api_server_rejects_non_localhost() -> None:
    context, _, _ = make_api_context(ready=False)

    with pytest.raises(ValueError):
        ApiServer(context, host="0.0.0.0")


def test_api_server_accepts_localhost() -> None:
    context, _, _ = make_api_context(ready=False)

    server = ApiServer(context)

    assert server.base_url.startswith(f"http://{API_HOST}:")
