import json
from django.shortcuts import render, redirect,get_object_or_404
from django.views import View
from django.db.models import Q
from .models import *
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings
from django.urls import reverse, reverse_lazy
from datetime import datetime
from django.http import Http404, HttpResponseRedirect
import stripe
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib.auth import login, authenticate
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django import forms
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth import get_user_model
from django.views.generic import DetailView, UpdateView, ListView
from django.db import transaction
from django.urls import reverse
import logging
from collections import defaultdict
from django.db.models import Sum



# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

User = get_user_model()


class OrderForm(forms.ModelForm):
    class Meta:
        model = OrderModel
        fields = [
            'client_full_name',
            'cell_number', 'date_of_event', 'event_type', 'number_of_guests', 
            'start_time', 'end_time', 'location_of_event', 
            'email','street_address', 'city', 'state', 'zip_code'
        ]

def register(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Explicitly specify the backend to use
            backend = authenticate(
                username=form.cleaned_data['username'], 
                password=form.cleaned_data['password1']
            )
            
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')  # Adjust this to your backend

            return redirect('user_dashboard')  # Redirect to a home page or some other page
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('user_dashboard')  # Redirect to a home page or some other page
    else:
        form = CustomAuthenticationForm()
    return render(request, 'login.html', {'form': form})

class Index(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('user_dashboard')
        else:
            return render(request, 'customer/index.html')

class About(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'customer/about.html')

class Order(View):
    def get(self, request, *args, **kwargs):
       # Check if an unpaid order exists for the user
        existing_unpaid_order = OrderModel.objects.filter(user=request.user, is_paid=False).first()
        
        if existing_unpaid_order:
            # Redirect to the order details page for the existing unpaid order
            return redirect(reverse('order-detail', args=[existing_unpaid_order.id]))


        # Retrieve menu items from each category
        visuals = MenuItem.objects.filter(category__name__contains='Visuals')
        time = MenuItem.objects.filter(category__name__contains='Time')
        photo = MenuItem.objects.filter(category__name__contains='Photo')
        lights = MenuItem.objects.filter(category__name__contains='Lights')
        type_of_payments = OrderModel.objects.all()
        menu_items = MenuItem.objects.all()
        
        cart_items = CartItem.objects.filter(user=request.user)
        order, created = OrderModel.objects.get_or_create(user=request.user, is_paid=False)
        
        # Associate items with the order
        order.items.set([item.menu_item for item in cart_items])

        form = OrderForm(initial={
            'client_full_name': request.user.first_name + ' ' + request.user.last_name,
            'email': request.user.email,
        })
        
        context = {
            'visuals': visuals,
            'time': time,
            'photo': photo,
            'lights': lights,
            'type_of_payments': type_of_payments,
            'form':form,
            'menu_items': menu_items,
        }
        
        return render(request, 'customer/order.html', context)

    def post(self, request, *args, **kwargs):
        # Check if an unpaid order exists for the user
        existing_unpaid_order = OrderModel.objects.filter(user=request.user, is_paid=False).first()
        
        if existing_unpaid_order:
            # Redirect to payment page for the existing unpaid order, or show a message
            return redirect(reverse('order-detail', args=[existing_unpaid_order.id]))

        try:
            form = OrderForm(request.POST)
            if form.is_valid():
                # This will create a new OrderModel instance and populate it
                # with the data from the form
                order, created = OrderModel.objects.get_or_create(
                    user=request.user,
                    is_paid=False,
                    defaults=form.cleaned_data  # use form.cleaned_data to populate the fields
                )
                
                # If an existing order is found, update its details
                if not created:
                    for field, value in form.cleaned_data.items():
                        setattr(order, field, value)
                    order.save()
                
                items = request.POST.getlist('items[]')
                
                for item_id in items:
                    menu_item = MenuItem.objects.get(pk=item_id)
                    order.items.add(menu_item)  # Assuming 'items' is a ManyToMany field in OrderModel

                return HttpResponseRedirect(reverse('user_dashboard'))
            else:
                print(form.errors)  # Debugging: print errors to the console
                return JsonResponse({"status": "error", "message": "Invalid form data"})
            
        except Exception as e:
            print(f"An error occurred: {e}")  # Debugging: print exceptions to the console
            return JsonResponse({"status": "error", "message": str(e)})
        
class OrderConfirmation(LoginRequiredMixin, View):
    def get(self, request, order_id, *args, **kwargs):
        order = OrderModel.objects.get(pk=order_id)
        total_price = order.items.aggregate(total_price=Sum('price'))['total_price']
        # Assuming you have a ForeignKey relationship between OrderModel and OrderItem
        
        is_paid = order.is_paid

        # Send email to customer if the order is paid
        if is_paid:
            email_to_customer_body = "Thank you for your payment! Your order has been confirmed."
            send_mail(
                'Order Confirmation',
                email_to_customer_body,
                settings.DEFAULT_FROM_EMAIL,
                [order.email],
                fail_silently=False
            )

            # Send email to admin
            email_to_admin_body = f"Payment received for order {order.pk}."
            send_mail(
                'Payment Received',
                email_to_admin_body,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],  # Replace with the admin's email address
                fail_silently=False
            )

        context = {
            'order': order,
            'is_paid': is_paid,
        }

        return render(request, 'customer/order_confirmation.html', context)

class OrderPayConfirmation(View):
    def get(self, request, *args, **kwargs):
        try:
            # Retrieve the order using any relevant identifier (e.g., order ID)
            order_id = kwargs['order_id']
            order = OrderModel.objects.get(id=order_id)
            
            # Fetch items associated with this order
            order_items = order
            print("Orders----:",order_id)

            # Calculate total_price
            total_price = sum(item.price for item in order.items.all())

            # Mark the order as paid
            order.is_paid = True
            order.payment_account = "right2ya@business.example.com"
            order.save()

            # Render the order confirmation template with the updated order
            context = {
                'order': order,
                'is_paid': True,
                'total_price': total_price,
               'order_items': order_items,
            }
            return render(request, 'customer/order_confirmation.html', context)

        except OrderModel.DoesNotExist:
            # Handle order not found
            messages.error(request, 'Order not found.')

        # Redirect to the order confirmation page with the original order
        # Render the order confirmation template with the updated order
        context = {
            'order': order,
            'is_paid': True,  # or False depending on your logic
            'total_price': total_price,  # Include the total price in the context
            'order_items': order_items,
        }
        return render(request, 'customer/order_confirmation.html', context)

class Contact(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'customer/contact.html')

class Menu(View):
    def get(self, request, *args, **kwargs):
        menu_items = MenuItem.objects.all()

        context = {
            'menu_items': menu_items,
        }

        return render(request, 'customer/menu.html', context)

class MenuSearch(View):
    def post(self, request, *args, **kwargs):
        search_query = request.POST.get('search_query')

        menu_items = MenuItem.objects.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

        context = {
            'menu_items': menu_items,
            'search_query': search_query
        }

        return render(request, 'customer/menu_search.html', context)

class AddToCart(View):
    def post(self, request, *args, **kwargs):
        print(f"Entire POST payload: {request.POST}")

        try:
            print("Inside AddToCart post method.")
            
            item_id = request.POST.get('item_id')

            print(f"Item ID received: {item_id}")
            
            menu_item = get_object_or_404(MenuItem, id=item_id)
            print(f"Menu item retrieved: {menu_item}")
            
            user = request.user
            print(f"Current user: {user}")
            
            if user.is_anonymous:
                print("User is anonymous. Exiting.")
                return JsonResponse({"status": "User must be logged in"})
            
            with transaction.atomic():  # Ensuring atomicity for the following operations
                print("Inside atomic block.")
                
                order, created = OrderModel.objects.get_or_create(user=user,is_paid=False)
                print(f"Order retrieved or created: {order}, Created: {created}")
                
                cart_item, created = CartItem.objects.get_or_create(
                    user=user, menu_item=menu_item, order=order, defaults={'quantity': 1})
                print(f"Cart item retrieved or created: {cart_item}, Created: {created}")
                
                # Check if the item has a maximum allowable quantity
                max_quantity = menu_item.max_quantity

                # Existing cart item
                if not created and max_quantity is not None:
                    new_quantity = cart_item.quantity + 1

                    if new_quantity > max_quantity:
                        return JsonResponse({"status": "error", "message": "Maximum quantity reached"})
                    
                    cart_item.quantity = new_quantity
                    cart_item.save()
                
                # New cart item
                elif created and max_quantity is not None:
                    if 1 > max_quantity:
                        return JsonResponse({"status": "error", "message": "Maximum quantity reached"})
                    
                # Assuming the item has been successfully added to the cart at this point
                # messages.success(request, 'Item successfully added to cart!')
                
                total_price = sum(item.menu_item.price * item.quantity for item in order.cartitem_set.all())
                print(f"Total price calculated: {total_price}")
                order.total_price = total_price
                order.save()
                print("Order price updated.")
                
            # Inside AddToCart class-based view
            is_cart_empty = (order.cartitem_set.count() == 0)
            total_price = sum(item.menu_item.price * item.quantity for item in order.cartitem_set.all())
            return JsonResponse({"status": "success", "message": "Item successfully added to cart!"})
        
        except Exception as e:
            print(f"An exception occurred: {e}")
            return JsonResponse({"status": f"An error occurred: {str(e)}"})

class RemoveFromCartView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        cart_item_id = request.POST.get('cart_item_id')
        CartItem.objects.get(id=cart_item_id).delete()
        return redirect('cart')

class CheckoutView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        cart_items = CartItem.objects.filter(user=request.user)
        total_price = sum(item.menu_item.price * item.quantity for item in cart_items)
        stripe_publishable_key = settings.STRIPE_PUBLISHABLE_KEY
        
        context = {
            'cart_items': cart_items,
            'total_price': total_price,
            'stripe_publishable_key':stripe_publishable_key,
        }
        
        return render(request, 'customer/checkout.html', context)

    def post(self, request, *args, **kwargs):
        token = request.POST.get('stripeToken')
        cart_items = CartItem.objects.filter(user=request.user)
        order = OrderModel.objects.get(user=request.user, is_paid=False)
        
        # Extract the associated MenuItem objects from cart_items
        menu_items = [cart_item.menu_item for cart_item in cart_items]

        # Add them to the order
        order.items.add(*menu_items)

        # Save the order
        order.save()
        
        total_price = sum(item.menu_item.price * item.quantity for item in cart_items)
        
        with transaction.atomic():  # Ensures database consistency
            total_price = sum(item.menu_item.price * item.quantity for item in cart_items)
            total_price_cents = int(total_price * 100)
            
            customer_email = request.user.email  # Assuming the email is stored in user model
            customer_name = request.user.username 

            # Create a Stripe charge
            try:
                charge = stripe.Charge.create(
                    amount=total_price_cents,
                    currency="usd",
                    source=token,
                    description=f"Charge for {request.user.email}",
                    metadata={
                        "customer_email": customer_email,
                        "customer_name": customer_name,
                    }
                    
                )

                # Update the order to mark it as paid
                order.is_paid = True
                order.save()

                # Clear the cart
                CartItem.objects.filter(user=request.user).delete()

                return redirect(reverse('payment_confirmation', args=[order.id]))

            except stripe.error.CardError as e:
                messages.error(request, "Your card has been declined.")
        
class Cart(View):
    def get(self, request, *args, **kwargs):
        cart_items = CartItem.objects.filter(user=request.user)
        total_price = sum(item.menu_item.price * item.quantity for item in cart_items)

        context = {'cart_items': cart_items,
                   'total_price': total_price}
        return render(request, 'customer/cart.html', context)

@login_required
def user_dashboard_view(request):
    current_user = request.user
    user_orders = OrderModel.objects.filter(user=current_user.id)  # Filter by user id
    context = {
        'user_orders': user_orders,
    }
    return render(request, 'customer/user_dashboard.html', context)


@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard_view(request):
    # your logic here
    return render(request, 'customer/admin_dashboard.html')


@method_decorator(login_required, name='dispatch')
class OrderListView(ListView):
    model = OrderModel
    template_name = 'customer/order_list.html'
    context_object_name = 'orders'

    def get_queryset(self):
        return OrderModel.objects.filter(user=self.request.user)


@method_decorator(login_required, name='dispatch')
class OrderDetailView(DetailView):
    model = OrderModel
    template_name = 'customer/order_detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_paid'] = self.object.is_paid
        context['menu_items'] = MenuItem.objects.all()

        order = self.object  # This view's object is already the order you want

        if order:  # Check if an order exists
            total_price = sum(item.menu_item.price * item.quantity for item in order.cartitem_set.all())
            cart_items = CartItem.objects.filter(user=self.request.user, order=order)
            
            context['total_cost'] = total_price
            context['cart_items'] = cart_items
        else:
            context['total_cost'] = 0
            context['cart_items'] = []

        cart_quantities = defaultdict(int)
        for cart_item in context['cart_items']:
            cart_quantities[cart_item.menu_item.id] += cart_item.quantity

        context['cart_quantities'] = cart_quantities

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        menuItem_id = request.POST.get('menuItem_id')

        try:
            menu_item = MenuItem.objects.get(id=menuItem_id)
            self.object.items.add(menu_item)
            self.object.save()
            messages.success(request, 'Item successfully added.')
            status = 'success'
        except MenuItem.DoesNotExist:
            messages.error(request, 'MenuItem does not exist.')
            status = 'error'
        except Exception as e:
            messages.error(request, f'An unexpected error occurred: {e}')
            status = 'error'

        if request.is_ajax():
            return JsonResponse({'status': status})

        return redirect('order-detail', pk=self.object.pk)


