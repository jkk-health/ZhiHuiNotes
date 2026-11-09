from flask import Blueprint, current_app, jsonify
from app.models import Note
from app.services.api_utils import ApiError, owned, payload
from app.services.auth_service import login_required
from app.services.content_service import note_text
from app.services.ai_service import generate

ai_bp = Blueprint('ai', __name__)


def run(user, kind):
    note = owned(Note, payload().get('note_id'), user.id)
    if note.is_deleted:
        raise ApiError('笔记在回收站中', 404)
    body = note_text(note)
    if not body.strip():
        raise ApiError('笔记正文为空，请先写下内容')
    config = {name: current_app.config[name] for name in
              ('DEEPSEEK_API_KEY', 'DEEPSEEK_BASE_URL', 'DEEPSEEK_MODEL', 'AI_TIMEOUT_SECONDS')}
    return jsonify(generate(kind, body, config))


@ai_bp.post('/ai/summary')
@login_required
def summary(user):
    return run(user, 'summary')


@ai_bp.post('/ai/tags')
@login_required
def tags(user):
    return run(user, 'tags')
