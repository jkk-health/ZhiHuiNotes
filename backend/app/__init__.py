"""应用工厂：create_app() 创建并装配 Flask 实例。"""
import sqlite3
from pathlib import Path

from flask import Flask, jsonify
from sqlalchemy import Engine, event

from app.config import Config
from app.extensions import db

# 前端构建产物目录（交付态：flask run 一条命令托管全站，断网可演示）
DIST_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@event.listens_for(Engine, "connect")
def _sqlite_fk_on(dbapi_connection, _):
    """SQLite 默认不强制外键，连接时显式打开（用户删除级联清理其数据）。"""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(config_class=Config, **config_overrides):
    """应用工厂。

    config_overrides 会覆盖配置类里的同名项，且**在 db.init_app 之前生效**——
    Flask-SQLAlchemy 3.x 在 init_app 那一刻就按当时的 URI 建好 engine，
    之后再改 app.config 对 engine 无效（测试库曾因此删错开发库 app.db）。
    """
    # 存在 dist 时托管之（static_url_path 置空 = 静态资源挂站点根路径）
    app = Flask(
        __name__,
        static_folder=str(DIST_DIR) if DIST_DIR.exists() else None,
        static_url_path="",
    )
    app.config.from_object(config_class)
    if config_overrides:
        app.config.update(config_overrides)

    # 扩展
    db.init_app(app)

    # 蓝图（统一挂在 /api 前缀下，只对外提供 REST 接口）
    from app.blueprints.auth import auth_bp
    from app.blueprints.health import health_bp
    from app.blueprints.notes import notes_bp
    from app.blueprints.notebooks import notebooks_bp
    from app.blueprints.tags import tags_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(notes_bp, url_prefix="/api")
    app.register_blueprint(notebooks_bp, url_prefix="/api")
    app.register_blueprint(tags_bp, url_prefix="/api")
    from app.blueprints.todos import todos_bp
    from app.blueprints.mindmaps import mindmaps_bp
    from app.blueprints.bills import bills_bp
    from app.blueprints.ai import ai_bp
    from app.services.api_utils import ApiError
    from werkzeug.exceptions import HTTPException
    for blueprint in (todos_bp, mindmaps_bp, bills_bp, ai_bp):
        app.register_blueprint(blueprint, url_prefix="/api")

    @app.errorhandler(ApiError)
    def api_error(error):
        db.session.rollback()
        return jsonify(error=error.message), error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        from flask import request
        if request.path.startswith('/api/'):
            return jsonify(error=error.description), error.code
        return error

    # CLI 命令
    from app.cli import register_cli

    register_cli(app)

    # ---- SPA fallback：非 /api 的 404 回退 index.html（Vue Router history 模式）----
    # 用 errorhandler 而非 catch-all 路由：static_url_path="" 时静态路由 /<path:filename>
    # 优先级高于自定义 catch-all，路由冲突会让 fallback 失效
    if DIST_DIR.exists():

        @app.errorhandler(404)
        def spa_fallback(_):
            from flask import request

            if request.path.startswith("/api/"):
                return jsonify(error="Not Found"), 404
            return app.send_static_file("index.html")

    return app
