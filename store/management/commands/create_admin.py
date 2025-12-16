from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Створення суперюзера автоматично'

    def handle(self, *args, **options):
        if not User.objects.filter(username='adminRia').exists():
            User.objects.create_superuser('adminRia', 'admin@example.com', 'Baitrens!29')
            self.stdout.write(self.style.SUCCESS('✅ СУПЕРЮЗЕР СТВОРЕНИЙ: логін adminRia, пароль Baitrens!29'))
        else:
            self.stdout.write('Суперюзер вже існує.')
