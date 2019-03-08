from datetime import timedelta
import dateutil
import mock

from sagepaypi.exceptions import InvalidTransactionStatus
from sagepaypi.models import Transaction

from tests.mocks import void_instruction_transaction
from tests.test_case import AppTestCase


class TestVoidTransaction(AppTestCase):
    fixtures = ['tests/fixtures/test']

    def test_error__no_transaction_id(self):
        transaction = Transaction.objects.get(pk='ec87ac03-7c34-472c-823b-1950da3568e6')

        with self.assertRaises(InvalidTransactionStatus) as e:
            transaction.void()

        self.assertEqual(
            e.exception.args[0],
            'transaction is missing a transaction_id'
        )

    def test_error__not_successful(self):
        transaction = Transaction.objects.get(pk='ec87ac03-7c34-472c-823b-1950da3568e6')
        transaction.transaction_id = 'dummy-transaction-id'
        transaction.type = 'Payment'
        transaction.status_code = '9999'

        with self.assertRaises(InvalidTransactionStatus) as e:
            transaction.void()

        self.assertEqual(
            e.exception.args[0],
            'cannot void an unsuccessful transaction'
        )

    def test_error__invalid_type(self):
        transaction = Transaction.objects.get(pk='ec87ac03-7c34-472c-823b-1950da3568e6')
        transaction.transaction_id = 'dummy-transaction-id'
        transaction.status_code = '0000'

        for tr_type in ['Deferred', 'Repeat']:
            transaction.type = tr_type

            with self.assertRaises(InvalidTransactionStatus) as e:
                transaction.void()

            self.assertEqual(
                e.exception.args[0],
                'can only void a payment or refund'
            )

    def test_error__instruction_too_late(self):
        transaction = Transaction.objects.get(pk='ec87ac03-7c34-472c-823b-1950da3568e6')
        transaction.transaction_id = 'dummy-transaction-id'
        transaction.type = 'Payment'
        transaction.status_code = '0000'
        transaction.created_at = transaction.utc_now() - timedelta(days=1)

        with self.assertRaises(InvalidTransactionStatus) as e:
            transaction.void()

        self.assertEqual(
            e.exception.args[0],
            'can only void transaction that was created today'
        )

    @mock.patch('sagepaypi.gateway.requests.post', side_effect=void_instruction_transaction)
    def test_successful_instruction(self, mock_post):
        transaction = Transaction.objects.get(pk='ec87ac03-7c34-472c-823b-1950da3568e6')
        transaction.transaction_id = 'dummy-transaction-id'
        transaction.type = 'Payment'
        transaction.status_code = '0000'
        transaction.created_at = transaction.utc_now()

        transaction.void()

        json = mock_post().json()

        # expected
        self.assertEqual(transaction.instruction, json['instructionType'])
        self.assertEqual(transaction.instruction_created_at, dateutil.parser.parse(json['date']))