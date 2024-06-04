from rest_framework import serializers
from APIcashless.models import CarteCashless


# Validate the number card recived by the miniserver
class CardValidator(serializers.Serializer):
    tag_id = serializers.SlugRelatedField(
        queryset=CarteCashless.objects.all(),
        slug_field='tag_id'
    )


# Validate the amount and uuid posted
class AmountValidator(serializers.Serializer):
    tag_id = serializers.SlugRelatedField(
        queryset=CarteCashless.objects.all(),
        slug_field='tag_id'
    )
    total = serializers.DecimalField(max_digits=8, decimal_places=2)
    device_confirm = serializers.CharField(required=False)


class BillValidator(serializers.Serializer):
    bill = serializers.DecimalField(max_digits=8, decimal_places=2)

    def validate_bill(self, value):
        try:
            value in [5.00,10.00,20.00,50.00,100.00]
            return value
        except ValueError: # We have to check how to send the error to
            # the device ...
            raise serializers.ValidationError("Bill error")
