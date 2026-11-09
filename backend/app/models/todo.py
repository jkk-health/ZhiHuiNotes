"""待办表：note_id 实现与笔记的双向关联（为空=独立待办）。"""
from datetime import datetime

from app.extensions import db


class Todo(db.Model):
    __tablename__ = "todo"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    note_id = db.Column(
        db.Integer, db.ForeignKey("note.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.Date, nullable=True)  # 截止日期，过期由前端标红
    done = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "note_id": self.note_id,
            "title": self.title,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "done": self.done,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
