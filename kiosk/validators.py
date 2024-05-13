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
    uuid = serializers.SlugRelatedField(
        queryset=CarteCashless.objects.all(),
        slug_field='id'
    )
    total = serializers.DecimalField(max_digits=8, decimal_places=2)

