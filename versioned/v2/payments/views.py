from payments.views import TipPayments
from stargramz.models import Stargramrequest


class TipPaymentsV2(TipPayments):

    def query_check(self, request, customer):
        booking, celebrity = Stargramrequest.objects.values_list('id', 'celebrity').get(id=request.data['booking'])
        return booking, celebrity
