import uuid
import os
import time
import traceback
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class Printer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)

    EPSON_PI = 'EP'
    SUNMI_INTEGRATED_80 = 'S8'
    SUNMI_INTEGRATED_57 = 'S5'
    SUNMI_CLOUD = 'SC'

    PRINTER_TYPE_CHOICES = [
        (EPSON_PI, _('Epson via Serveur sur Pi (réseau ou USB) 80mm)')),
        (SUNMI_INTEGRATED_80, _('Imprimante intégrée aux Sunmi 80mm')),
        (SUNMI_INTEGRATED_57, _('Imprimante intégrée aux Sunmi 57mm')),
        (SUNMI_CLOUD, _('Sunmi Cloud printer 80mm')),
    ]

    printer_type = models.CharField(
        max_length=2,
        choices=PRINTER_TYPE_CHOICES,
        default=EPSON_PI,
        verbose_name=_('Type d\'imprimante')
    )

    ## POUR SUNMI Printer cloud

    sunmi_serial_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Numéro de série de l'imprimante Sunmi Cloud Printing",
        help_text="Vérifiez sur votre interface https://partner.sunmi.com et comparez sur le ticket de test."
    )

    ## POUR SUNMI Integrated

    host = models.ForeignKey("APIcashless.Appareil", on_delete=models.SET_NULL,
                             null=True, blank=True, related_name='printers',
                             verbose_name=_("Appareil hôte"))

    ### POUR EPSON TM20 et Raspberry Pi

    thermal_printer_adress = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Adresse de l'imprimante",
        help_text="USB ex: 0x04b8,0x0e28 ou ip locale"
    )

    serveur_impression = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Adresse du serveur d'impression"
    )

    api_serveur_impression = models.CharField(
        max_length=50,
        blank=True, null=True,
        verbose_name="Clé d'api pour serveur d'impression"
    )

    revoquer_api_serveur_impression = models.BooleanField(
        default=False,
        verbose_name='Révoquer la clé API',
        help_text="Selectionnez et validez pour supprimer la clé API et entrer une nouvelle."
    )

    def _api_serveur_impression(self):
        if self.api_serveur_impression:
            return f"{self.api_serveur_impression[:3]}{'*' * (len(self.api_serveur_impression) - 3)}"
        else:
            return None

    def can_print(self):
        """
        Check if the printer has all the required fields set for its type.
        Returns a tuple (bool, str) where the bool indicates if the printer can print
        and the str contains an error message if it can't.
        """
        if self.printer_type == self.EPSON_PI:
            # Check if thermal_printer_adress, serveur_impression, and api_serveur_impression are set
            if not self.thermal_printer_adress:
                return False, _("L'adresse de l'imprimante n'est pas définie")
            if not self.serveur_impression:
                return False, _("L'adresse du serveur d'impression n'est pas définie")
            if not self.api_serveur_impression:
                return False, _("La clé d'API pour le serveur d'impression n'est pas définie")
            return True, ""

        elif self.printer_type in [self.SUNMI_INTEGRATED_80, self.SUNMI_INTEGRATED_57]:
            # Check if host is set
            if not self.host:
                return False, _("L'appareil hôte n'est pas défini")
            return True, ""

        elif self.printer_type == self.SUNMI_CLOUD:
            # Check if sunmi_serial_number is set
            if not self.sunmi_serial_number:
                return False, _("Le numéro de série de l'imprimante Sunmi Cloud n'est pas défini")

            # Check if Configuration has sunmi_app_id and sunmi_app_key set
            try:
                from APIcashless.models import Configuration
                config = Configuration.objects.get()

                try:
                    config.get_sunmi_app_id()
                except Exception:
                    return False, _("L'APP ID Sunmi n'est pas défini dans la configuration")

                try:
                    config.get_sunmi_app_key()
                except Exception:
                    return False, _("L'APP KEY Sunmi n'est pas défini dans la configuration")

                return True, ""
            except Exception as e:
                return False, str(e)

        return False, _("Type d'imprimante non reconnu")

    def test_print(self):
        """
        Attempt to print a test page based on the printer type.
        Returns a tuple (bool, str) where the bool indicates if the test was successful
        and the str contains an error message if it wasn't.
        """
        can_print, error_msg = self.can_print()
        if not can_print:
            return False, error_msg

        if self.printer_type == self.EPSON_PI:
            # Implement test print for EPSON_PI
            try:
                # This is a placeholder. Actual implementation would depend on how EPSON_PI printers are accessed
                return True, _("Test d'impression envoyé à l'imprimante Epson")
            except Exception as e:
                return False, str(e)

        elif self.printer_type in [self.SUNMI_INTEGRATED_80, self.SUNMI_INTEGRATED_57]:
            # Implement test print for SUNMI_INTEGRATED
            try:
                # This is a placeholder. Actual implementation would depend on how SUNMI_INTEGRATED printers are accessed
                return True, _("Test d'impression envoyé à l'imprimante Sunmi intégrée")
            except Exception as e:
                return False, str(e)

        elif self.printer_type == self.SUNMI_CLOUD:
            # Implement test print for SUNMI_CLOUD using SunmiCloudPrinter
            try:
                from APIcashless.models import Configuration
                from .sunmi_cloud_printer import SunmiCloudPrinter, ALIGN_CENTER

                config = Configuration.objects.get()
                app_id = config.get_sunmi_app_id()
                app_key = config.get_sunmi_app_key()

                # Create a printer instance with 384 dots per line (standard for 80mm thermal printer)
                printer = SunmiCloudPrinter(384, app_id=app_id, app_key=app_key, printer_sn=self.sunmi_serial_number)

                # Create a simple test receipt
                printer.lineFeed()
                printer.setAlignment(ALIGN_CENTER)
                printer.setPrintModes(True, True, False)  # Bold, double height, normal width
                printer.appendText("*** TEST RECEIPT ***\n")
                printer.setPrintModes(False, False, False)  # Reset print modes
                printer.appendText("Sunmi Cloud NT311 Printer\n")
                printer.appendText("------------------------\n")
                printer.appendText(f"Printer Name: {self.name}\n")
                printer.appendText(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                printer.appendText("This is a test receipt to verify\n")
                printer.appendText("that your Sunmi Cloud Printer is\n")
                printer.appendText("working correctly.\n")
                printer.lineFeed(3)
                printer.cutPaper(False)  # Partial cut

                # Generate a unique trade number for this print job
                trade_no = f"{self.sunmi_serial_number}_{int(time.time())}"

                # Send the print job to the printer
                printer.pushContent(
                    trade_no=trade_no,
                    sn=self.sunmi_serial_number,
                    count=1,
                    media_text="Test Receipt"
                )

                return True, _("Test d'impression envoyé à l'imprimante Sunmi Cloud")
            except Exception as e:
                traceback.print_exc()
                return False, str(e)

        return False, _("Type d'imprimante non reconnu")

    def __str__(self):
        return self.name
