from rest_framework import serializers
from APIcashless.models import CarteCashless, Configuration, Assets, Membre


#TODO: A virer au profit du webview/serializers, plus complet et qui sert au check carte et au paiement
class AssetsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assets
        fields = [
            'monnaie',
            'monnaie_name',
            'qty',
            'last_date_used',
        ]

#TODO: A virer au profit du webview/serializers, plus complet et qui sert au check carte et au paiement
class CarteCashlessSerializerForQrCode(serializers.ModelSerializer):
    # assets = AssetsSerializer(many=True)
    assets = serializers.SerializerMethodField()

    def get_assets(self, carte):
        config = Configuration.get_solo()
        monnaies_acceptee = [config.monnaie_principale, config.monnaie_principale_cadeau]

        instance = Assets.objects.filter(carte=carte, monnaie__in=monnaies_acceptee)
        serializer = AssetsSerializer(instance=instance, many=True)
        return serializer.data

    class Meta:
        model = CarteCashless
        fields = [
            'number',
            'uuid_qrcode',
            'assets',
        ]

class MembreSerializer(serializers.ModelSerializer):
    cards = CarteCashlessSerializerForQrCode(source='CarteCashless_Membre', many=True)

    class Meta:
        model = Membre
        fields = [
            'pk',
            'name',
            'prenom',
            'pseudo',
            'email',
            'demarchage',
            'code_postal',
            'date_naissance',
            'tel',
            'commentaire',
            'status',
            'date_inscription',
            'date_derniere_cotisation',
            'prochaine_echeance',
            'date_ajout',
            'last_action',
            'cotisation',
            'a_jour_cotisation',
            'cards',
        ]
        # depth = 1
        # read_only_fields = [
        #     'cards',
        # ]