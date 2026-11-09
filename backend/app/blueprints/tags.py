"""标签接口（T1.3 + T1.6 标签管理）。

- GET    /api/tags        列表（带在册笔记数）
- PUT    /api/tags/<id>   重命名（用户级重名拒绝）
- DELETE /api/tags/<id>   删除（note_tag 关联随外键 CASCADE 清理）
"""
from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app.extensions import db
from app.models import Note, Tag, note_tag
from app.services.auth_service import login_required

tags_bp = Blueprint("tags", __name__)


@tags_bp.get("/tags")
@login_required
def list_tags(user):
    """标签列表 + 使用数（只统计未删除笔记；含回收站里的笔记不计）。"""
    usage = (
        db.session.query(note_tag.c.tag_id, func.count().label("cnt"))
        .join(Note, Note.id == note_tag.c.note_id)
        .filter(Note.is_deleted == False, Note.user_id == user.id)  # noqa: E712
        .group_by(note_tag.c.tag_id)
        .subquery()
    )
    rows = (
        db.session.query(Tag.id, Tag.name, func.coalesce(usage.c.cnt, 0))
        .outerjoin(usage, usage.c.tag_id == Tag.id)
        .filter(Tag.user_id == user.id)
        .order_by(Tag.name)
        .all()
    )
    return jsonify([{"id": r[0], "name": r[1], "note_count": r[2]} for r in rows])


def _tag_or_404(user_id: int, tag_id: int):
    """取当前用户的标签；不存在/他人标签统一 404。"""
    tag = db.session.get(Tag, tag_id)
    if tag is None or tag.user_id != user_id:
        return None
    return tag


@tags_bp.put("/tags/<int:tag_id>")
@login_required
def rename_tag(user, tag_id):
    """重命名标签：所有挂着它的笔记同步生效（改的是 Tag 行本身）。"""
    tag = _tag_or_404(user.id, tag_id)
    if tag is None:
        return jsonify(error="标签不存在"), 404

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()[:50]
    if not name:
        return jsonify(error="标签名不能为空"), 400

    # 用户级重名拒绝（唯一约束 uq_tag_user_name，提前查给出可读错误）
    clash = Tag.query.filter(Tag.user_id == user.id, Tag.name == name, Tag.id != tag_id).first()
    if clash is not None:
        return jsonify(error=f"已有标签「{name}」"), 400

    tag.name = name
    db.session.commit()
    return jsonify({**tag.to_dict(), "message": "已重命名"})


@tags_bp.delete("/tags/<int:tag_id>")
@login_required
def delete_tag(user, tag_id):
    """删除标签：note_tag 关联行随 db.relationship + FK CASCADE 一并清掉。"""
    tag = _tag_or_404(user.id, tag_id)
    if tag is None:
        return jsonify(error="标签不存在"), 404

    db.session.delete(tag)
    db.session.commit()
    return jsonify(message="标签已删除，相关笔记上的该标签已移除")
