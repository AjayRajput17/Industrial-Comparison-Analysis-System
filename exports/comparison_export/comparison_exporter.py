import io
import pandas as pd
from exports.common.utils import sanitize_for_excel
from exports.comparison_export.comparison_formatting import apply_comparison_formatting

def export_comparison_excel(nochange: pd.DataFrame, modified: pd.DataFrame, new: pd.DataFrame, removed: pd.DataFrame) -> bytes:
    """
    Export 4 DataFrames to an openpyxl-formatted Excel workbook for the Comparison Module.
    """
    output = io.BytesIO()

    safe_nochange = sanitize_for_excel(nochange)
    safe_modified = sanitize_for_excel(modified)
    safe_new      = sanitize_for_excel(new)
    safe_removed  = sanitize_for_excel(removed)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        safe_nochange.to_excel(writer, index=False, sheet_name="No Change")
        safe_modified.to_excel(writer, index=False, sheet_name="Modified")
        safe_new.to_excel(writer, index=False, sheet_name="New")
        safe_removed.to_excel(writer, index=False, sheet_name="Deleted")
        
        workbook = writer.book
        
        # Set Tab Colors
        workbook["No Change"].sheet_properties.tabColor = "A6A6A6"
        workbook["Modified"].sheet_properties.tabColor = "FFC000"
        workbook["New"].sheet_properties.tabColor = "70AD47"
        workbook["Deleted"].sheet_properties.tabColor = "FF0000"
        
        # Apply standard formatting strictly through isolated formatting module
        apply_comparison_formatting(workbook["No Change"], safe_nochange)
        apply_comparison_formatting(workbook["Modified"], safe_modified)
        apply_comparison_formatting(workbook["New"], safe_new)
        apply_comparison_formatting(workbook["Deleted"], safe_removed)
        
        # document properties
        workbook.properties.title = "Industrial Comparison Report"
        workbook.properties.subject = "Part Comparison Analysis"
        workbook.properties.creator = "FCS Analysis System"

    return output.getvalue()
