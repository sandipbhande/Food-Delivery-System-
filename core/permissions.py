from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Only the restaurant owner can edit/delete their own restaurant / menu items."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = getattr(obj, "owner", None) or getattr(getattr(obj, "restaurant", None), "owner", None)
        return owner == request.user


class IsOrderOwnerOrRestaurantOwner(permissions.BasePermission):
    """Customers can view/manage their own orders; restaurant owners can view/manage orders placed at their restaurant."""

    def has_object_permission(self, request, view, obj):
        return obj.customer == request.user or obj.restaurant.owner == request.user
