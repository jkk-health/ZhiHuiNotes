"""笔记接口：CRUD（T1.2）+ 笔记本/标签（T1.3）+ 搜索/置顶/回收站（T1.4）。

列表默认排除回收站，置顶优先、更新时间倒序。
"""
from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Note, Notebook, Tag, note_tag
from app.services.auth_service import login_required
from app.services.api_utils import payload, text, ApiError
from app.services.content_service import apply_content

notes_bp = Blueprint("notes", __name__)


# ---------------------------------------------------------------- 供内部复用 --

def _note_or_404(user_id: int, note_id: int):
    """取当前用户的笔记；不存在/他人笔记统一 404（不泄露存在性）。

    返回 (note, None) 或 (None, 404 响应)。
    """
    note = db.session.get(Note, note_id)
    if note is None or note.user_id != user_id:
        return None, (jsonify(error="笔记不存在"), 404)
    return note, None


def _apply_notebook(user_id: int, note: Note, notebook_id) -> None:
    """校验并写入笔记本归属（notebook_id 为 None/0 = 未分组）。"""
    if notebook_id is not None and (isinstance(notebook_id, bool) or not isinstance(notebook_id, int)):
        raise ValueError('笔记本 ID 必须是整数或 null')
    if not notebook_id:  # None 或 0 都视为未分组
        note.notebook_id = None
        return
    nb = db.session.get(Notebook, notebook_id)
    if nb is None or nb.user_id != user_id:
        raise ValueError("笔记本不存在")
    note.notebook_id = nb.id


def _set_tags(user_id: int, note: Note, names: list) -> None:
    """整体替换笔记标签：不存在的名字按需创建（用户级去重）。"""
    if not isinstance(names, list) or any(not isinstance(n, str) for n in names):
        raise ValueError('tags 必须是字符串数组')
    cleaned, seen = [], set()
    for raw in names or []:
        name = (raw or "").strip()[:50]
        if name and name not in seen:
            seen.add(name)
            cleaned.append(name)

    tags = []
    for name in cleaned:
        tag = Tag.query.filter_by(user_id=user_id, name=name).first()
        if tag is None:
            tag = Tag(user_id=user_id, name=name)
            db.session.add(tag)
        tags.append(tag)
    note.tags = tags  # 多对多关联表随 commit 同步


def _filter_notes_query(user_id: int, query_params):
    """按查询参数组装列表过滤（trash / notebook_id / tag / q）。"""
    trash = bool(query_params.get("trash", type=int))
    query = Note.query.filter_by(user_id=user_id, is_deleted=trash)

    notebook_id = query_params.get("notebook_id", type=int)
    if notebook_id is not None:
        if notebook_id == 0:  # 约定：0 = 未分组
            query = query.filter(Note.notebook_id.is_(None))
        else:
            query = query.filter_by(notebook_id=notebook_id)

    tag = (query_params.get("tag") or "").strip()
    if tag:
        query = (
            query.join(note_tag, note_tag.c.note_id == Note.id)
            .join(Tag, Tag.id == note_tag.c.tag_id)
            .filter(Tag.name == tag)
        )

    q = (query_params.get("q") or "").strip()
    if q:
        # LIKE 参数化查询（% 由代码拼接），ORM 自动转义，SQL 注入串只是普通文本。
        # 只搜 content_md（纯文本副本），不搜 content_html，免得把 <img>/<span> 标签也匹配进来。
        like = f"%{q}%"
        query = query.filter(Note.title.like(like) | Note.content_md.like(like))

    return query.order_by(Note.is_top.desc(), Note.updated_at.desc())


# ---------------------------------------------------------------- 笔记 CRUD --

@notes_bp.get("/notes")
@login_required
def list_notes(user):
    """笔记列表；trash=1 看回收站。可按 notebook_id/tag 过滤。"""
    notes = _filter_notes_query(user.id, request.args).all()
    return jsonify([n.to_dict(with_content=False) for n in notes])


@notes_bp.get("/notes/search")
@login_required
def search_notes(user):
    """全文搜索（标题 + 正文 LIKE），可叠加 tag 过滤（5.6 契约端点）。"""
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify(error="缺少搜索关键词 q"), 400
    notes = _filter_notes_query(user.id, request.args).all()
    return jsonify([n.to_dict(with_content=False) for n in notes])


@notes_bp.post("/notes")
@login_required
def create_note(user):
    data = payload()
    title = text(data.get('title'), '标题')

    note = Note(
        user_id=user.id,
        title=title[:200],
    )
    try:
        apply_content(note, data)
        if "notebook_id" in data:
            _apply_notebook(user.id, note, data.get("notebook_id"))
        if "tags" in data:
            _set_tags(user.id, note, data.get("tags"))
    except ValueError as e:
        db.session.rollback()
        return jsonify(error=str(e)), 400

    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201


@notes_bp.get("/notes/<int:note_id>")
@login_required
def get_note(user, note_id):
    note, err = _note_or_404(user.id, note_id)
    if err:
        return err
    if note.is_deleted:
        return jsonify(error="笔记在回收站中"), 404
    return jsonify(note.to_dict())


@notes_bp.put("/notes/<int:note_id>")
@login_required
def update_note(user, note_id):
    note, err = _note_or_404(user.id, note_id)
    if err:
        return err

    if note.is_deleted:
        return jsonify(error='笔记在回收站中'), 404
    data = payload()
    if "title" in data:
        note.title = text(data['title'], '标题')
    if "is_top" in data:  # 置顶（T1.4）
        if not isinstance(data['is_top'], bool):
            raise ApiError('is_top 必须是布尔值')
        note.is_top = data['is_top']
    try:
        apply_content(note, data)
        if "notebook_id" in data:
            _apply_notebook(user.id, note, data.get("notebook_id"))
        if "tags" in data:
            _set_tags(user.id, note, data.get("tags"))
    except ValueError as e:
        db.session.rollback()
        return jsonify(error=str(e)), 400

    db.session.commit()
    return jsonify(note.to_dict())


@notes_bp.delete("/notes/<int:note_id>")
@login_required
def delete_note(user, note_id):
    """软删除 -> 回收站。"""
    note, err = _note_or_404(user.id, note_id)
    if err:
        return err
    note.is_deleted = True
    db.session.commit()
    return jsonify(message="已移入回收站")


@notes_bp.post("/notes/<int:note_id>/restore")
@login_required
def restore_note(user, note_id):
    """回收站恢复（T1.4）；不在回收站则幂等返回。"""
    note, err = _note_or_404(user.id, note_id)
    if err:
        return err
    if not note.is_deleted:
        return jsonify(message="笔记不在回收站中")
    note.is_deleted = False
    db.session.commit()
    return jsonify(note.to_dict(with_content=False))


# ---------------------------------------------------------------- 打标签（5.6 契约端点） --

@notes_bp.post("/notes/<int:note_id>/tags")
@login_required
def replace_tags(user, note_id):
    """整体替换笔记标签：{ "tags": ["算法", "期末复习"] }。"""
    note, err = _note_or_404(user.id, note_id)
    if err:
        return err
    if note.is_deleted:
        return jsonify(error='笔记在回收站中'), 404
    data = payload()
    if not isinstance(data.get("tags", []), list):
        return jsonify(error="tags 必须是字符串数组"), 400
    try:
        _set_tags(user.id, note, data.get("tags", []))
    except ValueError as e:
        db.session.rollback()
        return jsonify(error=str(e)), 400
    db.session.commit()
    return jsonify(note.to_dict(with_content=False))
