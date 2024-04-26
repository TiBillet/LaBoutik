from APIcashless.models import ArticleVendu, Articles, Configuration, PointDeVente

# config = Configuration.get_solo()
# arts_me = ArticleVendu.objects.filter(article__methode=config.methode_vente_article)

arts_vendus = ArticleVendu.objects.filter(article__methode_choices=Articles.VENTE)
pdv_vente = PointDeVente.objects.filter(comportement=PointDeVente.VENTE).first()

for art in arts_vendus:
    if art.pos.comportement != PointDeVente.VENTE :
        ArticleVendu.objects.filter(pk=art.pk).update(pos=pdv_vente)
        print(f"{art.article.name} - {art.pos}")
