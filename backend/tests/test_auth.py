"""T1.1 认证：注册 / 登录 / 退出 / 登录态。

验收对照：
- 错误密码 401           -> test_login_wrong_password_401
- 未登录访问 API 返回 401 -> test_api_requires_login
"""


def test_register_then_me(client):
    """注册即登录，/me 能取到当前用户。"""
    rv = client.post(
        "/api/auth/register", json={"username": "stu1", "password": "abc123456"}
    )
    assert rv.status_code == 201
    assert rv.get_json()["username"] == "stu1"

    rv = client.get("/api/auth/me")
    assert rv.status_code == 200
    assert rv.get_json()["username"] == "stu1"


def test_register_duplicate_username(client):
    client.post("/api/auth/register", json={"username": "stu1", "password": "abc123456"})
    rv = client.post(
        "/api/auth/register", json={"username": "stu1", "password": "xyz987654"}
    )
    assert rv.status_code == 409


def test_register_invalid_payload(client):
    """空用户名 / 短密码 -> 400。"""
    rv = client.post("/api/auth/register", json={"username": "  ", "password": "abc123456"})
    assert rv.status_code == 400
    rv = client.post("/api/auth/register", json={"username": "ok", "password": "123"})
    assert rv.status_code == 400


def test_login_ok(client, demo_user):
    rv = client.post("/api/auth/login", json={"username": "demo", "password": "demo123456"})
    assert rv.status_code == 200
    assert rv.get_json()["username"] == "demo"


def test_login_wrong_password_401(client, demo_user):
    """验收：错误密码 401。"""
    rv = client.post("/api/auth/login", json={"username": "demo", "password": "wrong-pwd"})
    assert rv.status_code == 401


def test_login_unknown_user_401(client):
    rv = client.post("/api/auth/login", json={"username": "nobody", "password": "whatever"})
    assert rv.status_code == 401


def test_logout_clears_session(client):
    client.post("/api/auth/register", json={"username": "stu2", "password": "abc123456"})
    assert client.get("/api/auth/me").status_code == 200

    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401
