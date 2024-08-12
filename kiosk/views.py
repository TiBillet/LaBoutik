from decimal import Decimal

from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect, HttpResponse
from django.utils import timezone
from requests import Response

from rest_framework import viewsets, permissions,status
from rest_framework.decorators import action

import Cashless
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
            return HttpResponse(status=404)#, "Card error, please try again!")

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
            return render(request, 'kiosk_pages/card_error.html',
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
        total: Decimal = str(selected_data.validated_data.get('total'))
        Payment.objects.create(card=card,amount=total)
        return render(request,
        'kiosk_pages/recharge.html',
        {'total':total, 'card': card})


class DeviceViewset(viewsets.ViewSet):
    permission_classes = []
    # Open device:
    @action(detail=False, methods=['POST'], permission_classes=[permissions.AllowAny])
    def device_on(self, request):
        choosed_data = AmountValidator(data=request.data)
        # check if the datas are well selected
        if not choosed_data.is_valid():
            messages.add_message(request, messages.WARNING,
                                 "Wrong selection, please try again")
            return HttpResponseRedirect('/kiosk')

        card: CarteCashless = choosed_data.validated_data.get('tag_id')
        total0: Decimal = choosed_data.validated_data.get('total')

        total = str((total0))

        return render(request, 'paiment/prepare_device.html'
                    ,{'card': card, 'total': total})


    # Check if the device is open
    @action(detail=False, methods=['POST'])
    def is_device_open(self, request):
        choosed_data = AmountValidator(data=request.data)
        # check if the datas are well selected
        if not choosed_data.is_valid():
            messages.add_message(request, messages.WARNING,
                                 "Wrong selection, please try again")
            return HttpResponseRedirect('/kiosk')

        card: CarteCashless = choosed_data.validated_data.get('tag_id')
        total0: Decimal = choosed_data.validated_data.get('total')
        total=str((total0))
        # Extract the last payment from the card tag_id
        paiment_choice = Payment.objects.filter(card=card).order_by('created_at').last()
        import random
        x = random.randint(1, 5)
        if x == 1:
            print("The Device is not open yet")
            return render(request, 'paiment/prepare_device.html'
                    ,{'card': card, 'total': total})
        print('The Device is open')
        return render(request, 'paiment/paiment.html'
                ,{'card': card, 'paiment_choice': paiment_choice})


    @action(detail=False, methods=['POST'])
    # the page with the bill payment
    def paiment(self, request):
        test = request.POST.get('tag_id')
        print(test)
        card_data = CardValidator(data=request.data)

        # choosed_data = AmountValidator(data=request.data)
        # check if the datas are well selected
        if not card_data.is_valid():
            messages.add_message(request, messages.WARNING,
                                 "Wrong selection, please try again")
            return HttpResponseRedirect('/kiosk')

        card: CarteCashless = card_data.validated_data.get('tag_id')
        paiment_complete = False
        paiment_choice = Payment.objects.filter(card=card).order_by('created_at').last()
        # Calculate the rest and send it
        rest = paiment_choice.amount - paiment_choice.device_amount
        if rest <= 0:
            paiment_complete = True
            rest_device = False
            if rest < 0:
                rest_device = True
                rest = paiment_choice.device_amount - paiment_choice.amount
            return render(request,
            'paiment/paiment.html',
            {'paiment_complete': paiment_complete, 'paiment_choice':paiment_choice,
             'rest_device': rest_device, 'rest': rest, 'card': card})
        return render(request,
        'paiment/paiment.html',
    {'paiment_choice': paiment_choice, 'paiment_choice':paiment_choice,
        'paiment_complete':paiment_complete,'rest': rest, 'card': card})


    # verify bill reciving
    @action(detail=False, methods=['POST'])#, permission_classes=[permissions.AllowAny])
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
    def completed(self, request):
        card_data = CardValidator(data=request.data)
        if not card_data.is_valid():
            messages.add_message(request, messages.WARNING,
                                 "Wrong selection, please try again")
            return HttpResponseRedirect('/kiosk')
        card: CarteCashless = card_data.validated_data.get('tag_id')
        print("_____________")

        return render(request, 'paiment/confirmation_paiement.html'
                      ,{'card': card})



# Stripe ----------------
def stripe_paiment(request):
    return render(request, 'paiment/stripe_paiment.html')
