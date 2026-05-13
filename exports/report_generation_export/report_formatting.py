from exports.common.base_formatting import apply_base_formatting

def apply_report_formatting(worksheet, dataframe):
    """
    Applies formatting specific to the Report Generation Export module.
    It builds on the base formatting.
    """
    apply_base_formatting(worksheet, dataframe)
    # Additional report-specific formatting can go here in the future
