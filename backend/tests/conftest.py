"""pytest 公共夹具：临时库应用实例 + 测试客户端 + 演示用户。

库用 tmp_path 下的 SQLite 文件（避开开发库 app.db），每测独立。

两个踩过的坑：
1. 不要在夹具函数内写 `import app.models`——import 语句会把局部名 `app`
   重新绑定为包模块，覆盖 Flask 实例（Sprint 1 踩坑记录）。
2. 测试库 URI 必须通过 create_app(**overrides) 传进去，不能建完 app 再改
   app.config：Flask-SQLAlchemy 3.x 在 init_app 时就按当时的 URI 建 engine，
   事后改配置不生效，drop_all() 会把开发库 app.db 清光（Sprint 2 踩坑记录）。
"""
import pytest

# models 随包导入完成注册（create_all 前必须发生）
from app import create_app, models  # noqa: F401
from app.extensions import db as _db


@pytest.fixture()
def app(tmp_path):
    # 测试库 + TESTING 必须在 create_app 阶段就传进去（见文件头第 2 条踩坑）
    flask_app = create_app(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
    )
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user_client(app):
    """注册并登录 stu 的独立客户端（与匿名 client 各持会话，互不影响）。"""
    c = app.test_client()
    c.post("/api/auth/register", json={"username": "stu", "password": "abc123456"})
    return c


@pytest.fixture()
def demo_user(app):
    """预置 demo/demo123456（走模型层，比 HTTP 注册快）。"""
    from app.models import User

    with app.app_context():
        user = User(username="demo")
        user.set_password("demo123456")
        _db.session.add(user)
        _db.session.commit()
        yield user
