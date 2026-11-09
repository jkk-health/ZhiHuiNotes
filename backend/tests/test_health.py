"""冒烟测试：/api/health 返回 200 且带服务标识（TDD 基线，Sprint 6 扩充）。"""
import pytest

from app import create_app


@pytest.fixture()
def client():
    # 冒烟测试不碰库，但仍指向内存库，杜绝任何误伤开发库 app.db 的可能
    app = create_app(SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "zhihui-notes-api"
    assert data["ai_engine"] in ("api", "local")
