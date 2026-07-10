from __future__ import annotations

import requests

from amar_passport.repository import PassportKnowledgeBase


def test_remote_failure_uses_local_database(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.ConnectionError("simulated offline environment")

    monkeypatch.setattr(requests, "get", fail)
    knowledge, source = PassportKnowledgeBase().load(prefer_remote=True)

    assert source.startswith("local_fallback")
    assert knowledge["fees_2026"]["64_pages"]["10_years"]["super_express"] == 13800

