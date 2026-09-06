import logging
import time
from datetime import timedelta

import stripe
from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.utils import timezone

from APIcashless.models import PaymentsIntent, CarteCashless, ConfigurationStripe
from fedow_connect.fedow_api import FedowAPI

logger = logging.getLogger(__name__)

# Seuil a partir duquel on considere Stripe injoignable.
# Ce seuil ne fait PAS sortir de la boucle de polling : il ne sert qu'a qualifier la
# raison de sortie dans les logs. Abandonner le polling au bout de cinq secondes
# reviendrait a annuler le paiement d'un usager qui a encore presque deux minutes pour
# presenter sa carte -- or le reseau d'un lieu hoquete regulierement.
# / Threshold above which Stripe is considered unreachable. It does NOT break the
# polling loop, it only qualifies the exit reason in the logs.
MAX_CONSECUTIVE_STRIPE_ERRORS = 5

# Duree pendant laquelle on laisse Stripe trancher un paiement DEJA ENGAGE.
# / How long we let Stripe settle an already engaged payment.
PROCESSING_GRACE_SECONDS = 10

# Filet de secours quand Stripe est injoignable au moment de l'annulation.
# Tant que le rattrapage n'a pas abouti, un lecteur peut etre reste ARME : le filet doit
# donc couvrir une vraie coupure de reseau de lieu, pas seulement un hoquet. 20 tentatives
# toutes les 30 secondes = dix minutes.
# / Fallback retries when Stripe is unreachable at cancellation time: 10 minutes of cover,
# because an armed reader stays dangerous until the catch-up succeeds.
SETTLE_RETRY_COUNTDOWN_SECONDS = 30
MAX_SETTLE_ATTEMPTS = 20


def push_screen_to_kiosk(payment_intent, template_name, retry_count=0):
    """
    Pousse un ecran vers la borne, sur le groupe Channels dont le nom est l'id Stripe
    de l'intention de paiement.
    / Pushes a screen to the kiosk, on the Channels group named after the Stripe id.

    LOCALISATION : htmxview/tasks.py

    L'ENVOI EST TOUJOURS GARDE. Une panne du channel layer (Redis) est un probleme
    d'AFFICHAGE : si elle remontait a l'appelant, elle serait traitee comme une
    defaillance de paiement et declencherait une annulation. On couperait la carte
    d'un usager en plein tap a cause d'un hoquet Redis.
    / The send is always guarded: a channel layer outage is a DISPLAY problem and must
    never bubble up into the payment cancellation path.
    """
    if not payment_intent.payment_intent_stripe_id:
        logger.error(f"Pas d'id Stripe pour {payment_intent.pk} : impossible de joindre la borne")
        return

    try:
        async_to_sync(get_channel_layer().group_send)(
            payment_intent.payment_intent_stripe_id,
            {
                'type': 'template',
                'template': template_name,
                'status': payment_intent.status,
                'status_display': payment_intent.get_status_display(),
                'timestamp': timezone.now().isoformat(),
                'retry_count': retry_count,
            }
        )
    except Exception as erreur_websocket:
        logger.error(
            f"Echec de l'envoi de l'ecran {template_name} pour {payment_intent.pk} -- {erreur_websocket}"
        )


def read_stripe_status(payment_intent):
    """
    Statut BRUT de l'intention de paiement chez Stripe, ou None si Stripe est injoignable.

    On interroge Stripe directement au lieu de passer par `PaymentsIntent.get_from_stripe`
    car celui-ci court-circuite des que le statut en base est terminal
    (APIcashless/models.py) : il ne permet donc pas de verifier un statut qu'on aurait
    ecrit soi-meme par defaut.
    / Raw Stripe status, or None if Stripe is unreachable. Queried directly because
    get_from_stripe() short-circuits on an already terminal local status.
    """
    try:
        return stripe.PaymentIntent.retrieve(payment_intent.payment_intent_stripe_id).status
    except Exception as erreur_lecture:
        logger.error(f"Statut Stripe illisible pour {payment_intent.pk} -- {erreur_lecture}")
        return None


