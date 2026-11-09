"""T1.2 笔记 CRUD。

验收对照：
- 建改删查全通        -> 本文件各用例
- 未登录访问 API 401  -> test_notes_require_login
（user_client / client 夹具见 conftest.py，两者会话独立）
"""


def _create(client, title="测试笔记", content="# 标题\n\n正文"):
    return client.post(
        "/api/notes", json={"title": title, "content_md": content}
    )


def test_notes_require_login(client):
    """验收：未登录访问业务 API 返回 401。"""
    assert client.get("/api/notes").status_code == 401


def test_create_note(user_client):
    rv = _create(user_client)
    assert rv.status_code == 201
    data = rv.get_json()
    assert data["title"] == "测试笔记"
    assert data["content_md"] == "# 标题\n\n正文"
    assert data["is_deleted"] is False


def test_create_note_empty_title_400(user_client):
    rv = user_client.post("/api/notes", json={"title": "  ", "content_md": ""})
    assert rv.status_code == 400


def test_list_notes(user_client):
    _create(user_client, title="笔记A")
    _create(user_client, title="笔记B")

    rv = user_client.get("/api/notes")
    assert rv.status_code == 200
    data = rv.get_json()
    assert len(data) == 2
    # 列表不下发正文（省流量），标题存在
    assert "content_md" not in data[0]
    assert {n["title"] for n in data} == {"笔记A", "笔记B"}


def test_get_note_detail(user_client):
    note_id = _create(user_client, content="正文内容XYZ").get_json()["id"]

    rv = user_client.get(f"/api/notes/{note_id}")
    assert rv.status_code == 200
    assert rv.get_json()["content_md"] == "正文内容XYZ"


def test_update_note(user_client):
    note_id = _create(user_client).get_json()["id"]

    rv = user_client.put(
        f"/api/notes/{note_id}",
        json={"title": "改过标题", "content_md": "## 新正文"},
    )
    assert rv.status_code == 200
    assert rv.get_json()["title"] == "改过标题"

    detail = user_client.get(f"/api/notes/{note_id}").get_json()
    assert detail["content_md"] == "## 新正文"


def test_delete_note_soft(user_client):
    """删除 = 软删除：列表不再出现，详情 404，数据库仍可恢复（T1.4）。"""
    note_id = _create(user_client).get_json()["id"]

    assert user_client.delete(f"/api/notes/{note_id}").status_code == 200
    assert user_client.get("/api/notes").get_json() == []
    assert user_client.get(f"/api/notes/{note_id}").status_code == 404


def test_note_isolation_between_users(user_client, client):
    """甲的笔记乙不可见（404，不泄露存在性）。"""
    note_id = _create(user_client).get_json()["id"]

    client.post("/api/auth/register", json={"username": "stu2", "password": "abc123456"})
    assert client.get(f"/api/notes/{note_id}").status_code == 404
    assert client.put(f"/api/notes/{note_id}", json={"title": "hack"}).status_code == 404
