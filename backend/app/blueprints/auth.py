"""认证接口：POST /api/auth/register · /login · /logout，GET /api/auth/me。"""
from flask import Blueprint, jsonify, request

from app.services import auth_service

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/auth/register")
def register():
    """注册成功即登录（201 返回用户）；重名 409；参数不合法 400。"""
    data = request.get_json(silent=True) or {}
    try:
        user = auth_service.register_user(data.get("username"), data.get("password"))
    except ValueError as e:
        return jsonify(error=str(e)), 400
    if user is None:
        return jsonify(error="用户名已被占用"), 409
    auth_service.login_session(user)
    return jsonify(user.to_dict()), 201


@auth_bp.post("/auth/login")
def login():
    """登录成功 200；用户名或密码错误一律 401（不区分，防账号枚举）。"""
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    user = auth_service.authenticate(username, data.get("password"))
    if user is None:
        return jsonify(error="用户名或密码错误"), 401
    auth_service.login_session(user)
    return jsonify(user.to_dict())


@auth_bp.post("/auth/logout")
def logout():
    auth_service.logout_session()
    return jsonify(message="已退出登录")


@auth_bp.get("/auth/me")
def me():
    """前端刷新后恢复登录态用：200 当前用户 / 401 未登录。"""
    user = auth_service.current_user()
    if user is None:
        return jsonify(error="未登录"), 401
    return jsonify(user.to_dict())
