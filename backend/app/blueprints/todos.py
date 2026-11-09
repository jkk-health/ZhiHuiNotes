from flask import Blueprint, jsonify, request
from app.extensions import db
from app.models import Todo
from app.services.auth_service import login_required
from app.services.api_utils import ApiError, payload, text, owned, linked_note, source_note, iso_date, query_id

todos_bp = Blueprint('todos', __name__)


def serialize(todo):
    return {**todo.to_dict(), 'source_note': source_note(todo)}


def apply(todo, data, user_id, new=False):
    if new or 'title' in data:
        todo.title = text(data.get('title'), '标题')
    if 'note_id' in data:
        todo.note_id = linked_note(data['note_id'], user_id, todo.note_id)
    if 'due_date' in data:
        todo.due_date = iso_date(data['due_date'], nullable=True)
    if 'done' in data:
        if not isinstance(data['done'], bool):
            raise ApiError('done 必须是布尔值')
        todo.done = data['done']


@todos_bp.get('/todos')
@login_required
def listing(user):
    query = Todo.query.filter_by(user_id=user.id)
    if 'note_id' in request.args:
        query = query.filter_by(note_id=query_id(request.args['note_id']))
    if 'done' in request.args:
        if request.args['done'] not in {'0', '1'}:
            raise ApiError('done 筛选必须为 0 或 1')
        query = query.filter_by(done=request.args['done'] == '1')
    return jsonify([serialize(t) for t in query.order_by(Todo.done, Todo.due_date.is_(None), Todo.due_date, Todo.id.desc())])


@todos_bp.post('/todos')
@login_required
def create(user):
    todo = Todo(user_id=user.id)
    apply(todo, payload(), user.id, new=True)
    db.session.add(todo)
    db.session.commit()
    return jsonify(serialize(todo)), 201


@todos_bp.get('/todos/<int:item_id>')
@login_required
def detail(user, item_id):
    return jsonify(serialize(owned(Todo, item_id, user.id)))


@todos_bp.put('/todos/<int:item_id>')
@login_required
def update(user, item_id):
    todo = owned(Todo, item_id, user.id)
    apply(todo, payload(), user.id)
    db.session.commit()
    return jsonify(serialize(todo))


@todos_bp.delete('/todos/<int:item_id>')
@login_required
def delete(user, item_id):
    db.session.delete(owned(Todo, item_id, user.id))
    db.session.commit()
    return jsonify(message='待办已删除')
