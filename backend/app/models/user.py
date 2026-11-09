"""用户表：密码加盐哈希（PBKDF2-SHA256，10 万轮迭代）。"""
import hashlib
import secrets

from datetime import datetime

from app.extensions import db

# PBKDF2 参数（答辩讲解点：预计算彩虹表被盐击溃，迭代次数拖慢暴力破解）
PBKDF2_ITERATIONS = 100_000


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    pwd_hash = db.Column(db.String(128), nullable=False)  # 64 hex 字符
    salt = db.Column(db.String(32), nullable=False)  # 16 字节随机盐（hex）
    created_at = db.Column(db.DateTime, default=datetime.now)

    notes = db.relationship("Note", backref="user", lazy="dynamic")
    notebooks = db.relationship("Notebook", backref="user", lazy="dynamic")

    # ---- 密码哈希（模型自带，Service 层不重复实现）----

    def set_password(self, raw_password: str) -> None:
        """生成随机盐并计算 PBKDF2 哈希。"""
        self.salt = secrets.token_hex(16)
        self.pwd_hash = hashlib.pbkdf2_hmac(
            "sha256",
            raw_password.encode("utf-8"),
            bytes.fromhex(self.salt),
            PBKDF2_ITERATIONS,
        ).hex()

    def check_password(self, raw_password: str) -> bool:
        """用恒定时间比较防时序攻击。"""
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            raw_password.encode("utf-8"),
            bytes.fromhex(self.salt),
            PBKDF2_ITERATIONS,
        ).hex()
        return secrets.compare_digest(candidate, self.pwd_hash)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
