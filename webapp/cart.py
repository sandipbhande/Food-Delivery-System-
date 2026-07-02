from decimal import Decimal

from core.models import MenuItem

CART_SESSION_KEY = "cart"


class Cart:
    """A simple session-backed shopping cart: {menu_item_id: quantity}."""

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_KEY)
        if cart is None:
            cart = self.session[CART_SESSION_KEY] = {}
        self.cart = cart

    def add(self, menu_item_id, quantity=1):
        key = str(menu_item_id)
        self.cart[key] = self.cart.get(key, 0) + quantity
        self.save()

    def set_quantity(self, menu_item_id, quantity):
        key = str(menu_item_id)
        if quantity <= 0:
            self.cart.pop(key, None)
        else:
            self.cart[key] = quantity
        self.save()

    def remove(self, menu_item_id):
        self.cart.pop(str(menu_item_id), None)
        self.save()

    def clear(self):
        self.session[CART_SESSION_KEY] = {}
        self.save()

    def save(self):
        self.session[CART_SESSION_KEY] = self.cart
        self.session.modified = True

    def __len__(self):
        return sum(self.cart.values())

    def restaurant_id(self):
        """All cart items must belong to the same restaurant; returns its id or None."""
        items = self.get_items()
        if not items:
            return None
        return items[0]["menu_item"].restaurant_id

    def get_items(self):
        ids = [int(k) for k in self.cart.keys()]
        menu_items = MenuItem.objects.select_related("restaurant").filter(id__in=ids)
        lookup = {m.id: m for m in menu_items}
        items = []
        for key, qty in self.cart.items():
            menu_item = lookup.get(int(key))
            if not menu_item:
                continue
            items.append({
                "menu_item": menu_item,
                "quantity": qty,
                "subtotal": menu_item.price * qty,
            })
        return items

    def get_total(self):
        return sum((item["subtotal"] for item in self.get_items()), Decimal("0.00"))
