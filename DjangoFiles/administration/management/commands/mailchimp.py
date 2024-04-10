from django.core.management.base import BaseCommand
from datetime import timedelta, datetime
import os
from APIcashless.models import Membre

import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError


class Command(BaseCommand):
    def handle(self, *args, **options):
        mailchimpClient = MailchimpMarketing.Client()
        mailchimpClient.set_config({
            "api_key": os.environ.get('MAILCHIMP_API_KEY'),
            "server": os.environ.get('MAILCHIMP_SERVER_LOCATION')
        })

        # response = mailchimpClient.lists.get_list_members_info(os.environ.get('MAILCHIMP_API_LIST'))

        for membre in Membre.objects.filter(date_ajout__gte=(datetime.now() - timedelta(days=7))):
            if membre.email:
                try:
                    FNAME = ' '.join(membre.name.split(' ')[1:])
                    LNAME = membre.name.split(' ')[0]
                except Exception as e:
                    FNAME = ""
                    LNAME = membre.name

                print(FNAME)
                print(LNAME)

                try:
                    response = mailchimpClient.lists.add_list_member(os.environ.get('MAILCHIMP_API_LIST'),
                                                                     {"email_address": membre.email,
                                                                      "status": "subscribed",
                                                                      'merge_fields': {
                                                                          'FNAME': FNAME,
                                                                          'LNAME': LNAME,
                                                                      },
                                                                      })
                    print(response['status'])
                except ApiClientError as error:
                    print("Error: {}".format(error.text))
