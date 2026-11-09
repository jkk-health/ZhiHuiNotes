"""笔记本接口：分组 CRUD（T1.3）。

删除笔记本 -> 笔记保留、notebook_id 置 NULL 归入"未分组"（FK SET NULL）。
"""
from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Notebook
from app.services.auth_service import login_required

notebooks_bp = Blueprint("notebooks", __name__)


def _notebook_or_404(user_id: int, nb_id: int):
    nb = db.session.get(Notebook, nb_id)
    if nb is None or nb.user_id != user_id:
        return None, (jsonify(error="笔记本不存在"), 404)
    return nb, None


@notebooks_bp.get("/notebooks")
@login_required
def list_notebooks(user):
    """笔记本列表（带未删笔记数，供侧栏展示）。"""
    nbs = (
        Notebook.query.filter_by(user_id=user.id).order_by(Notebook.sort, Notebook.id).all()
    )
    return jsonify(
        [
            {**nb.to_dict(), "note_count": nb.notes.filter_by(is_deleted=False).count()}
            for nb in nbs
        ]
    )


@notebooks_bp.post("/notebooks")
@login_required
def create_notebook(user):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="笔记本名称不能为空"), 400
    nb = Notebook(user_id=user.id, name=name[:100], sort=data.get("sort") or 0)
    db.session.add(nb)
    db.session.commit()
    return jsonify(nb.to_dict()), 201


@notebooks_bp.put("/notebooks/<int:nb_id>")
@login_required
def rename_notebook(user, nb_id):
    nb, err = _notebook_or_404(user.id, nb_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="笔记本名称不能为空"), 400
    nb.name = name[:100]
    if "sort" in data:
        nb.sort = data.get("sort") or 0
    db.session.commit()
    return jsonify(nb.to_dict())


@notebooks_bp.delete("/notebooks/<int:nb_id>")
@login_required
def delete_notebook(user, nb_id):
    """删除笔记本：笔记不删，归入未分组（SQLite FK SET NULL 已开 PRAGMA）。"""
    nb, err = _notebook_or_404(user.id, nb_id)
    if err:
        return err
    db.session.delete(nb)
    db.session.commit()
    return jsonify(message="笔记本已删除，其笔记归入未分组")
