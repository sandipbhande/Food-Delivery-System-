from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from core.models import (
    Address, Delivery, DeliveryAgent, MenuCategory, MenuItem,
    Order, OrderItem, Profile, Restaurant, Review,
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=Profile._meta.get_field("role").choices, default="customer")
    phone_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "role", "phone_number"]

    def create(self, validated_data):
        role = validated_data.pop("role", "customer")
        phone_number = validated_data.pop("phone_number", "")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        Profile.objects.create(user=user, role=role, phone_number=phone_number)
        return user


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"
        read_only_fields = ["user"]


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = [
            "id", "restaurant", "category", "name", "description",
            "price", "image", "is_vegetarian", "is_available",
        ]


class MenuCategorySerializer(serializers.ModelSerializer):
    items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = MenuCategory
        fields = ["id", "restaurant", "name", "display_order", "items"]


class RestaurantSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)

    class Meta:
        model = Restaurant
        fields = [
            "id", "owner", "name", "description", "cuisine_type", "address",
            "city", "phone_number", "logo", "is_active", "opening_time",
            "closing_time", "average_rating", "created_at",
        ]
        read_only_fields = ["average_rating"]

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)


class OrderItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["menu_item", "quantity"]


class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source="menu_item.name", read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "menu_item", "menu_item_name", "quantity", "price", "subtotal"]
        read_only_fields = ["price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    order_items = OrderItemWriteSerializer(many=True, write_only=True)
    customer = UserSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_id", "customer", "restaurant", "delivery_address",
            "status", "payment_method", "is_paid", "subtotal", "delivery_fee",
            "total_amount", "special_instructions", "items", "order_items",
            "created_at", "updated_at",
        ]
        read_only_fields = ["subtotal", "total_amount", "status", "is_paid"]

    def validate_order_items(self, value):
        if not value:
            raise serializers.ValidationError("An order must contain at least one item.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        order_items_data = validated_data.pop("order_items")
        validated_data["customer"] = self.context["request"].user
        order = Order.objects.create(**validated_data)

        for item_data in order_items_data:
            menu_item = item_data["menu_item"]
            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=item_data["quantity"],
                price=menu_item.price,  # snapshot current price
            )
        order.recalculate_total()
        return order


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["status"]


class DeliveryAgentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = DeliveryAgent
        fields = [
            "id", "user", "vehicle_number", "is_available",
            "current_latitude", "current_longitude",
        ]


class DeliverySerializer(serializers.ModelSerializer):
    agent = DeliveryAgentSerializer(read_only=True)
    agent_id = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryAgent.objects.all(), source="agent", write_only=True, required=False
    )

    class Meta:
        model = Delivery
        fields = [
            "id", "order", "agent", "agent_id",
            "assigned_at", "picked_up_at", "delivered_at",
        ]


class ReviewSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ["id", "order", "restaurant", "customer", "rating", "comment", "created_at"]

    def create(self, validated_data):
        validated_data["customer"] = self.context["request"].user
        return super().create(validated_data)
