import pytest


@pytest.fixture(autouse=True)
def _paypal_eteint(_paypal_au_grand_livre):
    """The ledger as at launch: PayPal off (finance 0006). A money account in use must be reconciled every day."""
    from apps.finance.models import CompteArgentModel, MoyenPaiementModel

    CompteArgentModel.objects.filter(code='PAYPAL').update(actif=False)
    MoyenPaiementModel.objects.filter(code='PAYPAL').update(actif=False)
