import io
import pandas as pd
from exports.common.utils import sanitize_for_excel
from exports.report_generation_export.report_formatting import apply_report_formatting

def export_business_report_excel(df: pd.DataFrame) -> bytes:
    """
    Export single DataFrame to an openpyxl-formatted Excel workbook for the Report Generation Module.
    """
    output = io.BytesIO()
    safe_df = sanitize_for_excel(df)
    
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        safe_df.to_excel(writer, index=False, sheet_name="Report")
        workbook = writer.book
        apply_report_formatting(workbook["Report"], safe_df)
        
        workbook.properties.title = "Business Output Report"
        workbook.properties.subject = "Generated from MBOM"
        workbook.properties.creator = "FCS Report Generator"
        
    return output.getvalue()