def update_quantity(request):
    if request.method == 'POST':
        cart_item_id = request.POST.get('cart_item_id')
        quantity = int(request.POST.get('quantity'))

        # Find the cart item and update its quantity
        cart_item = CartItem.objects.get(id=cart_item_id)
        cart_item.quantity = quantity
        cart_item.save()
        
    messages.add_message(request, messages.SUCCESS, 'Quantity updated.')

    return redirect('cart')  # Redirect back to the cart page

@method_decorator(login_required, name='dispatch')
class OrderUpdateView(UpdateView):
    model = OrderModel
    fields = [
            'client_full_name', 'street_address', 
            'cell_number', 'date_of_event', 'event_type', 'number_of_guests', 
            'start_time', 'end_time', 'location_of_event', 
            'email', 'city', 'state', 'zip_code'
        ]  # Fields that you want to be editable
    template_name = 'customer/order_edit.html'
    success_url = reverse_lazy('user_dashboard')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)
    

@login_required
def order_pay_view(request, pk):
    # Implement your logic for payment here
    # You could, for example, redirect to a payment gateway page
    return redirect(reverse('payment_confirmation', args=[pk]))

@login_required
def order_add_services_view(request, pk):
    # Implement logic to add services to the order
    # You could use AJAX here to send data without page reload
    if request.method == 'POST':
        # Extract data from POST request and add services
        # Return a JsonResponse if you're using AJAX
        return JsonResponse({'status': 'success'})

    return render(request, 'customer/add_services.html', {'order_id': pk})

