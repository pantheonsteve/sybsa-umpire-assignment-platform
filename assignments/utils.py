import csv
import io
import re
from decimal import Decimal
from .models import PayRate


def strip_csv_reader(reader):
    """Strip leading/trailing whitespace from CSV column headers and cell values."""
    if reader.fieldnames:
        reader.fieldnames = [
            name.strip() if isinstance(name, str) else name
            for name in reader.fieldnames
        ]

    for row in reader:
        yield {
            (key.strip() if isinstance(key, str) else key): (
                value.strip() if isinstance(value, str) else value
            )
            for key, value in row.items()
        }


def read_csv_file(csv_file):
    """Decode an uploaded CSV file and return a row iterator with stripped values."""
    decoded_file = csv_file.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    return strip_csv_reader(csv.DictReader(io_string))


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