from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from core.models import (
    Delivery, MenuItem, Order, OrderItem, OrderStatus,
    Profile, Restaurant, Review,
)
from webapp.cart import Cart
from webapp.forms import AddressForm, CheckoutForm, RegisterForm, ReviewForm

DELIVERY_FEE = Decimal("40.00")


# ---------------------------------------------------------------------------
# Browsing
# ---------------------------------------------------------------------------
def home(request):
    restaurants = Restaurant.objects.filter(is_active=True)
    query = request.GET.get("q", "").strip()
    city = request.GET.get("city", "").strip()
    if query:
        restaurants = restaurants.filter(name__icontains=query) | restaurants.filter(cuisine_type__icontains=query)
    if city:
        restaurants = restaurants.filter(city__icontains=city)
    return render(request, "webapp/home.html", {
        "restaurants": restaurants.distinct(),
        "query": query,
        "city": city,
    })


def restaurant_detail(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk, is_active=True)
    categories = restaurant.categories.prefetch_related("items").all()
    uncategorized = restaurant.menu_items.filter(category__isnull=True, is_available=True)
    reviews = restaurant.reviews.select_related("customer").order_by("-created_at")[:10]
    return render(request, "webapp/restaurant_detail.html", {
        "restaurant": restaurant,
        "categories": categories,
        "uncategorized": uncategorized,
        "reviews": reviews,
    })


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------
def add_to_cart(request, item_id):
    menu_item = get_object_or_404(MenuItem, pk=item_id, is_available=True)
    cart = Cart(request)

    existing_restaurant_id = cart.restaurant_id()
    if existing_restaurant_id and existing_restaurant_id != menu_item.restaurant_id:
        messages.warning(
            request,
            "Your cart has items from another restaurant. Starting a new cart for this one."
        )
        cart.clear()

    quantity = int(request.POST.get("quantity", 1))
    cart.add(menu_item.id, quantity)
    messages.success(request, f"Added {menu_item.name} to your cart.")
    return redirect(request.META.get("HTTP_REFERER", "webapp:home"))


def update_cart_item(request, item_id):
    cart = Cart(request)
    quantity = int(request.POST.get("quantity", 0))
    cart.set_quantity(item_id, quantity)
    return redirect("webapp:cart")


def remove_from_cart(request, item_id):
    cart = Cart(request)
    cart.remove(item_id)
    return redirect("webapp:cart")


def cart_view(request):
    cart = Cart(request)
    items = cart.get_items()
    subtotal = cart.get_total()
    delivery_fee = DELIVERY_FEE if items else Decimal("0.00")
    return render(request, "webapp/cart.html", {
        "items": items,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "total": subtotal + delivery_fee,
    })


# ---------------------------------------------------------------------------
# Checkout / Orders
# ---------------------------------------------------------------------------
@login_required
def checkout(request):
    cart = Cart(request)
    items = cart.get_items()
    if not items:
        messages.info(request, "Your cart is empty.")
        return redirect("webapp:home")

    restaurant = items[0]["menu_item"].restaurant

    if request.method == "POST":
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                order = Order.objects.create(
                    customer=request.user,
                    restaurant=restaurant,
                    delivery_address=form.cleaned_data["address"],
                    payment_method=form.cleaned_data["payment_method"],
                    delivery_fee=DELIVERY_FEE,
                    special_instructions=form.cleaned_data["special_instructions"],
                )
                for item in items:
                    OrderItem.objects.create(
                        order=order,
                        menu_item=item["menu_item"],
                        quantity=item["quantity"],
                        price=item["menu_item"].price,
                    )
                order.recalculate_total()
            cart.clear()
            return redirect("webapp:order_success", order_id=order.id)
    else:
        form = CheckoutForm(user=request.user)

    if not form.fields["address"].queryset.exists():
        messages.info(request, "Add a delivery address before checking out.")
        return redirect("webapp:add_address")

    subtotal = cart.get_total()
    return render(request, "webapp/checkout.html", {
        "form": form,
        "items": items,
        "restaurant": restaurant,
        "subtotal": subtotal,
        "delivery_fee": DELIVERY_FEE,
        "total": subtotal + DELIVERY_FEE,
    })


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id, customer=request.user)
    return render(request, "webapp/order_success.html", {"order": order})


@login_required
def order_history(request):
    orders = Order.objects.filter(customer=request.user).prefetch_related("items")
    return render(request, "webapp/order_history.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id, customer=request.user)
    delivery = getattr(order, "delivery", None)
    review = getattr(order, "review", None)
    review_form = None
    if order.status == OrderStatus.DELIVERED and review is None:
        if request.method == "POST":
            review_form = ReviewForm(request.POST)
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.order = order
                review.restaurant = order.restaurant
                review.customer = request.user
                review.save()
                messages.success(request, "Thanks for your review!")
                return redirect("webapp:order_detail", order_id=order.id)
        else:
            review_form = ReviewForm()

    return render(request, "webapp/order_detail.html", {
        "order": order,
        "delivery": delivery,
        "review": review,
        "review_form": review_form,
    })


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id, customer=request.user)
    if order.status in [OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED]:
        messages.error(request, "This order can no longer be cancelled.")
    else:
        order.status = OrderStatus.CANCELLED
        order.save(update_fields=["status"])
        messages.success(request, "Order cancelled.")
    return redirect("webapp:order_detail", order_id=order.id)


# ---------------------------------------------------------------------------
# Restaurant owner: manage incoming orders
# ---------------------------------------------------------------------------
@login_required
def owner_orders(request):
    orders = Order.objects.filter(restaurant__owner=request.user).select_related(
        "customer", "restaurant"
    ).prefetch_related("items")
    return render(request, "webapp/owner_orders.html", {"orders": orders})


@login_required
def owner_update_status(request, order_id):
    order = get_object_or_404(Order, pk=order_id, restaurant__owner=request.user)
    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in OrderStatus.values:
            order.status = new_status
            order.save(update_fields=["status"])
            if new_status == OrderStatus.OUT_FOR_DELIVERY:
                Delivery.objects.get_or_create(order=order)
            messages.success(request, f"Order #{order.id} marked as {order.get_status_display()}.")
    return redirect("webapp:owner_orders")


# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------
@login_required
def add_address(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, "Address saved.")
            return redirect("webapp:checkout")
    else:
        form = AddressForm()
    return render(request, "webapp/add_address.html", {"form": form})


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user, phone_number=form.cleaned_data.get("phone_number", ""))
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account has been created.")
            return redirect("webapp:home")
    else:
        form = RegisterForm()
    return render(request, "webapp/register.html", {"form": form})
