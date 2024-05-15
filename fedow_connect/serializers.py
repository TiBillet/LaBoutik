import logging

from rest_framework import serializers

from APIcashless.models import CarteCashless, MoyenPaiement, Origin, Configuration, Place

logger = logging.getLogger(__name__)




### Serializer spécial cashless pour envoyer les cartes vers FEDOW

class CardSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(source="id", read_only=True)
    first_tag_id = serializers.CharField(source="tag_id", read_only=True)
    qrcode_uuid = serializers.UUIDField(source='uuid_qrcode', read_only=True)
    number_printed = serializers.CharField(source="number", read_only=True)
    generation = serializers.SerializerMethodField()
    is_primary = serializers.SerializerMethodField()

    # Lors de la création de la carte vers FEDOW, si il existe déja des assets dans la carte cashless,
    # on les créé avec l'uuid de l'asset cashless pour une meilleure correspondance.
    tokens_uuid = serializers.SerializerMethodField()

    def get_tokens_uuid(self, carte: CarteCashless):
        return [{
            'asset_uuid': f"{token.monnaie.pk}",
            'token_uuid': f"{token.pk}",
        } for token in carte.assets.filter(
            monnaie__categorie__in=[MoyenPaiement.LOCAL_EURO, MoyenPaiement.LOCAL_GIFT])]

    def get_is_primary(self, carte: CarteCashless):
        return carte.cartes_maitresses.count() > 0

    def get_generation(self, carte: CarteCashless):
        if not carte.origin:
            config = Configuration.get_solo()
            # Le moyen de paiement local cashless est forcément celui de la place origin
            self_place = MoyenPaiement.objects.get(categorie='LE').place_origin
            origin, created = Origin.objects.get_or_create(place=self_place, generation=1)
            carte.origin = origin
            carte.save()
        return carte.origin.generation

    class Meta:
        model = CarteCashless
        fields = (
            'uuid',
            'first_tag_id',
            'qrcode_uuid',
            'number_printed',
            'generation',
            'is_primary',
            'tokens_uuid',
        )


