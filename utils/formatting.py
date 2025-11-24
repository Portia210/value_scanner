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
    """
    # Skip formatting for N/A or skipped checks
    if "N/A" in message or "Skipped" in message:
        return message

    # Emoji outside bold for better markdown rendering
    emoji = "🟢" if is_valid else "🔴"
    indicator = f"{emoji} **PASS**" if is_valid else f"{emoji} **FAIL**"

    # Replace both formats: "**valid?**: True/False" and "**valid?** True/False"
    message = message.replace(f"**valid?**: {is_valid}", indicator)
    message = message.replace(f"**valid?** {is_valid}", indicator)

    return message
