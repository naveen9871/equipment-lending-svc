from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Only allow admin users"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsAdminOrStaff(permissions.BasePermission):
    """Allow both admin and staff users"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'staff']


class IsOwnerOrStaff(permissions.BasePermission):
    """Allow object owner or staff/admin"""
    def has_object_permission(self, request, view, obj):
        if request.user.role in ['admin', 'staff']:
            return True
        
        # Check if the object has a user attribute (like BorrowRequest)
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # For other objects, allow if the object is the user itself
        return obj == request.user