"""
Formatting utilities for report generation.
Provides consistent visual formatting across all report checks.
"""

def format_valid(is_valid: bool, message: str) -> str:
    """
    Format validation messages with colored indicators for better visibility.

    Args:
        is_valid: Boolean indicating if the check passed
        message: The original message string containing "**valid?**: True/False" or "**valid?** True/False"

    Returns:
        Formatted message with 🟢 PASS or 🔴 FAIL indicators

    Examples:
        >>> format_valid(True, "**valid?**: True, Revenue: $500M")
        "**🟢 PASS**, Revenue: $500M"

        >>> format_valid(False, "**valid?** False, P/E too high")
        "**🔴 FAIL**, P/E too high"
    """
    # Skip formatting for N/A or skipped checks
    if "N/A" in message or "Skipped" in message:
        return message

    indicator = "🟢 PASS" if is_valid else "🔴 FAIL"

    # Replace both formats: "**valid?**: True/False" and "**valid?** True/False"
    message = message.replace("**valid?**: True", f"**{indicator}**")
    message = message.replace("**valid?**: False", f"**{indicator}**")
    message = message.replace("**valid?** True", f"**{indicator}**")
    message = message.replace("**valid?** False", f"**{indicator}**")

    return message
