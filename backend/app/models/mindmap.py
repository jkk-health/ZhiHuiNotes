"""思维导图表：存储 jsMind 格式 JSON；笔记是源，导图是视图产物（单向，不回写）。"""
from datetime import datetime

from app.extensions import db


class Mindmap(db.Model):
    __tablename__ = "mindmap"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    note_id = db.Column(
        db.Integer, db.ForeignKey("note.id", ondelete="CASCADE"), nullable=True, index=True
    )  # 由笔记生成的导图记录来源笔记
    title = db.Column(db.String(200), nullable=False)
    map_json = db.Column(db.Text, nullable=False, default="{}")
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "note_id": self.note_id,
            "title": self.title,
            "map_json": self.map_json,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
