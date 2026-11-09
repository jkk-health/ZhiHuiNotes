"""自定义 CLI 命令。

- flask init-db   建表（幂等），建完自动补齐新增列；
- flask upgrade-db 只补齐新增列，用于已经跑过 init-db 的旧库。
"""
import click
from flask import current_app
from sqlalchemy import text

from app.extensions import db

# (表名, 列名, 列定义)：新增字段都登记在这里，一条命令把旧库补齐
PENDING_COLUMNS = [
    ("note", "content_html", "TEXT NOT NULL DEFAULT ''"),
]


def ensure_columns() -> list:
    """检查并补建缺失的列，返回本次真正新增的列名列表。"""
    added = []
    with db.engine.connect() as conn:
        for table, column, ddl in PENDING_COLUMNS:
            cols = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))]
            if column not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
                added.append(f"{table}.{column}")
        conn.commit()
    return added


def register_cli(app):
    @app.cli.command("init-db")
    def init_db_command():
        """按模型建表（幂等：已存在的表不会重建），并补齐新增列。"""
        # 导入模型包触发注册
        import app.models  # noqa: F401

        with current_app.app_context():
            db.create_all()
            added = ensure_columns()  # 旧库建过表，新字段靠这里补
        click.echo(
            "数据库初始化完成（8 张核心表就绪）。"
            + (f" 本次补齐列：{', '.join(added)}" if added else "")
        )

    @app.cli.command("upgrade-db")
    def upgrade_db_command():
        """给已有库补建新增列（不删数据）。"""
        import app.models  # noqa: F401

        with current_app.app_context():
            db.create_all()  # 万一有全新的表
            added = ensure_columns()
        click.echo(f"数据库升级完成，新增列：{', '.join(added) if added else '（无，已是最新）'}")
