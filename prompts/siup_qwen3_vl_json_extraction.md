# Short SIUP JSON Extraction Prompt for Qwen3 8B VL Instruct

The input document has already been classified as an Indonesian SIUP document.
Extract SIUP fields for downstream JSON consumption. Return only valid JSON. No markdown, no explanation.

Rules:
- Extract only visible text. Do not guess.
- Use `null` for missing, hidden, unreadable, or not applicable fields.
- Always set `"document_type": "siup"`.
- Keep printed values exactly in `raw`; put digits-only numbers in `digits`.
- SIUP may appear as older `Surat Izin Usaha Perdagangan (SIUP) Kecil/Menengah/Besar`
  or newer OSS `Izin Usaha (Surat Izin Usaha Perdagangan (SIUP))`.
- If multiple SIUP permits are visible, return multiple items in `siup_records`.
- Normalize dates to `YYYY-MM-DD` only when clear; otherwise use `null`.
- Split KBLI codes into an array when several codes are listed.
- Include warnings for blur, crop, rotation, low resolution, handwriting uncertainty, or conflicting text.

JSON schema/shape:

```json
{
  "document_type": "siup",
  "page_count_observed": null,
  "siup_records": [
    {
      "record_index": 1,
      "source_pages": [1],
      "permit": {
        "title": null,
        "category": "kecil | menengah | besar | unknown",
        "number": { "raw": null, "digits": null },
        "serial_number": null,
        "nib": { "raw": null, "digits": null },
        "project_number": null
      },
      "business": {
        "company_name": null,
        "entity_prefix": null,
        "owner_or_responsible_name": null,
        "responsible_position": null,
        "company_address": null,
        "business_location": null,
        "phone": null,
        "fax": null
      },
      "business_scope": {
        "institution_or_role": null,
        "net_worth_raw": null,
        "kbli_codes": [],
        "kbli_names": [],
        "main_goods_or_services": null
      },
      "issuer": {
        "government": null,
        "agency": null,
        "city_or_regency": null,
        "office_address": null
      },
      "dates": {
        "issued_place": null,
        "issued_date_raw": null,
        "issued_date_iso": null,
        "re_registration_date_raw": null,
        "re_registration_date_iso": null
      },
      "signatory": {
        "name": null,
        "title": null,
        "nip": { "raw": null, "digits": null }
      },
      "security": {
        "qr_code_visible": false,
        "stamp_visible": false,
        "signature_visible": false,
        "photo_visible": false
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
