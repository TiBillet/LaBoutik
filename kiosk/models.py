from uuid import uuid4

from django.db import models
from django.utils.translation import gettext_lazy as _

from APIcashless.models import CarteCashless


# Create your models here.


# Model that will save each card reeded by the NFC reeder
class ScannedNfcCard(models.Model):
    uuid = models.UUIDField(default=uuid4, editable=False)
    card = models.ForeignKey(CarteCashless, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='created at')


class Payment(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='created at')
    saved_at = models.DateTimeField(auto_now=True, verbose_name='saved at')

    card = models.ForeignKey(CarteCashless, on_delete=models.PROTECT, related_name='kiosk_payment',
                             verbose_name=_('Carte'))

    amount = models.DecimalField(max_digits=8, decimal_places=2, verbose_name=_('Somme souhaitée'))
    device_amount = models.DecimalField(default=0, max_digits=8, decimal_places=2,
                                        verbose_name=_('Somme insérée dans la machine'))


