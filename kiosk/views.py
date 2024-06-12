from decimal import Decimal

from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect, HttpResponse
from django.utils import timezone
from requests import Response

from rest_framework import viewsets, permissions,status
from rest_framework.decorators import action

from APIcashless.models import CarteCashless
from kiosk.serializers import CardSerializer
from kiosk.validators import AmountValidator, CardValidator, BillValidator
from kiosk.models import ScannedNfcCard, Payment




# First page
def index(request):
    last_scanned = ScannedNfcCard.objects.all().order_by('created_at').last()
    if last_scanned:
        # Check if the last card has been scaned the last 2 seconds
        if last_scanned.created_at >= timezone.now() - timezone.timedelta(seconds=2):
            return render(request, 'kiosk_pages/send_card.html'
                          , {'tag_id': last_scanned.card.tag_id})

    return render(request, 'kiosk_pages/first_page.html')

class CardViewset(viewsets.ViewSet):
    # The permission might be used in different methods, but not all
    permission_classes = []
    # save scanded card:
    @action(detail=False, methods=['POST'], permission_classes=[permissions.AllowAny])
    def save_scaned_card(self, request):
        # Look if the card that is being scaned exist in the DB
        validator = CardValidator(data=request.data)
        # check if the scaned card doesn't exist or is unvalid
        if not validator.is_valid():
            message = "Card error, please try again!"
            return render(request, 'kiosk_pages/first_page.html',
                          {'message': message})

        # Saving the card that is being scaned
        card: CarteCashless = validator.validated_data.get('tag_id')
        ScannedNfcCard.objects.create(card=card)
        return HttpResponse('Card saved: ')


    # post from card scan /
    @action(detail=False, methods=['POST'])
    def scan(self, request):
        card_data = CardValidator(data=request.data)
        # check if the scaned card doesn't exist or is unvalid
        if not card_data.is_valid():
            message = "Card error, please try again!"
            return render(request, 'kiosk_pages/first_page.html',
                          {'message': message})

        card: CarteCashless = card_data.validated_data.get('tag_id')
        return render(request,
                      'kiosk_pages/show.html',
                      {'card': card})


    # On this part we gather the total of amount selected
    @action(detail=False, methods=['POST'])
    def recharge(self,request):
        selected_data = AmountValidator(data=request.data)
        # If it happens that the tag_id or the total is wrong
        if not selected_data.is_valid():
            message = "Error, please try again! "

            return render(request, 'kiosk_pages/first_page.html',
                          {'message':message})

        card: CarteCashless = selected_data.validated_data.get('tag_id')
        total0: Decimal = selected_data.validated_data.get('total')
        total = str((total0))
        return render(request,
        'kiosk_pages/recharge.html',
        {'total':total, 'card': card})


    # post from paiment
    @action(detail=False, methods=['POST'])
    def paiment(self, request):
        choosed_data = AmountValidator(data=request.data)
        # check if the datas are well selected
        if not choosed_data.is_valid():
            messages.add_message(request, messages.WARNING,
                                 "Wrong selection, please try again")
            return HttpResponseRedirect('/kiosk')

        card: CarteCashless = choosed_data.validated_data.get('tag_id')
        total: Decimal = choosed_data.validated_data.get('total')
        paiment_choice = Payment.objects.create(amount=total, card=card)
        context = {'card': card, 'total': total, 'paiment_choice': paiment_choice}

        return render(request, 'paiment/paiement.html', context=context)


    # Amoount of bills recived from the device
    @action(detail=False, methods=['GET'])
    def return_device(self,request):
        paiment_complete = False
        paiment_choice = Payment.objects.all().order_by('created_at').last()
        rest = paiment_choice.amount - paiment_choice.device_amount
        if rest <= 0:
            paiment_complete = True
            rest_device = False
            if rest < 0:
                rest_device = True
                rest = paiment_choice.device_amount - paiment_choice.amount
            return render(request,
            'paiment/device_bills.html',
            {'paiment_complete': paiment_complete,
             'rest_device': rest_device, 'rest': rest})
        return render(request,
        'paiment/device_bills.html',
    {'paiment_choice': paiment_choice,
        'paiment_complete':paiment_complete,'rest': rest})

    # verify bill reciving
    @action(detail=False, methods=['POST'])
    def devices_bills(self, request):
        paiment_choice = Payment.objects.all().order_by('created_at').last()
        bill_data = BillValidator(data=request.data)
        if not bill_data.is_valid():
            message = ("Sorry error device, please take your bill from the device "
                       "and, restart again")
            return render(request, 'kiosk_pages/first_page.html',)

        amount_device = bill_data.validated_data.get('bill')
        paiment_choice.device_amount += amount_device
        paiment_choice.save()
        # A vérifier si HttpResponse(paiment_choise) c'est
        # le bon retour ...
        return HttpResponse(paiment_choice)



    @action(detail=False, methods=['POST'])
    def confirmation_paiment(self, request):
        confirmation_data = AmountValidator(data=request.data)
        # check if the datas are well selected
        if not confirmation_data.is_valid():
            message = ("Error, of payment, please take the money from the device"
                       "and try again!")

            return render(request, 'paiment/error_paiment.html',
                          {'message': message})

        card: CarteCashless = confirmation_data.validated_data.get('uuid')
        total: Decimal = confirmation_data.validated_data.get('total')
        device_confirm_paiment = confirmation_data.validated_data.get('device_confirm_paiment')

        """
        if device_confirm_paiment != None:
            card = Card.objects.get(uuid=uuid)
            card.amount += int(total)
            card.save()
            return render(request, 'paiment/confirmation_paiement.html', {'card': card})
        """

        message = ("Error, of payment, please take the money from the device"
                   "and try again!")

        return render(request, 'paiment/error_paiment.html',
                      {'message': message})


# This method will recharge paiment page
def recharge_paiment_pg(request):
    uuid = request.POST.get('uuid')
    total = request.POST.get('total')
    choice_amount = request.POST.get('choice_amount')
    devic_amount = request.POST.get('devic_amount')
    context = {'uuid': uuid, 'total': total,
               'choice_amount': choice_amount, 'devic_amount': devic_amount}
    return render(request, 'paiment/recharge_paiment_pg.html', context=context)


# # recharging value
# def recharge(request):
#     if request.method == 'GET':
#         total = request.GET.get('total')
#         uuid = request.GET.get('uuid')
#
#         return render(request,
#                       'kiosk_pages/recharge.html',
#                       {'total': total, 'uuid': uuid})


# Stripe ----------------
def stripe_paiment(request):
    return render(request, 'paiment/stripe_paiment.html')
