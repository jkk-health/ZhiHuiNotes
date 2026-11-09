"""T1.4 全文搜索 + 置顶 + 回收站。

验收对照：
- 注入串/XSS 串输入不崩且被转义 -> test_sql_injection_string_safe /
  test_xss_string_roundtrip（API 层不崩；前端转义由 DOMPurify 负责）
"""


def _note(client, title, content="", **extra):
    payload = {"title": title, "content_md": content, **extra}
    return client.post("/api/notes", json=payload).get_json()


# ---------------------------------------------------------------- 搜索 --

def test_search_by_title(user_client):
    _note(user_client, "动态规划入门", "正文A")
    _note(user_client, "无关标题", "正文里提到动态规划")

    got = [n["title"] for n in user_client.get("/api/notes/search?q=动态规划").get_json()]
    assert len(got) == 2  # 标题命中 + 正文命中


def test_search_by_content_keyword(user_client):
    _note(user_client, "笔记甲", "TCP 三次握手的细节")
    _note(user_client, "笔记乙", "毫不相干")

    got = [n["title"] for n in user_client.get("/api/notes/search?q=三次握手").get_json()]
    assert got == ["笔记甲"]


def test_search_with_tag_filter(user_client):
    _note(user_client, "算法文", "内容", tags=["算法"])
    _note(user_client, "算法笔记2", "内容", tags=["复习"])

    got = [
        n["title"]
        for n in user_client.get("/api/notes/search?q=算法&tag=复习").get_json()
    ]
    assert got == ["算法笔记2"]


def test_search_requires_q(user_client):
    assert user_client.get("/api/notes/search").status_code == 400
    assert user_client.get("/api/notes/search?q=%20").status_code == 400  # 空白


def test_sql_injection_string_safe(user_client):
    """注入串只是普通文本：不崩、查不炸、表还在。"""
    _note(user_client, "正常笔记", "正常内容")

    rv = user_client.get(
        "/api/notes/search?q='; DROP TABLE note; --"
    )
    assert rv.status_code == 200  # 不崩

    # 表还在，能继续正常查
    got = user_client.get("/api/notes/search?q=正常").get_json()
    assert [n["title"] for n in got] == ["正常笔记"]


def test_xss_string_roundtrip(user_client):
    """XSS 串原样存取（JSON 转义），不在 API 层丢信息；渲染层由 DOMPurify 消毒。"""
    xss = '<script>alert(1)</script><img src=x onerror=alert(2)>'
    note = _note(user_client, f"标题{xss}", f"正文{xss}")

    detail = user_client.get(f"/api/notes/{note['id']}").get_json()
    assert xss in detail["title"]
    assert xss in detail["content_md"]

    # 搜索 XSS 串也能命中且不崩
    rv = user_client.get("/api/notes/search?q=<script>")
    assert rv.status_code == 200


# ---------------------------------------------------------------- 置顶 --

def test_pin_note_to_top(user_client):
    _note(user_client, "旧笔记1")
    _note(user_client, "旧笔记2")
    top_id = _note(user_client, "要置顶的")["id"]

    rv = user_client.put(f"/api/notes/{top_id}", json={"is_top": True})
    assert rv.get_json()["is_top"] is True

    titles = [n["title"] for n in user_client.get("/api/notes").get_json()]
    assert titles[0] == "要置顶的"  # 置顶优先
    assert len(titles) == 3


def test_unpin(user_client):
    note_id = _note(user_client, "置顶过", tags=[])["id"]
    user_client.put(f"/api/notes/{note_id}", json={"is_top": True})
    rv = user_client.put(f"/api/notes/{note_id}", json={"is_top": False})
    assert rv.get_json()["is_top"] is False


# ---------------------------------------------------------------- 回收站 --

def test_trash_list_and_restore(user_client):
    keep_id = _note(user_client, "保留")["id"]
    gone_id = _note(user_client, "要删的")["id"]

    user_client.delete(f"/api/notes/{gone_id}")

    # 正常列表只剩保留的
    assert [n["title"] for n in user_client.get("/api/notes").get_json()] == ["保留"]

    # 回收站能看到被删的
    trash = user_client.get("/api/notes?trash=1").get_json()
    assert [n["title"] for n in trash] == ["要删的"]

    # 恢复 -> 回到正常列表，回收站清空
    assert user_client.post(f"/api/notes/{gone_id}/restore").status_code == 200
    assert len(user_client.get("/api/notes").get_json()) == 2
    assert user_client.get("/api/notes?trash=1").get_json() == []


def test_restore_not_in_trash_is_noop(user_client):
    note_id = _note(user_client, "没删过")["id"]
    rv = user_client.post(f"/api/notes/{note_id}/restore")
    assert rv.status_code == 200  # 幂等：不在回收站也正常返回


def test_trashed_note_hidden_from_search(user_client):
    _note(user_client, "搜索目标", "关键词在这里")
    note_id = user_client.get("/api/notes/search?q=搜索目标").get_json()[0]["id"]

    user_client.delete(f"/api/notes/{note_id}")
    assert user_client.get("/api/notes/search?q=搜索目标").get_json() == []
