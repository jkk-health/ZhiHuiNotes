"""Shared API validation; errors are handled as JSON by the app."""
from datetime import date
from flask import request
from app.extensions import db
from app.models import Note


class ApiError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError('请求体必须是 JSON 对象')
    return data


def text(value, name, maximum=200, required=True):
    if not isinstance(value, str) or (required and not value.strip()) or len(value.strip()) > maximum:
        raise ApiError(f'{name}必须是{1 if required else 0}至{maximum}个字符的字符串')
    return value.strip()


def identifier(value):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ApiError('ID 必须是正整数')
    return value


def owned(model, value, user_id):
    item = db.session.get(model, identifier(value))
    if item is None or item.user_id != user_id:
        raise ApiError('资源不存在', 404)
    return item


def linked_note(value, user_id, existing=None):
    if value is None:
        return None
    note = owned(Note, value, user_id)
    if note.is_deleted and note.id != existing:
        raise ApiError('来源笔记在回收站中')
    return note.id


def source_note(item):
    note = item.note
    if note is None or note.user_id != item.user_id:
        return None
    return {'id': note.id, 'title': note.title, 'is_deleted': note.is_deleted}


def iso_date(value, nullable=False):
    if value is None and nullable:
        return None
    try:
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError()
        result = date.fromisoformat(value)
        if result.isoformat() != value:
            raise ValueError()
        return result
    except ValueError:
        raise ApiError('日期格式必须为 YYYY-MM-DD')


def query_id(value):
    try:
        return identifier(int(value))
    except (ValueError, TypeError):
        raise ApiError('ID 必须是正整数')
