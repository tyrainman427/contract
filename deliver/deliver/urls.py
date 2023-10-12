from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from customer.views import *
from django.contrib.auth.views import LoginView, LogoutView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', include('dashboard.urls')),
    path('', Index.as_view(), name="index"),
    path('about/', About.as_view(), name="about"),
    path('order/', Order.as_view(), name="order"),
    path('order-confirmation/<int:pk>/', OrderConfirmation.as_view(), name="order-confirmation"),
    path('payment-confirmation/<int:order_id>/', OrderPayConfirmation.as_view(), name='payment_confirmation'),
    path('menu/', Menu.as_view(), name='menu'),
    path('menu/search/', MenuSearch.as_view(), name="menu-search"),
    # New URLs
    path('register/', register, name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('cart/', Cart.as_view(), name='cart'),
    path('add_to_cart/', AddToCart.as_view(), name='add_to_cart'),
    path('remove-from-cart/', RemoveFromCartView.as_view(), name='remove_from_cart'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    # User Dashboard URLSs
    path('user_dashboard/', user_dashboard_view, name='user_dashboard'),
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('order/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('order/<int:pk>/edit/', OrderUpdateView.as_view(), name='order_edit'),
    path('order/<int:pk>/pay/', order_pay_view, name='order_pay'),
    path('order/<int:pk>/add_services/', order_add_services_view, name='order_add_services'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('update_quantity/', update_quantity, name='update_quantity'),




] + static(settings.STATIC_URL, document_root=settings.MEDIA_ROOT)