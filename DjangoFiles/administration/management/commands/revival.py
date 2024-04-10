from datetime import timedelta
from time import sleep

from django.utils import timezone

from APIcashless.models import CommandeSauvegarde, ArticleCommandeSauvegarde

#la date du 07 juillet a la raff' est pas mal du tout niveau boulot :)
mercredi_heure = timezone.now() - timedelta(days=3)
mercredi_date = mercredi_heure.date()
cmd_mercredi = CommandeSauvegarde.objects.filter(datetime__date=mercredi_date)

while len(cmd_mercredi) > 0 :
    mercredi_heure = timezone.now() - timedelta(days=3)

    cmd_mercredi = CommandeSauvegarde.objects.filter(datetime__date=mercredi_date)

    cmds = CommandeSauvegarde.objects.filter(
        datetime__date=mercredi_date,
    ).exclude(
        datetime__gte=mercredi_heure
    )

    for cmd in cmds:
        cmd : CommandeSauvegarde
        cmd.archive = False
        for article in cmd.articles.all() :
            article.reste_a_servir = article.qty
            article.statut = ArticleCommandeSauvegarde.PAYES
            article.save()
        cmd.datetime = cmd.datetime + timedelta(days=3)
        cmd.check_statut()
        cmd.save()
        print(f"COMMANDE NOUVELLE !")

    sleep(5)