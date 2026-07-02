from django.contrib.auth import views as auth_views
from django.urls import path

from webapp import views

app_name = "webapp"

urlpatterns = [
    path("", views.home, name="home"),
    path("restaurants/<int:pk>/", views.restaurant_detail, name="restaurant_detail"),

    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:item_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:item_id>/", views.update_cart_item, name="update_cart_item"),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),

    path("checkout/", views.checkout, name="checkout"),
    path("orders/<int:order_id>/success/", views.order_success, name="order_success"),
    path("orders/", views.order_history, name="order_history"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/cancel/", views.cancel_order, name="cancel_order"),

    path("owner/orders/", views.owner_orders, name="owner_orders"),
    path("owner/orders/<int:order_id>/status/", views.owner_update_status, name="owner_update_status"),

    path("addresses/add/", views.add_address, name="add_address"),

    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="webapp/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="webapp:home"), name="logout"),
]
