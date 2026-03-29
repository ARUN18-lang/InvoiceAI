import logging

from openai import AsyncOpenAI

from app.core.config import Settings
from app.schemas.invoice import ParsedInvoiceFields

logger = logging.getLogger(__name__)

MAX_CHARS_FOR_LLM = 120_000

SYSTEM_PROMPT = """You are an expert invoice digitization assistant.
Extract structured data from the raw text of an invoice or bill.
Use null for unknown fields. Dates must be ISO 8601 date strings (YYYY-MM-DD).
Classify expense_category into exactly one of:
utilities, travel, office_supplies, software_subscriptions, vendor_payments, other.
Set category_confidence between 0 and 1.
Infer detected_language from the document (e.g. en, hi, kn).
Currency default INR if the document suggests India; otherwise infer from symbols/text.
For Indian GST invoices, when line-level tax is visible, populate per line when possible:
taxable_value, gst_rate_pct (combined rate e.g. 18), cgst_amount, sgst_amount, igst_amount, cess_amount.
Use IGST for inter-state; CGST+SGST (roughly equal) for intra-state. Leave null if not shown.
"""


class InvoiceLLMService:
    """Uses OpenAI structured parsing to turn OCR/markdown text into invoice fields."""

    def __init__(self, client: AsyncOpenAI, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def parse_from_text(self, raw_text: str) -> ParsedInvoiceFields:
        trimmed = raw_text if len(raw_text) <= MAX_CHARS_FOR_LLM else raw_text[:MAX_CHARS_FOR_LLM]
        completion = await self._client.chat.completions.parse(
            model=self._settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Extract invoice fields from this document text:\n\n{trimmed}",
                },
            ],
            response_format=ParsedInvoiceFields,
        )
        choice = completion.choices[0]
        parsed = choice.message.parsed
        if parsed is None:
            raise ValueError("OpenAI returned no parsed invoice structure")
        return parsed
