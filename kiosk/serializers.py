from rest_framework import serializers
from APIcashless.models import CarteCashless

# Serializer to create the data
class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarteCashless
        fields = '__all__'
