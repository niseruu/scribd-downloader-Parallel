# Short NPWP JSON Extraction Prompt for Qwen3 8B VL Instruct

The input document has already been classified as an Indonesian NPWP document/card.
Extract NPWP fields for downstream JSON consumption. Return only valid JSON. No markdown, no explanation.

Rules:
- Extract only visible text. Do not guess.
- Use `null` for missing, hidden, unreadable, or not applicable fields.
- Always set `"document_type": "npwp"`.
- Keep printed values exactly in `raw`; put digits-only numbers in `digits`.
- NPWP may be old format like `12.345.678.9-012.345` or new 16-digit grouped number.
- `NPWP16` is separate when printed. If printed as `-`, use `"raw": "-"` and `"digits": null`.
- Ignore KTP, selfie, and any non-NPWP documents. Extract NPWP fields only.
- If multiple NPWP cards/records are visible, return multiple items in `npwp_records`.
- Normalize dates to `YYYY-MM-DD` only when clear; otherwise use `null`.
- Taxpayer type: `individual`, `company`, or `unknown`.
- Company examples: PT, CV, UD, Yayasan, Koperasi, Firma.
- Include warnings for blur, crop, rotation, low resolution, conflicting text, or uncertain OCR.

JSON schema/shape:

```json
{
  "document_type": "npwp",
  "page_count_observed": null,
  "npwp_records": [
    {
      "record_index": 1,
      "source_pages": [1],
      "taxpayer": {
        "name": null,
        "type": "individual | company | unknown",
        "entity_prefix": null
      },
      "identifiers": {
        "npwp": { "raw": null, "digits": null },
        "npwp_16": { "raw": null, "digits": null },
        "nik": { "raw": null, "digits": null }
      },
      "address": {
        "raw": null,
        "rt": null,
        "rw": null,
        "village_or_kelurahan": null,
        "district_or_kecamatan": null,
        "city_or_regency": null,
        "province": null,
        "postal_code": null
      },
      "registration": {
        "date_raw": null,
        "date_iso": null
      },
      "issuing_office": {
        "kpp_name": null,
        "kpp_type": null
      },
      "card": {
        "front_visible": false,
        "back_visible": false,
        "qr_code_visible": false,
        "format_guess": "old_yellow_card | new_electronic_card | sixteen_digit_card | unknown"
      },
      "raw_visible_text": null,
      "confidence": 0.0
    }
  ],
  "quality": {
    "overall_readability": "good | medium | poor | unreadable",
    "blur_issue": false,
    "cropping_issue": false,
    "rotation_or_perspective_issue": false,
    "multiple_documents_detected": false
  },
  "warnings": []
}
```

Return real JSON values, not the enum text with `|`.