def wait_for_engaged_payment_to_settle(payment_intent):
    """
    Laisse a Stripe le temps de trancher un paiement deja engage, et renvoie le statut
    brut final (ou None si Stripe est injoignable).
    / Lets Stripe settle an already engaged payment and returns the final raw status.

    POURQUOI CETTE ATTENTE :
    des que la carte est presentee, l'intention passe en 'processing' et Stripe REFUSE
    de l'annuler -- l'exception qui autorise l'annulation d'un paiement en cours ne
    couvre que les prelevements bancaires (ACH, SEPA...), pas le 'card_present'. Le
    lecteur refuse lui aussi le desarmement en pleine autorisation
    ('terminal_reader_busy'). Une carte tapee dans les dernieres secondes du polling
    tombe exactement la : les deux annulations echouent, l'argent est bel et bien
    encaisse, Fedow credite la carte via le webhook Stripe -- et afficher « Annule »
    ferait recharger une seconde fois un usager qui a deja paye.
    On attend donc que Stripe ait tranche avant de conclure quoi que ce soit.

    / A card presented at the last second leaves the intent in 'processing', which a
    card_present intent cannot be cancelled from. Wait for Stripe to settle instead of
    lying to the user with a "canceled" screen.
    """
    stripe_status = read_stripe_status(payment_intent)
    if stripe_status != 'processing':
        return stripe_status

    logger.info(
        f"Paiement {payment_intent.pk} deja engage chez Stripe (processing) : "
        f"attente de {PROCESSING_GRACE_SECONDS}s avant de conclure"
    )
    deadline = timezone.now() + timedelta(seconds=PROCESSING_GRACE_SECONDS)
    while stripe_status == 'processing' and timezone.now() < deadline:
        time.sleep(1)
        stripe_status = read_stripe_status(payment_intent)

    return stripe_status


def persist_if_terminal(payment_intent, stripe_status):
    """
    Persiste le statut si Stripe donne le paiement pour termine, et dit si c'etait le cas.
    / Persists the status if Stripe reports the payment as final, and says whether it was.
    """
    if stripe_status == 'succeeded':
        payment_intent.status = PaymentsIntent.SUCCEEDED
        payment_intent.save()
        return True

    if stripe_status == 'canceled':
        payment_intent.status = PaymentsIntent.CANCELED
        payment_intent.save()
        return True

    return False


def cancel_reader_action_if_ours(payment_intent):
    """
    Desarme le lecteur, mais UNIQUEMENT si l'action en cours porte bien cette intention
    de paiement.
    / Cancels the reader action, but only if it actually belongs to this payment intent.

    POURQUOI CETTE VERIFICATION :
    `stripe.terminal.Reader.cancel_action` est scope au LECTEUR, pas a l'intention de
    paiement : l'API ne prend aucun parametre payment_intent. Un lecteur sert les clients
    les uns apres les autres, et une tache de polling peut survivre au paiement qu'elle
    surveille (une carte refusee laisse un statut non terminal jusqu'au timeout). Appeler
    cancel_action a l'aveugle depuis une tache perimee coupe alors le paiement du client
    SUIVANT en plein tap.
    / cancel_action is scoped to the READER, not to the payment intent: a stale task
    would disarm whatever payment is currently running on that terminal.
    """
    reader_stripe_id = payment_intent.terminal.stripe_id
    try:
        reader = stripe.terminal.Reader.retrieve(reader_stripe_id)
    except Exception as erreur_lecteur:
        logger.error(f"Lecteur {reader_stripe_id} illisible pour {payment_intent.pk} -- {erreur_lecteur}")
        return

    action = reader.get('action') or {}
    if action.get('status') != 'in_progress':
        logger.info(f"Lecteur {reader_stripe_id} : aucune action en cours, rien a desarmer")
        return

    action_payment_intent = (action.get('process_payment_intent') or {}).get('payment_intent')
    # Stripe renvoie soit l'identifiant, soit l'objet complet si la requete l'a etendu.
    # / Stripe returns either the id or the expanded object.
    action_payment_intent_id = getattr(action_payment_intent, 'id', action_payment_intent)

    if action_payment_intent_id != payment_intent.payment_intent_stripe_id:
        logger.warning(
            f"Lecteur {reader_stripe_id} occupe par {action_payment_intent_id} et non par "
            f"{payment_intent.payment_intent_stripe_id} : on ne desarme pas le paiement d'un autre client"
        )
        return

    try:
        stripe.terminal.Reader.cancel_action(reader_stripe_id)
        logger.info(f"Lecteur {reader_stripe_id} desarme pour {payment_intent.pk}")
    except Exception as erreur_annulation:
        logger.error(f"Echec cancel_action sur {reader_stripe_id} pour {payment_intent.pk} -- {erreur_annulation}")


