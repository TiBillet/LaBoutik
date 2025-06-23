from rest_framework import serializers
from APIcashless.models import Terminal


class CashfloatChangeValidator(serializers.Serializer):
    cashfloat = serializers.FloatField()

class PaymentIntentTpeValidator(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    terminal_pk = serializers.PrimaryKeyRelatedField(queryset=Terminal.objects.all())

    def validate_amount(self, value):
        """
        Check that the amount is positive.
        """
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")

        return int(value*100)
