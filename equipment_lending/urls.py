from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EquipmentViewSet, EquipmentCategoryViewSet, BorrowRequestViewSet, 
    UserViewSet, DashboardViewSet, NotificationViewSet, WishlistViewSet,
    MaintenanceLogViewSet
)

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register('categories', EquipmentCategoryViewSet, basename='category')
router.register('equipment', EquipmentViewSet, basename='equipment')
router.register('requests', BorrowRequestViewSet, basename='request')
router.register('notifications', NotificationViewSet, basename='notification')
router.register('wishlist', WishlistViewSet, basename='wishlist')
router.register('maintenance', MaintenanceLogViewSet, basename='maintenance')

# Dashboard doesn't need basename since it's a ViewSet
router.register('dashboard', DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
]