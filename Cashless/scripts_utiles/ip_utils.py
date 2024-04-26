from django.utils import timezone
import logging

from APIcashless.models import IpUser

logger = logging.getLogger(__name__)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    x_real_ip = request.META.get('HTTP_X_REAL_IP')

    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    elif x_real_ip:
        ip = x_real_ip
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_ip_user(request):
    if request.user:
        ip = get_client_ip(request)
        ip_user, created = IpUser.objects.get_or_create(user=request.user, ip=ip)
        logger.info(f"{timezone.now()} str_user : {ip_user.user.username} ip : {ip}")
        return ip_user

    else:
        logger.info(f"{timezone.now()} str_user : None ip : None")
        return None