def cancel_payment_on_stripe(payment_intent):
    """
    Annule le paiement chez Stripe et laisse TOUJOURS `payment_intent.status` sur un
    statut terminal persiste en base.
    / Cancels the payment on Stripe and always leaves a terminal status persisted.

    LOCALISATION : htmxview/tasks.py

    POURQUOI CETTE FONCTION EXISTE :
    aucun ecran « Annule » ne doit jamais partir vers la borne sans que cette annulation
    ait ete tentee. Tant que l'action du lecteur n'est pas annulee, le WisePOS reste ARME
    et accepte encore une carte : le paiement serait encaisse par Stripe et la carte
    creditee par Fedow (via son webhook), derriere un ecran qui affiche « Annule ».
    L'usager croit avoir echoue et recharge une seconde fois ; ou bien c'est le client
    SUIVANT qui tape sa carte et credite celle du precedent.
    Elle est appelee par TOUS les chemins de sortie de `poll_payment_intent_status`, et
    par `Kiosk.refill_with_wisepos` quand la tache de polling n'a pas pu demarrer.

    / No "canceled" screen may ever reach the kiosk without this cancellation having
    been attempted: an armed reader would still charge a late tap.

    DEUX GARANTIES, dont depend tout le reste :

    1. Apres l'appel, `payment_intent.status` porte un statut TERMINAL (SUCCEEDED ou
       CANCELED), persiste en base. L'appelant s'en sert pour choisir l'ecran, et le
       websocket le relit pour rejouer cet ecran si la borne se reconnecte
       (htmxview/consumers.py). Un statut non terminal laisserait la borne sur le
       spinner indefiniment, puisque plus aucune tache ne la surveille.
    2. Ce statut est celui que Stripe connait, jamais la raison de l'appel : une carte
       presentee juste avant l'annulation donne un vrai succes, et c'est le succes qu'il
       faut afficher.

    / After this call the status is terminal AND persisted, and it is the status Stripe
    knows, never the reason we were called.

    :param payment_intent: instance de PaymentsIntent a annuler
    """
    # Un paiement deja termine ne se re-annule pas. Sans cette garde, une simple panne
    # d'affichage apres un paiement REUSSI ferait desarmer un lecteur qui sert peut-etre
    # deja le client suivant, et ecraserait un succes en « annule » en base (le mode DEMO
    # ci-dessous, lui, ecrit sans jamais interroger Stripe).
    # / A finished payment is never re-cancelled: this guard protects both the reader and
    # an already succeeded status.
    if payment_intent.status in [PaymentsIntent.SUCCEEDED, PaymentsIntent.CANCELED]:
        logger.info(f"Paiement {payment_intent.pk} deja terminal ({payment_intent.status}) : rien a annuler")
        return

    if settings.DEMO:
        # En DEMO il n'y a pas de Stripe a annuler : la fin du polling vaut annulation.
        # / No Stripe to cancel in DEMO: end of polling means cancellation.
        payment_intent.status = PaymentsIntent.CANCELED
        payment_intent.save()
        return

    config_stripe = ConfigurationStripe.get_solo()
    stripe.api_key = config_stripe.get_stripe_api()

    # 1. Stripe est le SEUL arbitre de ce qui a ete encaisse. On lui demande d'abord ou
    #    en est le paiement, et on lui laisse le temps de trancher s'il est deja engage.
    # / Stripe is the only arbiter of what was charged: ask first, cancel after.
    stripe_status = wait_for_engaged_payment_to_settle(payment_intent)

    if persist_if_terminal(payment_intent, stripe_status):
        logger.info(
            f"Paiement {payment_intent.pk} deja tranche par Stripe ({stripe_status}) : aucune annulation"
        )
        return

    # 2. Le paiement n'a pas abouti : on desarme le lecteur puis on annule l'intention.
    #    Les deux annulations sont tentees SEPAREMENT : un lecteur qui ne repond plus ne
    #    doit pas empecher l'annulation de l'intention de paiement.
    # / Cancel both sides separately: an unresponsive reader must not prevent the
    # payment intent cancellation.
    cancel_reader_action_if_ours(payment_intent)

    try:
        stripe.PaymentIntent.cancel(payment_intent.payment_intent_stripe_id)
    except Exception as erreur_intention:
        logger.error(f"Echec PaymentIntent.cancel pour {payment_intent.pk} -- {erreur_intention}")

    # 3. On relit le statut reel et on le persiste. get_from_stripe() ecrit en base.
    # / Re-read the real status and persist it.
    try:
        payment_intent.get_from_stripe()
    except Exception as erreur_relecture:
        logger.error(f"Echec de la relecture du statut pour {payment_intent.pk} -- {erreur_relecture}")

    if payment_intent.status in [PaymentsIntent.SUCCEEDED, PaymentsIntent.CANCELED]:
        return

    # 3 bis. La carte a pu etre presentee ENTRE la lecture de l'etape 1 et l'annulation :
    #        le cancel est alors refuse et on relit 'processing'. C'est exactement le
    #        mensonge que l'etape 1 evite, sur une fenetre de deux secondes. On laisse
    #        donc Stripe trancher une seconde fois avant de conclure.
    # / The card may have been tapped between step 1 and the cancel: let Stripe settle
    # once more rather than showing "canceled" for a payment that is going through.
    if payment_intent.status == PaymentsIntent.IN_PROGRESS:
        stripe_status = wait_for_engaged_payment_to_settle(payment_intent)
        if persist_if_terminal(payment_intent, stripe_status):
            logger.warning(
                f"Paiement {payment_intent.pk} tranche par Stripe ({stripe_status}) PENDANT l'annulation"
            )
            return

    # 4. Le statut reste non terminal : soit Stripe est injoignable, soit le paiement est
    #    encore en cours de traitement chez lui. Dans les deux cas on ne sait pas si le
    #    lecteur a ete desarme. On ecrit CANCELED pour que la borne sorte du spinner et
    #    affiche un ecran final, puis on programme un rattrapage qui ira verifier chez
    #    Stripe des que possible : c'est lui qui desarmera le lecteur, ou corrigera ce
    #    statut si le paiement avait finalement abouti.
    # / Status still not final (Stripe unreachable, or payment still processing): write
    # CANCELED so the kiosk leaves the spinner, and schedule a catch-up task to really
    # disarm the reader.
    logger.error(
        f"Annulation NON CONFIRMEE pour {payment_intent.pk} (statut={payment_intent.status}, "
        f"Stripe injoignable ou paiement encore en cours) : statut force a CANCELED, "
        f"rattrapage programme dans {SETTLE_RETRY_COUNTDOWN_SECONDS}s"
    )
    payment_intent.status = PaymentsIntent.CANCELED
    payment_intent.save()
    ensure_payment_settled.apply_async(
        (payment_intent.pk,),
        countdown=SETTLE_RETRY_COUNTDOWN_SECONDS,
    )


