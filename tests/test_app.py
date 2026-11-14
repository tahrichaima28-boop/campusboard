from datetime import datetime

import app as app_module


class FakeCursor:
    def execute(self, *args, **kwargs):
        pass

    def fetchone(self):
        return (1,)

    def fetchall(self):
        return [(1, "Covoiturage Tunis", "Place libre lundi", datetime(2026, 11, 13, 10, 0))]


class FakeConn:
    def cursor(self):
        return FakeCursor()

    def commit(self):
        pass

    def close(self):
        pass


def client(monkeypatch):
    monkeypatch.setattr(app_module, "get_conn", lambda: FakeConn())
    return app_module.app.test_client()


def test_health(monkeypatch):
    r = client(monkeypatch).get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_list_posts(monkeypatch):
    r = client(monkeypatch).get("/posts")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 1
    assert data[0]["title"] == "Covoiturage Tunis"


def test_create_post(monkeypatch):
    r = client(monkeypatch).post("/posts", json={"title": "Objet perdu", "content": "Cle USB"})
    assert r.status_code == 201
    assert r.get_json()["id"] == 1


def test_create_post_without_title(monkeypatch):
    r = client(monkeypatch).post("/posts", json={"content": "sans titre"})
    assert r.status_code == 400
