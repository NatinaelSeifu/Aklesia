from datetime import datetime, date
from ethiopian_date import EthiopianDateConverter

AMHARIC_MONTHS = {
    1: "መስከረም", 2: "ጥቅምት", 3: "ህዳር", 
    4: "ታህሳስ", 5: "ጥር", 6: "የካቲት",
    7: "መጋቢት", 8: "ሚያዝያ", 9: "ግንቦት", 
    10: "ሰኔ", 11: "ሐምሌ", 12: "ነሐሴ", 
    13: "ጳጉሜ"
}

AMHARIC_DAYS = {
    0: "ሰኞ", 1: "ማክሰኞ", 2: "ረቡዕ", 
    3: "ሐሙስ", 4: "ዓርብ", 5: "ቅዳሜ", 6: "እሑድ"
}

def to_ethiopian(dt):
    """Convert Gregorian date to Ethiopian date string (DD/MM/YYYY)"""
    if isinstance(dt, str):
        dt = datetime.strptime(dt, '%Y-%m-%d').date()
    eth_date = EthiopianDateConverter.to_ethiopian(dt.year, dt.month, dt.day)
    return f"{eth_date[2]}/{eth_date[1]}/{eth_date[0]}"

def format_ethiopian_date(dt):
    """Format as Ethiopian date with month name (e.g., 12 መስከረም 2015)"""
    if isinstance(dt, str):
        dt = datetime.strptime(dt, '%Y-%m-%d').date()
    eth_date = EthiopianDateConverter.to_ethiopian(dt.year, dt.month, dt.day)
    return f"{eth_date[2]} {AMHARIC_MONTHS[eth_date[1]]} {eth_date[0]}"

def ethiopian_day_name(dt):
    """Get Amharic day name"""
    if isinstance(dt, str):
        dt = datetime.strptime(dt, '%Y-%m-%d').date()
    return AMHARIC_DAYS[dt.weekday()]

# def ethiopian_to_gregorian(eth_year, eth_month, eth_day):
#     """Convert Ethiopian date to Gregorian date"""
#     return EthiopianDateConverter.to_gregorian(eth_year, eth_month, eth_day)

def ethiopian_to_gregorian(eth_dt):
    """Convert Ethiopian date string (YYYY-MM-DD) to Gregorian date object"""
    if isinstance(eth_dt, str):
        year, month, day = map(int, eth_dt.split('-'))
        greg_date = EthiopianDateConverter.to_gregorian(year, month, day)
        return greg_date
    elif isinstance(eth_dt, (tuple, list)) and len(eth_dt) == 3:
        # Assume input is (year, month, day)
        year, month, day = eth_dt
        return EthiopianDateConverter.to_gregorian(year, month, day)
    else:
        raise ValueError("Input must be string in YYYY-MM-DD format or (year, month, day) tuple")
    
    