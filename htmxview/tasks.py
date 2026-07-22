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

# Nombre d'erreurs Stripe consecutives tolerees pendant le polling.
# Le reseau d'un lieu peut hoqueter : une seule erreur ne doit pas faire tomber
# tout le paiement. Au-dela, on considere Stripe injoignable et on abandonne.
# / Consecutive Stripe errors tolerated while polling before giving up.
MAX_CONSECUTIVE_STRIPE_ERRORS = 5


def cancel_payment_on_stripe(payment_intent):
    """
    Annule l'action du lecteur ET l'intention de paiement chez Stripe, puis relit
    le statut reel pour le persister en base.
    / Cancels the reader action AND the payment intent on Stripe, then re-reads the
    real status to persist it.

    LOCALISATION : htmxview/tasks.py

    POURQUOI CETTE FONCTION EXISTE :
    aucun ecran « Annule » ne doit jamais partir vers la borne sans que cette
    annulation ait ete tentee. Tant que l'action du lecteur n'est pas annulee, le
    WisePOS reste ARME et accepte encore une carte : le paiement serait encaisse par
    Stripe et la carte creditee par Fedow (via son webhook), derriere un ecran qui
    affiche « Annule ». L'usager croit avoir echoue et recharge une seconde fois ;
    ou bien c'est le client SUIVANT qui tape sa carte et credite celle du precedent.
    Elle est donc appelee par TOUS les chemins de sortie non nominaux de
    `poll_payment_intent_status`.

    / No "canceled" screen may ever reach the kiosk without this cancellation having
    been attempted: an armed reader would still charge a late tap.

    Apres l'appel, `payment_intent.status` porte le statut reel connu de Stripe :
    l'appelant s'en sert pour choisir l'ecran. Si la carte a ete presentee juste
    avant l'annulation, le paiement a pu aboutir — c'est alors le succes qu'il faut
    afficher, jamais l'annulation.

    :param payment_intent: instance de PaymentsIntent a annuler
    """
    if settings.DEMO:
        # En DEMO il n'y a pas de Stripe a annuler : la fin du polling vaut annulation.
        # / No Stripe to cancel in DEMO: end of polling means cancellation.
        payment_intent.status = PaymentsIntent.CANCELED
        payment_intent.save()
        return

    config_stripe = ConfigurationStripe.get_solo()
    stripe.api_key = config_stripe.get_stripe_api()

    # Les deux annulations sont tentees SEPAREMENT : un lecteur qui ne repond plus ne
    # doit pas empecher l'annulation de l'intention de paiement.
    # / Cancel both sides separately: an unresponsive reader must not prevent the
    # payment intent cancellation.
    try:
        stripe.terminal.Reader.cancel_action(payment_intent.terminal.stripe_id)
    except Exception as erreur_lecteur:
        logger.error(
            f"Echec cancel_action sur le terminal {payment_intent.terminal.stripe_id} "
            f"pour {payment_intent.pk} -- {erreur_lecteur}"
        )
    try:
        stripe.PaymentIntent.cancel(payment_intent.payment_intent_stripe_id)
    except Exception as erreur_intention:
        logger.error(f"Echec PaymentIntent.cancel pour {payment_intent.pk} -- {erreur_intention}")

    # Stripe est le SEUL arbitre de ce qui a ete encaisse.
    # get_from_stripe() persiste le statut lu en base.
    # / Stripe is the only arbiter of what was charged.
    try:
        payment_intent.get_from_stripe()
    except Exception as erreur_relecture:
        logger.error(f"Echec de la relecture du statut pour {payment_intent.pk} -- {erreur_relecture}")


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

    LA BOUCLE S'ARRETE sur SUCCEEDED ou CANCELED, au bout de max_duration_seconds, ou
    apres MAX_CONSECUTIVE_STRIPE_ERRORS erreurs Stripe d'affilee.

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
            # Une coupure reseau d'une seconde ne doit pas faire sortir de la boucle :
            # sinon le paiement continue cote terminal pendant que plus personne ne
            # le surveille, et l'ecran de la borne reste fige sur le spinner.
            # / Guard the Stripe call per iteration: a one-second network glitch must
            # not abort the whole polling loop.
            try:
                status = payment_intent.get_from_stripe()
                consecutive_stripe_errors = 0
            except Exception as erreur_stripe:
                consecutive_stripe_errors += 1
                logger.error(
                    f"Payment intent {payment_intent_pk} : erreur Stripe "
                    f"{consecutive_stripe_errors}/{MAX_CONSECUTIVE_STRIPE_ERRORS} -- {erreur_stripe}"
                )
                if consecutive_stripe_errors >= MAX_CONSECUTIVE_STRIPE_ERRORS:
                    # Stripe est injoignable : on sort de la boucle. La suite de la
                    # fonction se charge d'annuler et d'afficher un ecran final.
                    # / Stripe unreachable: leave the loop, the code below cancels
                    # and shows a final screen.
                    break
                time.sleep(1)
                continue

            logger.info(f"Payment intent {payment_intent_pk} status: {payment_intent.get_status_display()}")

            # Send the status update via WebSocket
            event = {
                'type': 'message',
                'status': status,
                'status_display': payment_intent.get_status_display(),
                'timestamp': timezone.now().isoformat(),
                'retry_count': retry_count,
            }

            async_to_sync(channel_layer.group_send)(
                room_name,
                event
            )

            # Wait for 1 second before the next poll
            retry_count += 1
            time.sleep(1)

        logger.info(f"Finished polling payment intent status for ID: {payment_intent_pk}")

        # CAS 1 : le paiement est termine (succes ou annule) -> on pousse l'ecran final.
        # Rien a annuler chez Stripe : le statut est deja terminal.
        # / Payment finished (success or cancel) -> push the final screen.
        if payment_intent.status in [PaymentsIntent.CANCELED, PaymentsIntent.SUCCEEDED]:
            payment_is_succeeded = (payment_intent.status == PaymentsIntent.SUCCEEDED)
            event = {
                'type': 'template',
                'template': 'success.html' if payment_is_succeeded else 'cancel.html',
                'status': payment_intent.status,
                'status_display': payment_intent.get_status_display(),
                'timestamp': timezone.now().isoformat(),
                'retry_count': retry_count,
            }
            async_to_sync(channel_layer.group_send)(
                room_name,
                event
            )
            return payment_is_succeeded

        # CAS 2 : on sort de la boucle sans succes ni annulation (timeout, ou Stripe
        # injoignable). Le paiement n'est PAS termine pour autant : on annule
        # reellement chez Stripe avant d'afficher quoi que ce soit.
        # / Left the loop without a terminal status: really cancel on Stripe before
        # showing anything.
        logger.warning(
            f"Fin de polling sans statut terminal pour {payment_intent_pk} "
            f"(status={payment_intent.status}) apres {max_duration_seconds}s max -- annulation Stripe"
        )
        cancel_payment_on_stripe(payment_intent)

        # Le statut lu chez Stripe decide de l'ecran, jamais la raison de la sortie de
        # boucle : une carte presentee juste avant l'annulation donne un vrai succes.
        # Persister ce statut compte autant que l'afficher — c'est cet etat en base que
        # le websocket relit pour rejouer le bon ecran si la borne se reconnecte.
        # / The status read from Stripe decides the screen, never the exit reason.
        payment_is_succeeded = (payment_intent.status == PaymentsIntent.SUCCEEDED)
        event = {
            'type': 'template',
            'template': 'success.html' if payment_is_succeeded else 'cancel.html',
            'status': payment_intent.status,
            'status_display': payment_intent.get_status_display(),
            'timestamp': timezone.now().isoformat(),
            'retry_count': retry_count,
        }
        async_to_sync(channel_layer.group_send)(
            room_name,
            event
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

        try:
            async_to_sync(channel_layer.group_send)(
                room_name,
                {
                    'type': 'template',
                    'template': 'success.html' if payment_intent.status == PaymentsIntent.SUCCEEDED else 'cancel.html',
                    'status': payment_intent.status,
                    'status_display': payment_intent.get_status_display(),
                    'timestamp': timezone.now().isoformat(),
                }
            )
        except Exception as erreur_websocket:
            logger.error(f"Echec de l'envoi de l'ecran final sur {room_name} -- {erreur_websocket}")
        return False
