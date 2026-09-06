from __future__ import annotations

from app.worker import storage as module


class _Settings:
    supabase = type("S", (), {"url": "https://example.supabase.co", "service_role_key": "key"})()
    infra = type("I", (), {"sources_bucket": "sources"})()


class _Response:
    def __init__(self, payload: object | None = None) -> None:
        self.status_code = 200
        self._payload = payload if payload is not None else []
        self.text = ""
        self.reason_phrase = "OK"

    def json(self) -> object:
        return self._payload


def test_delete_prefix_lists_then_removes_files(monkeypatch: object) -> None:
    listed = {
        "workspaces/ws/": [{"name": "study-sheets", "id": None}],
        "workspaces/ws/study-sheets/": [{"name": "notes.md", "id": "obj-1"}],
    }
    deleted: list[list[str]] = []

    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def post(self, url: str, headers: object = None, json: dict | None = None) -> _Response:
            prefix = (json or {}).get("prefix")
            return _Response(listed.get(prefix, []))

        def request(
            self,
            method: str,
            url: str,
            headers: object = None,
            json: dict | None = None,
        ) -> _Response:
            deleted.append(list((json or {}).get("prefixes") or []))
            return _Response()

    monkeypatch.setattr(module, "get_settings", lambda: _Settings())
    monkeypatch.setattr(module.httpx, "Client", FakeClient)

    removed = module.WorkerStorage().delete_prefix("workspaces/ws/")
    assert removed == 1
    assert deleted == [["workspaces/ws/study-sheets/notes.md"]]
