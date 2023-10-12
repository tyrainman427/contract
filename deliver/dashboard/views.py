from django.shortcuts import render
from django.views import View
from customer.models import OrderModel
from django.utils.timezone import datetime
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

@method_decorator(login_required, name='dispatch')
class Dashboard(View):
    def get(self, request, *args, **kwargs):
        # get the current date
        today = datetime.today()
        orders = OrderModel.objects.all(
            # created_on__year=today.year,
            # created_on__month=today.month,
            # created_on__day=today.day
        )

        # loop through the orders and calculate the total revenue
        unshipped_orders = []
        total_revenue = 0
        for order in orders:
            if order.is_completed:
                continue  # Skip shipped orders

            if order.is_paid:
                # Calculate total revenue by summing the prices of items in the paid order
                total_price = order.items.aggregate(total_price=Sum('price'))['total_price'] or 0

                # Apply service fee of $1
                # total_price += Decimal('1.00')

                # Calculate delivery fee of 2.9% + $0.30
                # delivery_fee = (total_price * Decimal('0.029')) + Decimal('0.30')

                # Add delivery fee to total price
                # total_price += delivery_fee

                total_revenue += total_price
            else:
                # Add the unpaid order to the unshipped_orders list
                unshipped_orders.append(order)

        # pass total numbers of orders and total revenue into the template
        context = {
            'orders': orders,
            'total_revenue': total_revenue,
            'total_orders': len(orders)
        }

        return render(request, 'dashboard/dashboard.html', context)

    def test_func(self):
        return self.request.user.groups.filter(name='Staff').exists()


class OrderDetails(View):
    def get(self, request, pk, *args, **kwargs):
        order = OrderModel.objects.get(pk=pk)
        context = {
            'order': order
        }
        return render(request, 'dashboard/order-details.html', context)

    def post(self, request, pk, *args, **kwargs):
        order = OrderModel.objects.get(pk=pk)
        # order.is_shipped = True
        order.save()

        context = {
            'order': order
        }

        return render(request, 'dashboard/order-details.html', context)

    def test_func(self):
        return self.request.user.groups.filter(name='Staff').exists()
