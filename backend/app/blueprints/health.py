"""健康检查：前后端联调的冒烟端点。"""
from flask import Blueprint, current_app, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    """GET /api/health -> 200，返回服务标识与 AI 引擎模式（答辩演示用）。"""
    return jsonify(
        status="ok",
        service="zhihui-notes-api",
        version="0.1.0",
        ai_engine="api" if current_app.config["DEEPSEEK_API_KEY"] else "local",
    )
