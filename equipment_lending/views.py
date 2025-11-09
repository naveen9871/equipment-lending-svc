from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.db import transaction
from .models import Equipment, EquipmentCategory, BorrowRequest, Notification, Wishlist, MaintenanceLog
from .serializers import (
    EquipmentSerializer, EquipmentCategorySerializer, BorrowRequestSerializer,
    UserRegistrationSerializer, UserSerializer, NotificationSerializer,
    WishlistSerializer, MaintenanceLogSerializer
)
from .permissions import IsAdminOrStaff, IsAdmin, IsOwnerOrStaff


class UserViewSet(viewsets.GenericViewSet):
    serializer_class = UserSerializer

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'User registered successfully',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class EquipmentCategoryViewSet(viewsets.ModelViewSet):
    queryset = EquipmentCategory.objects.all()
    serializer_class = EquipmentCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [IsAuthenticated()]


class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.select_related('category').all()
    serializer_class = EquipmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'condition', 'is_active']
    search_fields = ['name', 'description', 'serial_number', 'location']
    ordering_fields = ['name', 'created_at', 'available_quantity', 'total_quantity']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'update_quantity']:
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        available = self.request.query_params.get('available', None)
        if available is not None:
            if available.lower() == 'true':
                queryset = queryset.filter(available_quantity__gt=0, is_active=True)
        return queryset

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get equipment with low available quantity"""
        threshold = int(request.query_params.get('threshold', 3))
        low_stock_equipment = self.get_queryset().filter(
            available_quantity__lte=threshold,
            is_active=True
        )
        serializer = self.get_serializer(low_stock_equipment, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def update_quantity(self, request, pk=None):
        """Update total quantity of equipment"""
        equipment = self.get_object()
        new_quantity = request.data.get('total_quantity')
        
        if new_quantity is None:
            return Response(
                {'error': 'total_quantity is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_quantity = int(new_quantity)
            if new_quantity < 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {'error': 'total_quantity must be a positive integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        equipment.total_quantity = new_quantity
        if equipment.available_quantity > new_quantity:
            equipment.available_quantity = new_quantity
        equipment.save()
        
        serializer = self.get_serializer(equipment)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        equipment = self.get_object()
        start = request.query_params.get('start')
        end = request.query_params.get('end')

        if not start or not end:
            return Response(
                {'error': 'start and end parameters required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_date = timezone.datetime.fromisoformat(start)
            end_date = timezone.datetime.fromisoformat(end)
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        overlapping = BorrowRequest.objects.filter(
            equipment=equipment,
            status__in=['approved', 'issued'],
            borrow_from__lt=end_date,
            borrow_until__gt=start_date
        )

        borrowed_quantity = sum(req.quantity for req in overlapping)
        available = equipment.total_quantity - borrowed_quantity

        return Response({
            'equipment_id': equipment.id,
            'total_quantity': equipment.total_quantity,
            'available_quantity': max(available, 0),
            'borrowed_quantity': borrowed_quantity,
            'period': {'start': start, 'end': end}
        })

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def wishlist(self, request, pk=None):
        """Add or remove equipment from wishlist"""
        equipment = self.get_object()
        
        if request.method == 'POST':
            wishlist_item, created = Wishlist.objects.get_or_create(
                user=request.user,
                equipment=equipment
            )
            if created:
                return Response({'message': 'Added to wishlist'}, status=status.HTTP_201_CREATED)
            return Response({'message': 'Already in wishlist'}, status=status.HTTP_200_OK)
        
        elif request.method == 'DELETE':
            deleted_count, _ = Wishlist.objects.filter(
                user=request.user,
                equipment=equipment
            ).delete()
            if deleted_count:
                return Response({'message': 'Removed from wishlist'})
            return Response({'error': 'Not in wishlist'}, status=status.HTTP_404_NOT_FOUND)


class BorrowRequestViewSet(viewsets.ModelViewSet):
    queryset = BorrowRequest.objects.select_related('user', 'equipment', 'approved_by').all()
    serializer_class = BorrowRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'equipment', 'user']
    ordering_fields = ['requested_date', 'borrow_from', 'borrow_until']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if user.role == 'student':
            queryset = queryset.filter(user=user)

        overdue = self.request.query_params.get('overdue', None)
        if overdue and overdue.lower() == 'true':
            queryset = queryset.filter(
                status='issued',
                borrow_until__lt=timezone.now()
            )

        return queryset

    def get_permissions(self):
        if self.action in ['approve', 'reject', 'issue', 'return_equipment', 'overdue_requests', 'pending']:
            return [IsAdminOrStaff()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrStaff()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        """Override create to check availability before creating request"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        equipment = serializer.validated_data['equipment']
        quantity = serializer.validated_data['quantity']
        borrow_from = serializer.validated_data['borrow_from']
        borrow_until = serializer.validated_data['borrow_until']
        
        # Check availability
        if not self.check_equipment_availability(equipment, quantity, borrow_from, borrow_until):
            return Response(
                {'error': 'Equipment not available for the requested period'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check max borrow duration (e.g., 14 days)
        max_days = 14
        if (borrow_until - borrow_from).days > max_days:
            return Response(
                {'error': f'Maximum borrow duration is {max_days} days'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_create(serializer)
        
        # Create notification
        Notification.objects.create(
            user=request.user,
            title="Borrow Request Submitted",
            message=f"Your request for {equipment.name} has been submitted and is under review.",
            notification_type='request_update',
            related_request=serializer.instance
        )
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def check_equipment_availability(self, equipment, quantity, start, end):
        """Check if equipment is available for the requested period"""
        overlapping_requests = BorrowRequest.objects.filter(
            equipment=equipment,
            status__in=['approved', 'issued'],
            borrow_from__lt=end,
            borrow_until__gt=start
        )
        
        borrowed_quantity = sum(req.quantity for req in overlapping_requests)
        available = equipment.total_quantity - borrowed_quantity
        
        return available >= quantity

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrStaff])
    def approve(self, request, pk=None):
        borrow_request = self.get_object()

        if borrow_request.status != 'pending':
            return Response(
                {'error': 'Only pending requests can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not borrow_request.check_availability():
            return Response(
                {'error': 'Equipment not available for requested period'},
                status=status.HTTP_400_BAD_REQUEST
            )

        borrow_request.status = 'approved'
        borrow_request.approved_by = request.user
        borrow_request.approved_date = timezone.now()
        borrow_request.save()

        # Create notification
        Notification.objects.create(
            user=borrow_request.user,
            title="Request Approved",
            message=f"Your request for {borrow_request.equipment.name} has been approved. Please collect it during the specified period.",
            notification_type='request_update',
            related_request=borrow_request
        )

        serializer = self.get_serializer(borrow_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrStaff])
    def reject(self, request, pk=None):
        borrow_request = self.get_object()

        if borrow_request.status != 'pending':
            return Response(
                {'error': 'Only pending requests can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')
        borrow_request.status = 'rejected'
        borrow_request.rejection_reason = reason
        borrow_request.approved_by = request.user
        borrow_request.approved_date = timezone.now()
        borrow_request.save()

        # Create notification
        Notification.objects.create(
            user=borrow_request.user,
            title="Request Rejected",
            message=f"Your request for {borrow_request.equipment.name} has been rejected. Reason: {reason}",
            notification_type='request_update',
            related_request=borrow_request
        )

        serializer = self.get_serializer(borrow_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrStaff])
    def issue(self, request, pk=None):
        borrow_request = self.get_object()

        if borrow_request.status != 'approved':
            return Response(
                {'error': 'Only approved requests can be issued'},
                status=status.HTTP_400_BAD_REQUEST
            )

        equipment = borrow_request.equipment
        if equipment.available_quantity < borrow_request.quantity:
            return Response(
                {'error': 'Insufficient equipment quantity'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            equipment.available_quantity -= borrow_request.quantity
            equipment.save()

            borrow_request.status = 'issued'
            borrow_request.issued_date = timezone.now()
            borrow_request.save()

        # Create notification
        Notification.objects.create(
            user=borrow_request.user,
            title="Equipment Issued",
            message=f"Your {borrow_request.equipment.name} has been issued. Due date: {borrow_request.borrow_until.strftime('%Y-%m-%d')}",
            notification_type='request_update',
            related_request=borrow_request
        )

        serializer = self.get_serializer(borrow_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrStaff])
    def return_equipment(self, request, pk=None):
        borrow_request = self.get_object()

        if borrow_request.status not in ['issued', 'overdue']:
            return Response(
                {'error': 'Only issued requests can be returned'},
                status=status.HTTP_400_BAD_REQUEST
            )

        equipment = borrow_request.equipment
        
        with transaction.atomic():
            equipment.available_quantity += borrow_request.quantity
            equipment.save()

            borrow_request.status = 'returned'
            borrow_request.returned_date = timezone.now()
            notes = request.data.get('notes', '')
            if notes:
                borrow_request.notes = notes
            borrow_request.save()

        # Create notification
        Notification.objects.create(
            user=borrow_request.user,
            title="Equipment Returned",
            message=f"Your {borrow_request.equipment.name} has been successfully returned. Thank you!",
            notification_type='request_update',
            related_request=borrow_request
        )

        serializer = self.get_serializer(borrow_request)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_requests(self, request):
        requests = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrStaff])
    def pending(self, request):
        requests = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrStaff])
    def overdue_requests(self, request):
        """Get all overdue requests"""
        overdue = self.get_queryset().filter(
            status='issued',
            borrow_until__lt=timezone.now()
        )
        serializer = self.get_serializer(overdue, many=True)
        return Response(serializer.data)


