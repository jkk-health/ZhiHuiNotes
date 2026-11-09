"""记账表：type 收/支，amount 定点两位小数（Negative 由 Service 层校验拦截）。"""
from datetime import datetime

from app.extensions import db


class Bill(db.Model):
    __tablename__ = "bill"

    TYPE_INCOME = "收"
    TYPE_EXPENSE = "支"
    TYPES = (TYPE_INCOME, TYPE_EXPENSE)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type = db.Column(db.String(2), nullable=False)  # 收 / 支
    category = db.Column(db.String(50), nullable=False, default="其他")
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    bill_date = db.Column(db.Date, nullable=False, index=True)
    remark = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "category": self.category,
            "amount": float(self.amount),  # Decimal -> float 便于 JSON 序列化
            "bill_date": self.bill_date.isoformat() if self.bill_date else None,
            "remark": self.remark,
        }
