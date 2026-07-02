from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from core.views import (
    AddressViewSet, DeliveryAgentViewSet, DeliveryViewSet, MenuCategoryViewSet,
    MenuItemViewSet, OrderViewSet, RegisterView, RestaurantViewSet, ReviewViewSet,
)

router = DefaultRouter()
router.register("addresses", AddressViewSet, basename="address")
router.register("restaurants", RestaurantViewSet, basename="restaurant")
router.register("menu-categories", MenuCategoryViewSet, basename="menucategory")
router.register("menu-items", MenuItemViewSet, basename="menuitem")
router.register("orders", OrderViewSet, basename="order")
router.register("delivery-agents", DeliveryAgentViewSet, basename="deliveryagent")
router.register("deliveries", DeliveryViewSet, basename="delivery")
router.register("reviews", ReviewViewSet, basename="review")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", obtain_auth_token, name="login"),  # POST username/password -> token
    path("", include(router.urls)),
    
]
