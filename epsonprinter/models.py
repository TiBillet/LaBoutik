import uuid
from django.utils.translation import gettext_lazy as _

from django.db import models


class Printer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)

    thermal_printer_adress = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("Adresse de l'imprimante"),
        help_text="USB ex: 0x04b8,0x0e28 ou ip locale"
    )

    serveur_impression = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("Adresse du serveur d'impression")
    )

    api_serveur_impression = models.CharField(
        max_length=50,
        blank=True, null=True,
        verbose_name=_("Clé d'api pour serveur d'impression")
    )

    revoquer_odoo_api_serveur_impression = models.BooleanField(
        default=False,
        verbose_name=_('Révoquer la clé API'),
        help_text="Selectionnez et validez pour supprimer la clé API et entrer une nouvelle."
    )

    def _api_serveur_impression(self):
        if self.api_serveur_impression:
            return f"{self.api_serveur_impression[:3]}{'*' * (len(self.api_serveur_impression) - 3)}"
        else:
            return None


    def __str__(self):
        return self.name

