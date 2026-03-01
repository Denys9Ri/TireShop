from django import template
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta
from store.models import Order, OrderItem

register = template.Library()

@register.simple_tag
def get_admin_stats():
    today = timezone.now()
    # Початок поточного місяця
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Замовлення за місяць (крім скасованих)
    month_orders = Order.objects.filter(created_at__gte=start_of_month).exclude(status='canceled')
    month_orders_count = month_orders.count()
    
    # 2. Нові замовлення (Червоний статус)
    new_orders_count = Order.objects.filter(status='new').count()
    
    # 3. Фінанси за місяць (Виручка і Собівартість)
    month_items = OrderItem.objects.filter(order__in=month_orders)
    
    revenue = month_items.aggregate(
        total=Sum(F('quantity') * F('price_at_purchase'))
    )['total'] or 0
    
    cost = month_items.aggregate(
        total_cost=Sum(F('quantity') * F('product__cost_price'))
    )['total_cost'] or 0
    
    profit = revenue - cost
    
    # 4. Дані для графіка (Останні 7 днів)
    chart_labels = []
    chart_data = []
    
    for i in range(6, -1, -1):  # Від 6 днів тому до сьогодні
        day = today - timedelta(days=i)
        day_orders = Order.objects.filter(created_at__date=day.date()).exclude(status='canceled')
        day_revenue = OrderItem.objects.filter(order__in=day_orders).aggregate(
            total=Sum(F('quantity') * F('price_at_purchase'))
        )['total'] or 0
        
        chart_labels.append(day.strftime('%d.%m'))
        chart_data.append(float(day_revenue))

    # 5. Останні 5 замовлень (для швидкого доступу)
    recent_orders = Order.objects.all().order_by('-created_at')[:5]

    return {
        'month_orders': month_orders_count,
        'new_orders': new_orders_count,
        'revenue': revenue,
        'profit': profit,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'recent_orders': recent_orders
    }
