"""数据模型层：导入全部模型，确保 create_all / 关系注册生效。

核心 8 张表：user / notebook / note / tag / note_tag / todo / mindmap / bill
（社区模块在本轮交付范围之外。）
"""
from app.models.user import User
from app.models.notebook import Notebook
from app.models.note import Note
from app.models.tag import Tag, note_tag
from app.models.todo import Todo
from app.models.mindmap import Mindmap
from app.models.bill import Bill

__all__ = ["User", "Notebook", "Note", "Tag", "note_tag", "Todo", "Mindmap", "Bill"]
