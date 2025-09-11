from django import template
import re

register = template.Library()

@register.filter
def format_phone(phone):
    """
    Format a phone number as (xxx)xxx-xxxx.
    Handles various input formats and cleans the number.
    """
    if not phone:
        return ''
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', str(phone))
    
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