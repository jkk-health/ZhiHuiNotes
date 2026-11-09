import json
from flask import Blueprint, jsonify, request
from app.extensions import db
from app.models import Mindmap, Note
from app.services.auth_service import login_required
from app.services.api_utils import ApiError, payload, text, owned, linked_note, source_note, query_id
from app.services.mindmap_service import generate, encode

mindmaps_bp = Blueprint('mindmaps', __name__)


def serialize(item, content=True):
    result = item.to_dict()
    result['source_note'] = source_note(item)
    if content:
        result['map_json'] = json.loads(item.map_json)
    else:
        result.pop('map_json')
    return result


@mindmaps_bp.get('/mindmaps')
@login_required
def listing(user):
    query = Mindmap.query.filter_by(user_id=user.id)
    if 'note_id' in request.args:
        query = query.filter_by(note_id=query_id(request.args['note_id']))
    return jsonify([serialize(m, False) for m in query.order_by(Mindmap.updated_at.desc(), Mindmap.id.desc())])


@mindmaps_bp.post('/mindmaps')
@login_required
def create(user):
    data = payload()
    item = Mindmap(user_id=user.id, title=text(data.get('title'), '标题'),
                   note_id=linked_note(data.get('note_id'), user.id), map_json=encode(data.get('map_json')))
    db.session.add(item)
    db.session.commit()
    return jsonify(serialize(item)), 201


@mindmaps_bp.get('/mindmaps/<int:item_id>')
@login_required
def detail(user, item_id):
    return jsonify(serialize(owned(Mindmap, item_id, user.id)))


@mindmaps_bp.put('/mindmaps/<int:item_id>')
@login_required
def update(user, item_id):
    item, data = owned(Mindmap, item_id, user.id), payload()
    if 'title' in data:
        item.title = text(data['title'], '标题')
    if 'note_id' in data:
        item.note_id = linked_note(data['note_id'], user.id, item.note_id)
    if 'map_json' in data:
        item.map_json = encode(data['map_json'])
    db.session.commit()
    return jsonify(serialize(item))


@mindmaps_bp.delete('/mindmaps/<int:item_id>')
@login_required
def delete(user, item_id):
    db.session.delete(owned(Mindmap, item_id, user.id))
    db.session.commit()
    return jsonify(message='导图已删除')


@mindmaps_bp.post('/notes/<int:note_id>/to-mindmap')
@login_required
def from_note(user, note_id):
    note = owned(Note, note_id, user.id)
    if note.is_deleted:
        raise ApiError('笔记在回收站中', 404)
    value = generate(note)
    # Preview is read-only; generation without preview always creates a new map.
    if request.args.get('preview') == '1':
        return jsonify(map_json=value, title=note.title)
    item = Mindmap(user_id=user.id, note_id=note.id, title=note.title, map_json=encode(value))
    db.session.add(item)
    db.session.commit()
    return jsonify(serialize(item)), 201
