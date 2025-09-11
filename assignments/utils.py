import re
from decimal import Decimal
from .models import PayRate


def format_phone_number(phone):
    """
    Format a phone number as (xxx)xxx-xxxx.
    Handles various input formats and cleans the number.
    """
    if not phone:
        return ''
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Handle different lengths
    if len(digits) == 10:
        # Format as (xxx)xxx-xxxx
        return f"({digits[:3]}){digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        # Remove leading 1 and format
        return f"({digits[1:4]}){digits[4:7]}-{digits[7:]}"
    else:
        # Return original if we can't format it properly
        return phone


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