@shared_task
def ensure_payment_settled(payment_intent_pk, attempt=1):
    """
    Rattrapage differe : verifie chez Stripe l'etat reel d'un paiement dont l'annulation
    n'a pas pu etre confirmee, et desarme le lecteur si besoin.
    / Deferred catch-up: checks the real state of a payment whose cancellation could not
    be confirmed, and disarms the reader if needed.

    LOCALISATION : htmxview/tasks.py

    Programmee par `cancel_payment_on_stripe` quand Stripe est reste injoignable. A ce
    moment la, la base porte CANCELED par defaut et la borne affiche « Annule », mais
    deux choses restent en suspens :
      - le lecteur peut etre reste ARME, et encaisserait la prochaine carte presentee sur
        une intention orpheline dont les metadata signees designent l'usager precedent ;
      - le paiement a pu aboutir pendant la coupure, auquel cas la base et l'ecran mentent.
    Cette tache tranche les deux, et se reprogramme jusqu'a MAX_SETTLE_ATTEMPTS fois tant
    que Stripe ne repond pas.

    ELLE NE CORRIGE PAS L'ECRAN DE LA BORNE, et ne le peut pas : le hx-swap-oob de
    kiosk/cancel.html remplace #tb-kiosque, qui CONTIENT la section ws-connect
    (kiosk/waiting_credit_card_terminal.html) -- le websocket est donc ferme des l'instant
    ou « Annule » s'affiche. Ce qu'elle repare, c'est le lecteur et la base ; un usager
    mal informe se rattrape par la reconciliation, pas par un ecran.
    / It cannot fix the kiosk screen: the cancel.html OOB swap replaces #tb-kiosque, which
    contains the ws-connect section, so the socket is already closed. It repairs the
    reader and the stored status.

    :param payment_intent_pk: cle primaire du PaymentsIntent a verifier
    :param attempt: numero de la tentative en cours
    """
    if settings.DEMO:
        return

    try:
        payment_intent = PaymentsIntent.objects.get(pk=payment_intent_pk)
    except PaymentsIntent.DoesNotExist:
        logger.error(f"Rattrapage : payment intent {payment_intent_pk} introuvable")
        return

    if not payment_intent.payment_intent_stripe_id:
        return

    config_stripe = ConfigurationStripe.get_solo()
    stripe.api_key = config_stripe.get_stripe_api()

    stripe_status = read_stripe_status(payment_intent)

    if stripe_status is None or stripe_status == 'processing':
        reschedule_settle(payment_intent_pk, attempt)
        return

    if stripe_status == 'succeeded':
        # Le paiement avait abouti : la base mentait, on la corrige. Fedow a credite la
        # carte de son cote via le webhook Stripe, donc l'usager a bien son argent -- mais
        # il a vu « Annule », et c'est cette ligne de log qui permet de le comprendre apres
        # coup lors d'une reconciliation.
        # / The payment did go through: fix the stored status. Fedow credited the card via
        # the Stripe webhook, but the user saw "canceled": this log line is what makes the
        # discrepancy explainable during reconciliation.
        logger.error(
            f"Rattrapage : le paiement {payment_intent.pk} avait ABOUTI chez Stripe alors que "
            f"la borne a affiche « Annule » -- statut corrige en base, carte creditee par Fedow"
        )
        payment_intent.status = PaymentsIntent.SUCCEEDED
        payment_intent.save()
        return

    if stripe_status == 'canceled':
        logger.info(f"Rattrapage : {payment_intent.pk} bien annule chez Stripe")
        return

    # Statut encore annulable : le lecteur est probablement reste arme.
    # / Still cancellable: the reader is most likely still armed.
    cancel_reader_action_if_ours(payment_intent)
    try:
        stripe.PaymentIntent.cancel(payment_intent.payment_intent_stripe_id)
        logger.info(f"Rattrapage : intention {payment_intent.pk} annulee chez Stripe")
    except Exception as erreur_intention:
        logger.error(f"Rattrapage : echec PaymentIntent.cancel pour {payment_intent.pk} -- {erreur_intention}")
        reschedule_settle(payment_intent_pk, attempt)


