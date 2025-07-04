import logging
import time
from datetime import datetime, timedelta

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.template.loader import get_template
from django.utils import timezone

from APIcashless.models import PaymentsIntent

logger = logging.getLogger(__name__)


@shared_task
def poll_payment_intent_status(payment_intent_pk, max_duration_seconds=120):
    """
    Poll the payment intent status every second for up to max_duration_seconds.
    Send WebSocket messages to update the frontend in real-time.
    Stop polling if the status is REQUIRES_PAYMENT_METHOD or if max_duration_seconds is reached.
    
    Args:
        payment_intent_pk: The ID of the PaymentsIntent to poll
        max_duration_seconds: Maximum duration in seconds to poll (default: 120 seconds)
    """
    time.sleep(1)

    logger.info(f"Starting to poll payment intent status for ID: {payment_intent_pk}")

    channel_layer = get_channel_layer()
    room_name = None

    start_time = timezone.now()
    end_time = start_time + timedelta(seconds=max_duration_seconds)

    try:
        payment_intent = PaymentsIntent.objects.get(pk=payment_intent_pk)
        room_name = payment_intent.payment_intent_stripe_id

        retry_count = 0
        while timezone.now() < end_time and payment_intent.status not in [PaymentsIntent.SUCCEEDED,
                                                                          PaymentsIntent.CANCELED]:
            # Get the current status from Stripe
            status = payment_intent.get_from_stripe()
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
        # Si le paiement est succes, on renvoi un template
        if payment_intent.status == PaymentsIntent.CANCELED:
            # Send the status update via WebSocket
            event = {
                'type': 'template',
                'template': 'cancel.html',
                'status': payment_intent.status,
                'status_display': payment_intent.get_status_display(),
                'timestamp': timezone.now().isoformat(),
                'retry_count': retry_count,
            }
            async_to_sync(channel_layer.group_send)(
                room_name,
                event
            )
            return True

        elif payment_intent.status == PaymentsIntent.SUCCEEDED:
            # Send the status update via WebSocket
            event = {
                'type': 'template',
                'template': 'success.html',
                'status': payment_intent.status,
                'status_display': payment_intent.get_status_display(),
                'timestamp': timezone.now().isoformat(),
                'retry_count': retry_count,
            }
            async_to_sync(channel_layer.group_send)(
                room_name,
                event
            )
            return True

    except PaymentsIntent.DoesNotExist:
        logger.error(f"Payment intent with ID {payment_intent_pk} does not exist")
    except Exception as e:
        logger.error(f"Error polling payment intent status: {e}")

    logger.error(f"Error intent with ID {payment_intent_pk} ended with no condition ?")
    raise Exception(f"Error intent with ID {payment_intent_pk} ended with no condition ?")