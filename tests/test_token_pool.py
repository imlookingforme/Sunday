"""Tests for sunday.core.broker.token_pool – TokenPool & CredentialEntry."""

import time

import pytest

from sunday.core.broker.token_pool import CredentialEntry, TokenPool


# ── 1. Basic add & retrieve ──────────────────────────────────────────────

def test_add_and_get_key():
    """Add 2 keys for 'openai'; get_key should return the first one."""
    pool = TokenPool()
    pool.add_key("openai", "sk-aaa")
    pool.add_key("openai", "sk-bbb")

    assert pool.get_key("openai") == "sk-aaa"


# ── 2. Non-existent provider ─────────────────────────────────────────────

def test_get_key_empty_provider():
    """get_key for a provider with no registered keys returns None."""
    pool = TokenPool()
    assert pool.get_key("nonexistent") is None


# ── 3. Round-robin rotation ──────────────────────────────────────────────

def test_round_robin_rotation():
    """Add 3 keys, rotate twice, verify it cycles through them in order."""
    pool = TokenPool()
    pool.add_keys("openai", ["sk-aaa", "sk-bbb", "sk-ccc"])

    first = pool.get_key("openai")       # sk-aaa (index 0)
    second = pool.rotate("openai")       # sk-bbb (index 1)
    third = pool.rotate("openai")        # sk-ccc (index 2)

    assert first == "sk-aaa"
    assert second == "sk-bbb"
    assert third == "sk-ccc"


# ── 4. mark_exhausted auto-rotates ───────────────────────────────────────

def test_mark_exhausted_auto_rotates():
    """Exhausting the current key should auto-rotate to the next one."""
    pool = TokenPool()
    pool.add_key("openai", "sk-aaa")
    pool.add_key("openai", "sk-bbb")

    # Current key is sk-aaa (index 0); exhaust it
    new_key = pool.mark_exhausted("openai")

    assert new_key == "sk-bbb"


# ── 5. All keys exhausted – fallback ────────────────────────────────────

def test_all_keys_exhausted_fallback():
    """When every key is exhausted, get_key still returns something (first key)."""
    pool = TokenPool()
    pool.add_key("openai", "sk-aaa")
    pool.add_key("openai", "sk-bbb")

    # Exhaust both manually via the CredentialEntry objects
    for entry in pool._pools["openai"]:
        entry.mark_exhausted()

    result = pool.get_key("openai")
    # Should still return the first key as a fallback
    assert result is not None
    assert result == "sk-aaa"


# ── 6. Backoff recovery ─────────────────────────────────────────────────

def test_backoff_recovery():
    """A key marked exhausted becomes available again after backoff expires."""
    entry = CredentialEntry(value="sk-aaa", provider="openai")
    entry.mark_exhausted()

    assert entry.is_available is False

    # Simulate backoff expiry by pushing exhausted_at far into the past
    entry.exhausted_at = time.time() - entry.backoff_seconds - 1

    assert entry.is_available is True


# ── 7. Pool status reporting ────────────────────────────────────────────

def test_pool_status():
    """get_pool_status returns correct total / available / exhausted counts."""
    pool = TokenPool()
    pool.add_keys("openai", ["sk-aaa", "sk-bbb", "sk-ccc"])

    # Exhaust the first key
    pool._pools["openai"][0].mark_exhausted()

    status = pool.get_pool_status("openai")

    assert status["provider"] == "openai"
    assert status["total"] == 3
    assert status["available"] == 2
    assert status["exhausted"] == 1


# ── 8. Multiple independent providers ───────────────────────────────────

def test_multiple_providers():
    """Keys for different providers rotate independently."""
    pool = TokenPool()
    pool.add_keys("openai", ["sk-aaa", "sk-bbb"])
    pool.add_keys("anthropic", ["ant-111", "ant-222"])

    # Rotate openai forward; anthropic should remain unaffected
    pool.rotate("openai")

    assert pool.get_key("openai") == "sk-bbb"
    assert pool.get_key("anthropic") == "ant-111"


# ── 9. list_providers ───────────────────────────────────────────────────

def test_list_providers():
    """list_providers returns every provider that has registered keys."""
    pool = TokenPool()
    pool.add_key("openai", "sk-aaa")
    pool.add_key("anthropic", "ant-111")
    pool.add_key("gemini", "gem-xyz")

    providers = pool.list_providers()
    assert set(providers) == {"openai", "anthropic", "gemini"}


# ── 10. get_all_status ──────────────────────────────────────────────────

def test_get_all_status():
    """get_all_status returns a status dict keyed by every provider."""
    pool = TokenPool()
    pool.add_key("openai", "sk-aaa")
    pool.add_key("anthropic", "ant-111")

    all_status = pool.get_all_status()

    assert "openai" in all_status
    assert "anthropic" in all_status
    assert all_status["openai"]["total"] == 1
    assert all_status["anthropic"]["total"] == 1
