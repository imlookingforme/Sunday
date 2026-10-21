import os
import tempfile
import pytest
from sunday.core.broker.env_loader import parse_env_file, populate_token_pool_from_env
from sunday.core.broker.token_pool import TokenPool


def test_parse_env_file():
    content = """
    # Comment line
    OPENAI_API_KEY=sk-test-12345
    ANTHROPIC_API_KEY="sk-ant-test"
    GEMINI_API_KEY='gem-test'
    EMPTY_VAL=
    """
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write(content)
        path = f.name

    try:
        res = parse_env_file(path)
        assert res["OPENAI_API_KEY"] == "sk-test-12345"
        assert res["ANTHROPIC_API_KEY"] == "sk-ant-test"
        assert res["GEMINI_API_KEY"] == "gem-test"
        assert "EMPTY_VAL" not in res
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_populate_token_pool_from_env():
    pool = TokenPool()
    os.environ["OPENAI_API_KEY"] = "sk-env-test-key"
    try:
        populate_token_pool_from_env(pool)
        key = pool.get_key("openai")
        assert key == "sk-env-test-key"
    finally:
        del os.environ["OPENAI_API_KEY"]
