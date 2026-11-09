"""笔记本表：笔记的分组维度（笔记属于唯一笔记本，可为空=未分组）。"""
from datetime import datetime

from app.extensions import db


class Notebook(db.Model):
    __tablename__ = "notebook"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = db.Column(db.String(100), nullable=False)
    sort = db.Column(db.Integer, default=0)  # 前端排序用

    notes = db.relationship(
        "Note", backref="notebook", lazy="dynamic"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "sort": self.sort,
        }
