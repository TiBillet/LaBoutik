from rest_framework import serializers


class CashfloatChangeValidator(serializers.Serializer):
    cashfloat = serializers.FloatField()