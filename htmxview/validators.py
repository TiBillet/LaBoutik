from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from APIcashless.models import Terminal, CarteCashless
import logging

from fedow_connect.fedow_api import FedowAPI

logger = logging.getLogger(__name__)


class CashfloatChangeValidator(serializers.Serializer):
    cashfloat = serializers.FloatField()

class RefillWisePoseValidator(serializers.Serializer):
    totalAmount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    # terminal_pk = serializers.PrimaryKeyRelatedField(queryset=Terminal.objects.all())
    tag_id = serializers.CharField(max_length=8, min_length=8, required=True)

    def validate_tag_id(self, value):
        try:
            tag_id = value.upper()
            logger.info(f"--> tag_id = {tag_id}")

            fedowApi = FedowAPI()
            fedowApi.NFCcard.retrieve(tag_id)
            self.card  = CarteCashless.objects.get(tag_id=tag_id)
            return self.card
        except CarteCashless.DoesNotExist:
            raise ValidationError(f"Card not found with tag {value}")
        except Exception as e:
            raise ValidationError(e)

    def validate_totalAmount(self, value):
        """
        Check that the amount is positive.
        """
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")

        return int(value*100)
