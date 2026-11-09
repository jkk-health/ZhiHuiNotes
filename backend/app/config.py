"""应用配置：从 backend/.env 读取，缺省值保证零配置可跑。"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/

load_dotenv(BASE_DIR / ".env")


class Config:
    # SQLite 放 backend/app.db（演示可见、免部署数据库服务）
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'app.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # AI：Key 为空 => AIService 直接走本地降级引擎
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    AI_TIMEOUT_SECONDS = 8  # 架构书 5.4：超时 8s 后降级
