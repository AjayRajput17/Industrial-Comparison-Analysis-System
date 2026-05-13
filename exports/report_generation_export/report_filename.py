from datetime import datetime

def generate_report_filename():
    """Generates TORQUE_REPORT_<DATE>.xlsx"""
    now = datetime.now()
    date_str = now.strftime("%d_%b_%Y").upper()
    return f"TORQUE_REPORT_{date_str}.xlsx"
