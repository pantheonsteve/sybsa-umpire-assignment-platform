from decimal import Decimal
from .models import PayRate


def get_pay_rate(is_patched, position):
    """
    Get the pay rate based on umpire status and position.
    """
    try:
        pay_rate = PayRate.objects.latest('effective_date')
    except PayRate.DoesNotExist:
        # Create default pay rates if none exist
        pay_rate = PayRate.objects.create()
    
    if position == 'solo':
        if is_patched:
            return pay_rate.solo_patched
        else:
            return pay_rate.solo_unpatched
    elif position == 'plate':
        if is_patched:
            return pay_rate.plate_patched
        else:
            return pay_rate.plate_unpatched
    elif position == 'base':
        # Base umpires are always unpatched
        return pay_rate.base_unpatched
    
    return Decimal('0.00')