from django.urls import path
from . import views


urlpatterns = [
    # Home and Menu
    path('', views.index, name='index'),
    path('menu/', views.menu, name='menu'),
    path('search/', views.search_food, name='search'),

    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Cart
    path('add-to-cart/<int:food_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart'),
    path('update-cart/', views.update_cart, name='update_cart'),
    path('get-cart-count/', views.get_cart_count, name='get_cart_count'),

    # Orders
    path('checkout/', views.checkout_view, name='checkout'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order-detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
]