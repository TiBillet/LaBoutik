from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect, HttpResponse
from django.utils import timezone

from rest_framework import viewsets
from rest_framework.decorators import action

from APIcashless.models import CarteCashless
from kiosk.serializers import CardSerializer
from kiosk.validators import AmountValidator, CardValidator
from kiosk.models import ScannedNfcCard, Payment



# saving the scanned data:
@csrf_exempt
def saving_scanned_card(request):
    if request.method == 'POST':
        card = get_object_or_404(CarteCashless, tag_id=request.POST['scanded_tag_id'])
        ScannedNfcCard.objects.create(card=card)
        return HttpResponse('ok')


@csrf_exempt
def given_bill(request):
    print('____________________')
    if request.method == 'POST':
        given_bill = request.POST.get('bill')

    print("Given Bill: ", given_bill)
    return HttpResponse(given_bill)

# First page
def index(request):
    return render(request, 'kiosk_pages/first_page.html')


def index_bis(request):
    render_repetly = render(request, 'kiosk_pages/first_page.html',
            {})

    # Avoid non existence of object ScannedNfcCard
    try:
        last_scanned = ScannedNfcCard.objects.all().order_by('created_at').last()
    except ScannedNfcCard.DoesNotExist:
        return render_repetly

    # Check if the last card has been scaned the last 2 seconds
    if last_scanned.created_at >= timezone.now() - timezone.timedelta(seconds=2):
        return render(request, 'kiosk_pages/send_card.html'
                ,{'tag_id':last_scanned.reeded_card})

    return render(request, 'kiosk_pages/first_page_bis.html')



class CardViewset(viewsets.ViewSet):
    # post from card scan /
    @action(detail=False, methods=['POST'])
    def scan(self, request):
        card_data = CardValidator(data=request.data)
        # check if the scaned card doesn't exist or is unvalid
        if not card_data.is_valid():
            message = "Card error, please try again!"

            return render(request, 'kiosk_pages/first_page.html',
                          {'message':message})

        card_number = card_data.validated_data.get('tag_id')
        card_obj = Card.objects.get(tag_id=card_number)
        card_serialized = CardSerializer(card_obj, many=False)
        card = card_serialized.data
        return render(request,
                      'kiosk_pages/show.html',
                      {'card': card})


    # post from paiment
    @action(detail=False, methods=['POST'])
    def paiment(self, request):
        choosed_data = AmouuntValidator(data=request.data)
        # check if the datas are well selected
        if not choosed_data.is_valid():
            messages.add_message(request, messages.WARNING,
            "Wrong selection, please try again")
            return HttpResponseRedirect('/')
        uuid = choosed_data.validated_data.get('uuid')
        total = choosed_data.validated_data.get('total')
        card = Card.objects.get(uuid=uuid)
        paiment_choice = Paiment_choice.objects.create(choice_amount=total,card_uuid=card)
        context = {'uuid': uuid, 'total': total, 'paiment_choice': paiment_choice}
        return render(request, 'paiment/paiement.html', context=context)


    @action(detail=False, methods=['POST'])
    def confirmation_paiment(self, request):
        confirmation_data = AmouuntValidator(data=request.data)
        # check if the datas are well selected
        if not confirmation_data.is_valid():
            message = ("Error, of payment, please take the money from the device"
                       "and try again!")

            return render(request, 'paiment/error_paiment.html',
                          {'message':message})

        uuid = confirmation_data.validated_data.get('uuid')
        total = confirmation_data.validated_data.get('total')
        device_confirm_paiment = confirmation_data.validated_data.get('device_confirm_paiment')
        if device_confirm_paiment != None:
            card = Card.objects.get(uuid=uuid)
            card.amount += int(total)
            card.save()
            return render(request, 'paiment/confirmation_paiement.html',{'card': card})

        message = ("Error, of payment, please take the money from the device"
                       "and try again!")

        return render(request, 'paiment/error_paiment.html',
                          {'message':message})


# This method will recharge paiment page
def recharge_paiment_pg(request):
    uuid = request.POST.get('uuid')
    total = request.POST.get('total')
    choice_amount = request.POST.get('choice_amount')
    devic_amount = request.POST.get('devic_amount')
    context = {'uuid': uuid, 'total': total,
               'choice_amount': choice_amount, 'devic_amount': devic_amount}
    return render(request, 'paiment/recharge_paiment_pg.html',context=context)



# recharging value
def recharge(request):
    if request.method == 'GET':
        total = request.GET.get('total')
        uuid = request.GET.get('uuid')
    return render(request,
    'kiosk_pages/recharge.html',
    {'total':total, 'uuid': uuid})


# Stripe ----------------
def stripe_paiment(request):
    return render(request, 'paiment/stripe_paiment.html')


