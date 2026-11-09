"""笔记表：核心实体，软删除进回收站。

正文双写：
- content_html：富文本正文（Quill 所见即所得编辑器的 HTML），前端展示用它；
- content_md ：后端从清理后的 HTML 生成的纯文本副本，用于全文搜索、AI 与导图；旧数据仍可能是 Markdown。名字沿用 md 是为了不动历史数据、不加第二张表。
"""
from datetime import datetime

from app.extensions import db
from app.models.tag import note_tag  # noqa: F401  确保关联表随模型注册


class Note(db.Model):
    __tablename__ = "note"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notebook_id = db.Column(
        db.Integer, db.ForeignKey("notebook.id", ondelete="SET NULL"), nullable=True, index=True
    )  # 删除笔记本后笔记保留、归为未分组
    title = db.Column(db.String(200), nullable=False)
    content_md = db.Column(db.Text, nullable=False, default="")
    content_html = db.Column(db.Text, nullable=False, default="")  # 富文本正文（Quill）
    is_top = db.Column(db.Boolean, default=False)  # 置顶
    is_deleted = db.Column(db.Boolean, default=False, index=True)  # 软删除=回收站
    is_public = db.Column(db.Boolean, default=False)  # 社区公开（Sprint 5）
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    todos = db.relationship("Todo", backref="note", lazy="dynamic")
    mindmaps = db.relationship("Mindmap", backref="note", lazy="dynamic")

    def to_dict(self, with_content: bool = True) -> dict:
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "notebook_id": self.notebook_id,
            "title": self.title,
            "is_top": self.is_top,
            "is_deleted": self.is_deleted,
            "is_public": self.is_public,
            "tags": [t.name for t in self.tags],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if with_content:  # 列表接口不传正文，节省流量
            data["content_md"] = self.content_md
            data["content_html"] = self.content_html
        return data
