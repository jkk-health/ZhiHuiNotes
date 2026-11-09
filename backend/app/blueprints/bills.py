import calendar
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from flask import Blueprint, jsonify, request
from app.extensions import db
from app.models import Bill
from app.services.auth_service import login_required
from app.services.api_utils import ApiError, payload, text, owned, iso_date

bills_bp = Blueprint('bills', __name__)


def month_range(value):
    try:
        if not isinstance(value, str) or len(value) != 7:
            raise ValueError()
        first = date.fromisoformat(value + '-01')
        days = calendar.monthrange(first.year, first.month)[1]
        return first, first + timedelta(days=days), days
    except (ValueError, OverflowError):
        raise ApiError('月份格式必须为 YYYY-MM')


def apply(item, data, new=False):
    for field in ('type', 'amount', 'bill_date'):
        if new and field not in data:
            raise ApiError(f'缺少 {field}')
    if 'type' in data:
        if data['type'] not in Bill.TYPES:
            raise ApiError('type 必须为 收 或 支')
        item.type = data['type']
    if 'amount' in data:
        try:
            value = data['amount']
            if isinstance(value, bool) or not isinstance(value, (int, float, str)):
                raise ValueError()
            amount = Decimal(str(value))
            if not amount.is_finite() or amount <= 0 or amount > Decimal('99999999.99') or amount != amount.quantize(Decimal('.01')):
                raise ValueError()
            item.amount = amount
        except (ValueError, InvalidOperation):
            raise ApiError('金额必须为正数、最多两位小数且不超过 99999999.99')
    if 'bill_date' in data:
        item.bill_date = iso_date(data['bill_date'])
    if new or 'category' in data:
        item.category = text(data.get('category', '其他'), '分类', 50)
    if new or 'remark' in data:
        item.remark = text(data.get('remark', ''), '备注', 200, False)


@bills_bp.get('/bills')
@login_required
def listing(user):
    query = Bill.query.filter_by(user_id=user.id)
    if 'month' in request.args:
        first, end, _ = month_range(request.args['month'])
        query = query.filter(Bill.bill_date >= first, Bill.bill_date < end)
    return jsonify([b.to_dict() for b in query.order_by(Bill.bill_date.desc(), Bill.id.desc())])


@bills_bp.get('/bills/monthly')
@login_required
def monthly(user):
    month = request.args.get('month')
    first, end, days = month_range(month)
    bills = Bill.query.filter(Bill.user_id == user.id, Bill.bill_date >= first, Bill.bill_date < end).all()
    daily = [{'date': (first + timedelta(days=i)).isoformat(), 'income': Decimal(0), 'expense': Decimal(0)} for i in range(days)]
    income, expense, categories = Decimal(0), Decimal(0), {}
    for bill in bills:
        key = 'income' if bill.type == Bill.TYPE_INCOME else 'expense'
        daily[(bill.bill_date - first).days][key] += bill.amount
        if key == 'income':
            income += bill.amount
        else:
            expense += bill.amount
            categories[bill.category] = categories.get(bill.category, Decimal(0)) + bill.amount
    for row in daily:
        row['income'], row['expense'] = float(row['income']), float(row['expense'])
    return jsonify(month=month, income=float(income), expense=float(expense), balance=float(income - expense),
                   daily=daily, categories=[{'name': k, 'value': float(v)} for k, v in sorted(categories.items())])


@bills_bp.post('/bills')
@login_required
def create(user):
    item = Bill(user_id=user.id)
    apply(item, payload(), True)
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@bills_bp.get('/bills/<int:item_id>')
@login_required
def detail(user, item_id):
    return jsonify(owned(Bill, item_id, user.id).to_dict())


@bills_bp.put('/bills/<int:item_id>')
@login_required
def update(user, item_id):
    item = owned(Bill, item_id, user.id)
    apply(item, payload())
    db.session.commit()
    return jsonify(item.to_dict())


@bills_bp.delete('/bills/<int:item_id>')
@login_required
def delete(user, item_id):
    db.session.delete(owned(Bill, item_id, user.id))
    db.session.commit()
    return jsonify(message='记录已删除')
