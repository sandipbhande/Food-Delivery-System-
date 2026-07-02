from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from core.models import (
    Address, Delivery, DeliveryAgent, MenuCategory, MenuItem,
    Order, OrderStatus, Restaurant, Review,
)
from core.permissions import IsOrderOwnerOrRestaurantOwner, IsOwnerOrReadOnly
from core.serializers import (
    AddressSerializer, DeliveryAgentSerializer, DeliverySerializer,
    MenuCategorySerializer, MenuItemSerializer, OrderSerializer,
    OrderStatusUpdateSerializer, RegisterSerializer, RestaurantSerializer,
    ReviewSerializer,
)


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ -> create a user + auth token."""
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"user": serializer.data, "token": token.key},
            status=status.HTTP_201_CREATED,
        )


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.filter(is_active=True)
    serializer_class = RestaurantSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filterset_fields = ["city", "cuisine_type"]
    search_fields = ["name", "cuisine_type", "city"]

    @action(detail=True, methods=["get"])
    def menu(self, request, pk=None):
        """GET /api/restaurants/{id}/menu/ -> categorized menu for a restaurant."""
        restaurant = self.get_object()
        categories = restaurant.categories.prefetch_related("items")
        serializer = MenuCategorySerializer(categories, many=True)
        return Response(serializer.data)


class MenuCategoryViewSet(viewsets.ModelViewSet):
    queryset = MenuCategory.objects.all()
    serializer_class = MenuCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ["restaurant"]


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.filter(is_available=True)
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filterset_fields = ["restaurant", "category", "is_vegetarian"]
    search_fields = ["name", "description"]


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrderOwnerOrRestaurantOwner]
    filterset_fields = ["status", "restaurant"]

    def get_queryset(self):
        user = self.request.user
        # A user sees orders they placed, or orders placed at restaurants they own.
        return Order.objects.filter(customer=user) | Order.objects.filter(restaurant__owner=user)

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        """PATCH /api/orders/{id}/status/ -> restaurant owner updates order status."""
        order = self.get_object()
        if order.restaurant.owner != request.user:
            return Response({"detail": "Only the restaurant owner can update order status."}, status=403)

        serializer = OrderStatusUpdateSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Auto-create a Delivery record once the order heads out for delivery.
        if order.status == OrderStatus.OUT_FOR_DELIVERY:
            Delivery.objects.get_or_create(order=order, defaults={"assigned_at": timezone.now()})
        if order.status == OrderStatus.DELIVERED and hasattr(order, "delivery"):
            order.delivery.delivered_at = timezone.now()
            order.delivery.save(update_fields=["delivered_at"])

        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """POST /api/orders/{id}/cancel/ -> customer cancels their own order."""
        order = self.get_object()
        if order.customer != request.user:
            return Response({"detail": "You can only cancel your own orders."}, status=403)
        if order.status in [OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED]:
            return Response({"detail": "Order can no longer be cancelled."}, status=400)
        order.status = OrderStatus.CANCELLED
        order.save(update_fields=["status"])
        return Response(OrderSerializer(order).data)


class DeliveryAgentViewSet(viewsets.ModelViewSet):
    queryset = DeliveryAgent.objects.all()
    serializer_class = DeliveryAgentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.select_related("order", "agent")
    serializer_class = DeliverySerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["patch"])
    def pick_up(self, request, pk=None):
        delivery = self.get_object()
        delivery.picked_up_at = timezone.now()
        delivery.save(update_fields=["picked_up_at"])
        return Response(DeliverySerializer(delivery).data)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ["restaurant"]
