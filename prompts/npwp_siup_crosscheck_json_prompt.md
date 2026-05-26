# NPWP vs SIUP Crosscheck Prompt

You receive two JSON objects from upstream extractors:
- `npwp_json`, already classified/extracted from an NPWP document
- `siup_json`, already classified/extracted from a SIUP document

Crosscheck whether both documents appear to belong to the same business/taxpayer.
Return only valid JSON. No markdown, no explanation.

Rules:
- Compare only fields present in the input JSON. Do not invent missing values.
- Use fuzzy matching for names and addresses: ignore case, punctuation, repeated spaces,
  legal prefixes in different positions, and common abbreviations such as `JL`/`JALAN`.
- A missing field is `not_available`, not a mismatch.
- NPWP number, SIUP number, NIB, KBLI, and KPP usually do not directly match each other.
- Strongest checks are business/name and address. Dates and issuing regions are only supporting checks.

Crosscheck field map:

```json
[
  {
    "check_name": "business_or_taxpayer_name",
    "importance": "high",
    "npwp_paths": ["npwp_records[].taxpayer.name"],
    "siup_paths": ["siup_records[].business.company_name", "siup_records[].business.owner_or_responsible_name"],
    "match_type": "fuzzy_text"
  },
  {
    "check_name": "entity_prefix",
    "importance": "medium",
    "npwp_paths": ["npwp_records[].taxpayer.entity_prefix"],
    "siup_paths": ["siup_records[].business.entity_prefix"],
    "match_type": "exact_or_null"
  },
  {
    "check_name": "taxpayer_or_business_type",
    "importance": "medium",
    "npwp_paths": ["npwp_records[].taxpayer.type"],
    "siup_paths": ["siup_records[].business.company_name", "siup_records[].business.entity_prefix"],
    "match_type": "inferred"
  },
  {
    "check_name": "registered_or_company_address",
    "importance": "high",
    "npwp_paths": ["npwp_records[].address.raw"],
    "siup_paths": ["siup_records[].business.company_address", "siup_records[].business.business_location"],
    "match_type": "fuzzy_address"
  },
  {
    "check_name": "city_or_regency",
    "importance": "medium",
    "npwp_paths": ["npwp_records[].address.city_or_regency"],
    "siup_paths": ["siup_records[].business.company_address", "siup_records[].business.business_location", "siup_records[].issuer.city_or_regency"],
    "match_type": "substring_or_fuzzy"
  },
  {
    "check_name": "province",
    "importance": "medium",
    "npwp_paths": ["npwp_records[].address.province"],
    "siup_paths": ["siup_records[].business.company_address", "siup_records[].business.business_location"],
    "match_type": "substring_or_fuzzy"
  },
  {
    "check_name": "postal_code",
    "importance": "low",
    "npwp_paths": ["npwp_records[].address.postal_code"],
    "siup_paths": ["siup_records[].business.company_address", "siup_records[].business.business_location"],
    "match_type": "exact_digits"
  },
  {
    "check_name": "date_plausibility",
    "importance": "low",
    "npwp_paths": ["npwp_records[].registration.date_iso"],
    "siup_paths": ["siup_records[].dates.issued_date_iso"],
    "match_type": "npwp_date_should_not_be_after_siup_date"
  }
]
```

Output JSON shape:

```json
{
  "document_pair": {
    "left_document_type": "npwp",
    "right_document_type": "siup"
  },
  "overall_result": {
    "status": "match | partial_match | mismatch | insufficient_data",
    "confidence": 0.0,
    "summary": null
  },
  "checks": [
    {
      "check_name": "business_or_taxpayer_name",
      "importance": "high",
      "npwp_path": null,
      "siup_path": null,
      "npwp_value": null,
      "siup_value": null,
      "result": "match | partial_match | mismatch | not_available",
      "confidence": 0.0,
      "reason": null
    }
  ],
  "matched_record_pairs": [
    {
      "npwp_record_index": 1,
      "siup_record_index": 1,
      "status": "match | partial_match | mismatch | insufficient_data",
      "confidence": 0.0
    }
  ],
  "critical_mismatches": [],
  "warnings": []
}
```

Return real JSON values, not the enum text with `|`.
