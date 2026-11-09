"""认证业务层：注册 / 登录校验 / 会话管理 / 登录态装饰器。

会话方案：Flask 签名 Cookie（session）。前端与 API 同源（Vite 代理或
dist 托管），Cookie 自动携带，无需令牌，演示与讲解成本最低。
"""
from functools import wraps

from flask import jsonify, session

from app.extensions import db
from app.models import User


def register_user(username: str, password: str) -> User | None:
    """注册新用户。

    返回：User（成功）| None（用户名已占用）。
    校验不过抛 ValueError（由蓝图转 400）。
    """
    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        raise ValueError("用户名和密码不能为空")
    if len(username) > 50:
        raise ValueError("用户名最长 50 个字符")
    if len(password) < 6:
        raise ValueError("密码至少 6 位")

    if User.query.filter_by(username=username).first():
        return None

    user = User(username=username)
    user.set_password(password)  # PBKDF2 加盐哈希（模型层实现）
    db.session.add(user)
    db.session.commit()
    return user


def authenticate(username: str, password: str) -> User | None:
    """校验用户名密码：查无此人 / 密码不符统一返回 None（不泄露具体原因）。"""
    if not username:
        return None
    user = User.query.filter_by(username=username).first()
    if user is not None and user.check_password(password or ""):
        return user
    return None


# ---- 会话 ----

def login_session(user: User) -> None:
    """写入登录态（清旧防会话固定攻击）。"""
    session.clear()
    session["uid"] = user.id


def logout_session() -> None:
    session.clear()


def current_user() -> User | None:
    """从会话取当前用户（session 存在签名防篡改）。"""
    uid = session.get("uid")
    if uid is None:
        return None
    return db.session.get(User, uid)


def login_required(view):
    """登录态装饰器：视图函数第一个参数注入 current_user，未登录 401。"""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            return jsonify(error="未登录或登录已过期"), 401
        return view(user, *args, **kwargs)

    return wrapped
