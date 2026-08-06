import pytest
from syllavox.api.server import ApiServer
from tests.api_helpers import make_api_context


def test_api_server_rejects_non_localhost() -> None:
    context, _, _ = make_api_context(ready=False)

    with pytest.raises(ValueError):
        ApiServer(context, host="0.0.0.0")


def test_api_server_accepts_default_localhost() -> None:
    context, _, _ = make_api_context(ready=False)

    server = ApiServer(context)

    assert server.base_url == "http://127.0.0.1:8765/v1"
