import logging
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from APIcashless.tasks import email_activation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        User = get_user_model()
        email_first_admin = input('email ? \n')
        staff_group, created = Group.objects.get_or_create(name="staff")
        admin, created = User.objects.get_or_create(
            username=email_first_admin,
            email=email_first_admin,
            is_staff=True,
            is_active=False,
        )
        admin.groups.add(staff_group)
        admin.save()
        email_activation(admin.uuid)