class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get dashboard statistics"""
        user = request.user
        
        if user.role in ['admin', 'staff']:
            total_equipment = Equipment.objects.filter(is_active=True).count()
            total_requests = BorrowRequest.objects.count()
            pending_requests = BorrowRequest.objects.filter(status='pending').count()
            active_borrows = BorrowRequest.objects.filter(status='issued').count()
            overdue_borrows = BorrowRequest.objects.filter(status='issued', borrow_until__lt=timezone.now()).count()
            low_stock_count = Equipment.objects.filter(available_quantity__lte=2, is_active=True).count()
            
            # Popular equipment
            popular_equipment = Equipment.objects.annotate(
                request_count=Count('borrowrequest')
            ).order_by('-request_count')[:5]
            
            return Response({
                'total_equipment': total_equipment,
                'total_requests': total_requests,
                'pending_requests': pending_requests,
                'active_borrows': active_borrows,
                'overdue_borrows': overdue_borrows,
                'low_stock_count': low_stock_count,
                'popular_equipment': EquipmentSerializer(popular_equipment, many=True, context={'request': request}).data
            })
        else:
            # Student statistics
            my_requests = BorrowRequest.objects.filter(user=user)
            total_requests = my_requests.count()
            pending_requests = my_requests.filter(status='pending').count()
            approved_requests = my_requests.filter(status='approved').count()
            active_borrows = my_requests.filter(status='issued').count()
            overdue_borrows = my_requests.filter(status='issued', borrow_until__lt=timezone.now()).count()
            
            return Response({
                'total_requests': total_requests,
                'pending_requests': pending_requests,
                'approved_requests': approved_requests,
                'active_borrows': active_borrows,
                'overdue_borrows': overdue_borrows,
            })


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read'})


class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related('equipment', 'equipment__category')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MaintenanceLogViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceLog.objects.select_related('equipment', 'completed_by').all()
    serializer_class = MaintenanceLogSerializer
    permission_classes = [IsAdminOrStaff]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['equipment', 'completed_by']
    ordering_fields = ['maintenance_date', 'created_at']