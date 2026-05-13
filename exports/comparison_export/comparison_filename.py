from datetime import datetime

def generate_comparison_filename():
    """Generates COMPARISON_REPORT_<DATE>.xlsx"""
    now = datetime.now()
    date_str = now.strftime("%d_%b_%Y").upper()
    return f"COMPARISON_REPORT_{date_str}.xlsx"
