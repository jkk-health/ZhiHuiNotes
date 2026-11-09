"""标签表 + 笔记-标签多对多关联表。

tag 与 note 通过 note_tag 关联（多对多）：
一篇笔记可挂多个标签，一个标签可挂多篇笔记。
"""
from app.extensions import db

# 关联表：无需模型类，db.Table 即建表
note_tag = db.Table(
    "note_tag",
    db.Column("note_id", db.Integer, db.ForeignKey("note.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(db.Model):
    __tablename__ = "tag"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = db.Column(db.String(50), nullable=False)

    # 同一用户下标签名唯一（不同用户可重名）
    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_tag_user_name"),)

    notes = db.relationship("Note", secondary=note_tag, backref="tags")

    def to_dict(self) -> dict:
        return {"id": self.id, "user_id": self.user_id, "name": self.name}
