from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView, ListView

from formtools.wizard.views import SessionWizardView
from sagepaypi.conf import get_setting
from sagepaypi.forms import RegisterCardForm
from sagepaypi.gateway import SagepayGateway
from sagepaypi.models import Transaction, CardIdentifier, Customer

from example.forms import TransactionForm


class CustomerListView(ListView):
    template_name = 'example/customers.html'
    model = Customer


class CustomerPaymentView(SessionWizardView):
    form_list = [
        ('transaction', TransactionForm),
        ('card', RegisterCardForm),
    ]
    templates = {
        'transaction': 'example/forms/transaction.html',
        'card': 'example/forms/card.html',
    }

    def dispatch(self, request, *args, **kwargs):
        self.customer = self.get_customer()
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return [self.templates[self.steps.current]]

    def get_customer(self):
        return get_object_or_404(Customer, pk=self.kwargs['pk'])

    def done(self, form_list, form_dict, **kwargs):
        transaction = form_dict['transaction'].save(commit=False)

        card = form_dict['card'].cleaned_data
        gateway = SagepayGateway()
        new_identifier = gateway.create_card_identifier(
            card['card_holder_name'],
            card['card_number'],
            card['expiry_date'].strftime('%m%y'),
            card['security_code']
        )

        if not new_identifier:
            return self.render_goto_step('card')

        card_identifier = CardIdentifier.objects.create(
            customer=self.customer,
            merchant_session_key=new_identifier[0],
            card_identifier=new_identifier[1],
            card_identifier_expiry=new_identifier[2],
            card_type=new_identifier[3],
            last_four_digits=card['card_number'][-4:],
            expiry_date=card['expiry_date'].strftime('%m%y'),
            reusable=card['reusable']
        )

        # for new cards payment type is Payment
        transaction.type = 'Payment'
        transaction.card_identifier = card_identifier
        transaction.description = 'Payment for goods'
        transaction.save()

        transaction.submit_transaction()

        if transaction.requires_3d_secure:
            return render(
                self.request,
                'example/3d_secure_redirect.html',
                {'transaction': transaction}
            )

        transaction.refresh_from_db()
        tidb64, token = transaction.get_tokens()

        return HttpResponseRedirect(
            reverse(
                get_setting('POST_3D_SECURE_REDIRECT_URL'),
                kwargs={'tidb64': tidb64.decode('utf-8'), 'token': token}
            )
        )


class TransactionStatusView(DetailView):
    template_name = 'example/transaction_status.html'
    model = Transaction

    def get_object(self):
        tidb64 = self.kwargs['tidb64']
        token = self.kwargs['token']
        return Transaction.objects.get_for_token(tidb64, token)