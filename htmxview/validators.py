from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from APIcashless.models import Terminal, CarteCashless
import logging
import re

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


class linkValidator(serializers.Serializer):
    email = serializers.EmailField(required=True)
    last_name = serializers.CharField(required=True)
    first_name = serializers.CharField(required=True)
    tag_id = serializers.CharField(max_length=8, min_length=8, required=True)
    
    def validate_email(self, value):
        """
        Validate email format.
        """
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            raise serializers.ValidationError("Invalid email format")
        return value
    
    def validate_last_name(self, value):
        """
        Validate that last name is not empty.
        """
        if not value.strip():
            raise serializers.ValidationError("Last name cannot be empty")
        return value
    
    def validate_first_name(self, value):
        """
        Validate that first name is not empty.
        """
        if not value.strip():
            raise serializers.ValidationError("First name cannot be empty")
        return value
    
    def validate_tag_id(self, value):
        try:
            tag_id = value.upper()
            logger.info(f"--> tag_id = {tag_id}")

            fedowApi = FedowAPI()
            fedowApi.NFCcard.retrieve(tag_id)
            self.card = CarteCashless.objects.get(tag_id=tag_id)
            return self.card
        except CarteCashless.DoesNotExist:
            raise ValidationError(f"Card not found with tag {value}")
        except Exception as e:
            raise ValidationError(e)
