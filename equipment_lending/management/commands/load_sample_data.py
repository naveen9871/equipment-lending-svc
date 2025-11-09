from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from equipment_lending.models import EquipmentCategory, Equipment, BorrowRequest
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Load sample data for equipment lending system'

    def handle(self, *args, **options):
        self.stdout.write('Loading sample data...')

        # Create users
        admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@school.edu',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role='admin',
            phone='+1234567890',
            department='Administration'
        )

        staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@school.edu',
            password='staff123',
            first_name='Staff',
            last_name='Member',
            role='staff',
            phone='+1234567891',
            department='IT Department'
        )

        student1 = User.objects.create_user(
            username='student1',
            email='john.doe@student.school.edu',
            password='student123',
            first_name='John',
            last_name='Doe',
            role='student',
            phone='+1234567892',
            department='Computer Science'
        )

        student2 = User.objects.create_user(
            username='student2',
            email='jane.smith@student.school.edu',
            password='student123',
            first_name='Jane',
            last_name='Smith',
            role='student',
            phone='+1234567893',
            department='Media Studies'
        )

        # Create categories
        photography = EquipmentCategory.objects.create(
            name='Photography',
            description='Cameras, lenses, and photography equipment'
        )

        technology = EquipmentCategory.objects.create(
            name='Technology',
            description='Laptops, tablets, and electronic devices'
        )

        sports = EquipmentCategory.objects.create(
            name='Sports',
            description='Sports equipment and gear'
        )

        # Create equipment
        camera = Equipment.objects.create(
            name='Canon EOS R5 Camera',
            category=photography,
            description='Professional mirrorless camera with 45MP sensor',
            condition='excellent',
            total_quantity=5,
            available_quantity=3,
            serial_number='CAM001',
            location='Media Lab A',
            purchase_date='2023-06-15'
        )

        laptop = Equipment.objects.create(
            name='MacBook Pro 16-inch',
            category=technology,
            description='Apple MacBook Pro with M2 Pro chip, 16GB RAM, 1TB SSD',
            condition='excellent',
            total_quantity=10,
            available_quantity=8,
            serial_number='MBP001',
            location='Computer Lab B',
            purchase_date='2023-08-20'
        )

        basketball = Equipment.objects.create(
            name='Basketball Set',
            category=sports,
            description='Professional basketball with pump and net',
            condition='good',
            total_quantity=15,
            available_quantity=12,
            serial_number='SPT001',
            location='Sports Storage',
            purchase_date='2023-03-10'
        )

        drone = Equipment.objects.create(
            name='DJI Mavic Air 2',
            category=photography,
            description='4K drone with 3-axis gimbal',
            condition='excellent',
            total_quantity=3,
            available_quantity=1,
            serial_number='DRN001',
            location='Media Lab A',
            purchase_date='2023-11-05'
        )

        # Create borrow requests
        BorrowRequest.objects.create(
            user=student1,
            equipment=camera,
            quantity=1,
            purpose='For photography class project - campus landscape photography',
            status='approved',
            borrow_from=timezone.now() + timedelta(days=1),
            borrow_until=timezone.now() + timedelta(days=6),
            approved_by=staff_user,
            approved_date=timezone.now()
        )

        BorrowRequest.objects.create(
            user=student1,
            equipment=laptop,
            quantity=1,
            purpose='Need for software development project - building a web application',
            status='pending',
            borrow_from=timezone.now() + timedelta(days=3),
            borrow_until=timezone.now() + timedelta(days=10)
        )

        BorrowRequest.objects.create(
            user=student2,
            equipment=drone,
            quantity=1,
            purpose='Aerial photography for film studies project',
            status='issued',
            borrow_from=timezone.now() - timedelta(days=2),
            borrow_until=timezone.now() + timedelta(days=5),
            approved_by=staff_user,
            approved_date=timezone.now() - timedelta(days=3),
            issued_date=timezone.now() - timedelta(days=2)
        )

        self.stdout.write(
            self.style.SUCCESS('Successfully loaded sample data!')
        )
        self.stdout.write('Created:')
        self.stdout.write(f'  - 4 users (admin, staff, 2 students)')
        self.stdout.write(f'  - 3 equipment categories')
        self.stdout.write(f'  - 4 equipment items')
        self.stdout.write(f'  - 3 borrow requests')
        self.stdout.write('\nTest credentials:')
        self.stdout.write('  Admin: admin_user / admin123')
        self.stdout.write('  Staff: staff_user / staff123')
        self.stdout.write('  Student: student1 / student123')