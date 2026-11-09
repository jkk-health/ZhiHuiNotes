"""T1.3 笔记本分组 + 标签多对多。

验收对照：按笔记本/标签筛选正确 -> test_filter_by_notebook / test_filter_by_tag
（user_client / client 夹具见 conftest.py，两者会话独立）
"""


def _nb(client, name="课程笔记"):
    return client.post("/api/notebooks", json={"name": name}).get_json()


def _note(client, title="测试笔记", **extra):
    payload = {"title": title, "content_md": "正文", **extra}
    return client.post("/api/notes", json=payload).get_json()


# ---------------------------------------------------------------- 笔记本 --

def test_notebook_crud(user_client):
    assert user_client.get("/api/notebooks").get_json() == []

    rv = user_client.post("/api/notebooks", json={"name": "课程笔记"})
    assert rv.status_code == 201

    # 建笔记进笔记本 -> note_count 计数
    _note(user_client, title="在分组里", notebook_id=rv.get_json()["id"])
    nbs = user_client.get("/api/notebooks").get_json()
    assert nbs[0]["name"] == "课程笔记"
    assert nbs[0]["note_count"] == 1

    # 重命名
    nb_id = nbs[0]["id"]
    rv = user_client.put(f"/api/notebooks/{nb_id}", json={"name": "课堂笔记"})
    assert rv.get_json()["name"] == "课堂笔记"


def test_delete_notebook_keeps_notes(user_client):
    """删笔记本：笔记保留，归入未分组。"""
    nb = _nb(user_client)
    note = _note(user_client, notebook_id=nb["id"])

    assert user_client.delete(f"/api/notebooks/{nb['id']}").status_code == 200
    detail = user_client.get(f"/api/notes/{note['id']}").get_json()
    assert detail["notebook_id"] is None


def test_note_rejects_foreign_notebook(user_client, client):
    """不能用别人的笔记本 ID。"""
    client.post("/api/auth/register", json={"username": "stu2", "password": "abc123456"})
    other_nb = client.post("/api/notebooks", json={"name": "乙的笔记本"}).get_json()

    rv = user_client.post(
        "/api/notes", json={"title": "越权笔记", "notebook_id": other_nb["id"]}
    )
    assert rv.status_code == 400


# ---------------------------------------------------------------- 标签 --

def test_tags_on_create_and_replace(user_client):
    note = _note(user_client, tags=["算法", "期末复习"])
    assert sorted(note["tags"]) == sorted(["算法", "期末复习"])

    # PUT 整体替换
    rv = user_client.put(f"/api/notes/{note['id']}", json={"tags": ["动态规划"]})
    assert rv.get_json()["tags"] == ["动态规划"]

    # 契约端点 POST /notes/{id}/tags 再换回两个
    rv = user_client.post(f"/api/notes/{note['id']}/tags", json={"tags": ["算法", "DP"]})
    assert sorted(rv.get_json()["tags"]) == ["DP", "算法"]


def test_tag_list_with_counts(user_client):
    _note(user_client, title="A", tags=["算法"])
    _note(user_client, title="B", tags=["算法", "复习"])
    _note(user_client, title="C", tags=[])

    tags = {t["name"]: t["note_count"] for t in user_client.get("/api/tags").get_json()}
    assert tags == {"算法": 2, "复习": 1}  # 同名标签复用，不重复建行


def test_filter_by_notebook(user_client):
    """验收：按笔记本筛选正确。"""
    nb = _nb(user_client, name="课程笔记")
    _note(user_client, title="组内", notebook_id=nb["id"])
    _note(user_client, title="未分组笔记")

    in_nb = [n["title"] for n in user_client.get(f"/api/notes?notebook_id={nb['id']}").get_json()]
    assert in_nb == ["组内"]

    ungrouped = [
        n["title"] for n in user_client.get("/api/notes?notebook_id=0").get_json()
    ]
    assert ungrouped == ["未分组笔记"]


def test_filter_by_tag(user_client):
    """验收：按标签筛选正确。"""
    _note(user_client, title="有标签", tags=["算法"])
    _note(user_client, title="无标签")

    got = [n["title"] for n in user_client.get("/api/notes?tag=算法").get_json()]
    assert got == ["有标签"]
    # 查无此标签 -> 空列表而非报错
    assert user_client.get("/api/notes?tag=不存在").get_json() == []


# ---------------------------------------------------------------- 标签管理（T1.6） --

def _tag_id(client, name):
    return next(t for t in client.get("/api/tags").get_json() if t["name"] == name)["id"]


def test_tag_rename(user_client):
    _note(user_client, title="A", tags=["算法"])
    tid = _tag_id(user_client, "算法")

    rv = user_client.put(f"/api/tags/{tid}", json={"name": "动态规划"})
    assert rv.status_code == 200

    # 笔记上的标签同步生效：新名能搜到、旧名查无
    assert [n["title"] for n in user_client.get("/api/notes?tag=动态规划").get_json()] == ["A"]
    assert user_client.get("/api/notes?tag=算法").get_json() == []

    # 与已有标签重名 -> 拒绝
    _note(user_client, title="B", tags=["DP"])
    assert user_client.put(f"/api/tags/{tid}", json={"name": "DP"}).status_code == 400
    # 空名 -> 拒绝
    assert user_client.put(f"/api/tags/{tid}", json={"name": "   "}).status_code == 400


def test_tag_delete(user_client):
    note = _note(user_client, title="A", tags=["算法", "临时"])
    tid = _tag_id(user_client, "临时")

    assert user_client.delete(f"/api/tags/{tid}").status_code == 200
    # 标签列表里没了
    assert "临时" not in [t["name"] for t in user_client.get("/api/tags").get_json()]
    # 笔记上的该标签被移除，其余标签不受影响
    assert user_client.get(f"/api/notes/{note['id']}").get_json()["tags"] == ["算法"]


def test_tag_ops_reject_foreign(user_client, client):
    """不能改/删别人的标签（统一 404，不泄露存在性）。"""
    client.post("/api/auth/register", json={"username": "stu3", "password": "abc123456"})
    _note(client, title="乙的", tags=["乙标签"])
    other = _tag_id(client, "乙标签")

    assert user_client.put(f"/api/tags/{other}", json={"name": "改"}).status_code == 404
    assert user_client.delete(f"/api/tags/{other}").status_code == 404
