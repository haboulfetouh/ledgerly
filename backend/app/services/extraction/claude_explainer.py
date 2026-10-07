"""Generates a one-or-two-sentence, plain-language explanation of an
already-computed match exception (PRD Section 10: "Exception Explanation
Generation" — informational only, grounded in the transaction's own data,
never itself authorizing any action). If generation fails for any reason,
callers must fall back to showing the raw discrepancy_detail rather than
blocking the workflow.
"""

from __future__ import annotations

import anthropic

from app.core.config import get_settings


def explain_exception(discrepancy_detail: str, fields: dict) -> str | None:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        response = client.messages.create(
            model=settings.anthropic_explanation_model,
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "An invoice-matching system flagged this exception. Write a "
                        "one or two sentence, plain-language explanation for an "
                        "Accounts Payable clerk, identifying the specific field, "
                        "expected value, and actual value. Do not suggest a resolution "
                        "or take any action — explain only.\n\n"
                        f"Discrepancy: {discrepancy_detail}\n"
                        f"Supporting data: {fields}"
                    ),
                }
            ],
        )
        return response.content[0].text.strip()
    except Exception:
        return None
