"""Flask 扩展单例（避免循环导入）。"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