def reschedule_settle(payment_intent_pk, attempt):
    """
    Reprogramme le rattrapage, sauf si on a deja epuise les tentatives.
    / Reschedules the catch-up task unless attempts are exhausted.
    """
    if attempt >= MAX_SETTLE_ATTEMPTS:
        logger.error(
            f"Rattrapage abandonne apres {attempt} tentatives pour {payment_intent_pk} : "
            f"le lecteur peut etre reste arme, verification manuelle necessaire"
        )
        return

    ensure_payment_settled.apply_async(
        (payment_intent_pk, attempt + 1),
        countdown=SETTLE_RETRY_COUNTDOWN_SECONDS,
    )


@shared_task
def poll_payment_intent_status(payment_intent_pk, max_duration_seconds=120):
    """
    Surveille le statut d'une intention de paiement TPE, une fois par seconde,
    pendant max_duration_seconds au maximum.
    / Polls a terminal payment intent status once a second, up to max_duration_seconds.

    LOCALISATION : htmxview/tasks.py

    Lancee par `Kiosk.refill_with_wisepos` (htmxview/views.py) juste apres avoir arme
    le lecteur WisePOS. Elle pousse l'avancement puis l'ecran final vers la borne, par
    le groupe Channels dont le nom est l'id Stripe de l'intention de paiement.

    LA BOUCLE S'ARRETE sur SUCCEEDED ou CANCELED, ou au bout de max_duration_seconds.
    Une erreur Stripe ne la fait PAS sortir : tant qu'il reste du temps, l'usager peut
    encore presenter sa carte, et sortir plus tot reviendrait a lui annuler son paiement
    pour un hoquet reseau de quelques secondes.

    TOUS LES CHEMINS DE SORTIE envoient un ecran final a la borne, et aucun n'envoie
    « Annule » sans avoir tente l'annulation reelle chez Stripe
    (voir `cancel_payment_on_stripe`).

    COMMUNICATION :
    Emet : event 'message' (avancement) puis 'template' (ecran final) vers
           htmxview.consumers.TerminalConsumer.

    :param payment_intent_pk: cle primaire du PaymentsIntent a surveiller
    :param max_duration_seconds: duree maximale de surveillance, en secondes
    :return: True si le paiement a reussi, False sinon
    """
    time.sleep(1)

    logger.info(f"Starting to poll payment intent status for ID: {payment_intent_pk}")

    channel_layer = get_channel_layer()
    room_name = None
    payment_intent = None

    start_time = timezone.now()
    end_time = start_time + timedelta(seconds=max_duration_seconds)

    try:
        payment_intent = PaymentsIntent.objects.get(pk=payment_intent_pk)
        logger.info(f"payment_intent {payment_intent.pk} -- status : {payment_intent.status}")
        room_name = payment_intent.payment_intent_stripe_id

        retry_count = 0
        consecutive_stripe_errors = 0
        while timezone.now() < end_time and payment_intent.status not in [PaymentsIntent.SUCCEEDED,
                                                                          PaymentsIntent.CANCELED]:
            # L'appel a Stripe est protege ITERATION PAR ITERATION.
            # Une coupure reseau ne doit pas faire sortir de la boucle : sinon le paiement
            # continue cote terminal pendant que plus personne ne le surveille, et surtout
            # on annulerait la recharge d'un usager qui a encore tout le temps de taper
            # sa carte. On ne renonce qu'a la fin de la fenetre de surveillance.
            # / Guard the Stripe call per iteration: a network glitch must never abort the
            # loop, or we would cancel a payment the user can still complete.
            try:
                status = payment_intent.get_from_stripe()
                consecutive_stripe_errors = 0
            except Exception as erreur_stripe:
                consecutive_stripe_errors += 1
                # warning et non error : la LoggingIntegration de Sentry remonte un
                # evenement par ligne ERROR, et cette boucle tourne une fois par seconde
                # pendant deux minutes. Une coupure ferait 120 evenements pour un seul
                # incident -- c'est la ligne de sortie de boucle, plus bas, qui porte
                # l'erreur.
                # / warning, not error: Sentry raises one event per ERROR line and this
                # loop runs once a second. The single exit line below carries the error.
                logger.warning(
                    f"Payment intent {payment_intent_pk} : erreur Stripe "
                    f"{consecutive_stripe_errors} d'affilee -- {erreur_stripe}"
                )
                time.sleep(1)
                continue

            logger.info(f"Payment intent {payment_intent_pk} status: {payment_intent.get_status_display()}")

            # Send the status update via WebSocket.
            # L'envoi est garde : une panne du channel layer n'est qu'un probleme
            # d'affichage et ne doit surtout pas remonter au handler d'erreur global,
            # qui annulerait le paiement en cours.
            # / Guarded send: a channel layer outage must not reach the global error
            # handler, which would cancel a live payment.
            event = {
                'type': 'message',
                'status': status,
                'status_display': payment_intent.get_status_display(),
                'timestamp': timezone.now().isoformat(),
                'retry_count': retry_count,
            }

            try:
                async_to_sync(channel_layer.group_send)(
                    room_name,
                    event
                )
            except Exception as erreur_websocket:
                logger.error(f"Echec de l'envoi de l'avancement sur {room_name} -- {erreur_websocket}")

            # Wait for 1 second before the next poll
            retry_count += 1
            time.sleep(1)

        logger.info(f"Finished polling payment intent status for ID: {payment_intent_pk}")

        if payment_intent.status not in [PaymentsIntent.CANCELED, PaymentsIntent.SUCCEEDED]:
            stripe_injoignable = consecutive_stripe_errors >= MAX_CONSECUTIVE_STRIPE_ERRORS
            raison = ("Stripe injoignable" if stripe_injoignable
                      else f"Polling timeout apres {max_duration_seconds}s")
            message = (
                f"Fin de polling sans statut terminal pour {payment_intent_pk} "
                f"(status={payment_intent.status}, raison={raison}) -- annulation Stripe"
            )
            # Un timeout est ordinaire : l'usager a pu renoncer devant la borne. Stripe
            # injoignable pendant deux minutes, non : c'est ce cas-la qu'on veut voir
            # remonter, et une seule fois.
            # / A timeout is routine (the user walked away); an unreachable Stripe is not.
            if stripe_injoignable:
                logger.error(message)
            else:
                logger.warning(message)

        # Sur un statut deja terminal cet appel ne fait rien (garde en tete de la
        # fonction) ; sur tous les autres chemins de sortie il annule reellement chez
        # Stripe avant qu'un ecran « Annule » ne parte vers la borne, et garantit un
        # statut terminal persiste en base.
        # / No-op on an already terminal status, real cancellation otherwise.
        cancel_payment_on_stripe(payment_intent)

        # Le statut lu chez Stripe decide de l'ecran, jamais la raison de la sortie de
        # boucle : une carte presentee juste avant l'annulation donne un vrai succes.
        # Persister ce statut compte autant que l'afficher -- c'est cet etat en base que
        # le websocket relit pour rejouer le bon ecran si la borne se reconnecte.
        # / The status read from Stripe decides the screen, never the exit reason.
        payment_is_succeeded = (payment_intent.status == PaymentsIntent.SUCCEEDED)
        push_screen_to_kiosk(
            payment_intent,
            'success.html' if payment_is_succeeded else 'cancel.html',
            retry_count,
        )
        return payment_is_succeeded

    except PaymentsIntent.DoesNotExist:
        logger.error(f"Payment intent with ID {payment_intent_pk} does not exist")
        return False
    except Exception as e:
        # logger.exception conserve la stacktrace : sans elle, une defaillance de
        # paiement n'est qu'une ligne de log sans contexte cote Sentry.
        # / logger.exception keeps the stacktrace, a bare logger.error loses it.
        logger.exception(f"Error polling payment intent status: {e}")

        # Une erreur inattendue ne doit pas laisser la borne sur le spinner. Mais ici
        # non plus on n'affiche pas « Annule » sans avoir annule : le lecteur peut
        # etre reste arme, et l'ecran mentirait sur un paiement encore encaissable.
        # / An unexpected error must not leave the kiosk stuck on the spinner — and
        # here too, no "canceled" screen without a real cancellation.
        if payment_intent is None or not room_name:
            return False

        try:
            cancel_payment_on_stripe(payment_intent)
        except Exception as erreur_annulation:
            logger.exception(f"Echec de l'annulation de secours pour {payment_intent_pk} -- {erreur_annulation}")

        push_screen_to_kiosk(
            payment_intent,
            'success.html' if payment_intent.status == PaymentsIntent.SUCCEEDED else 'cancel.html',
        )
        return False
