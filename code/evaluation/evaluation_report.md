# Evaluation Report

## Per-Field Accuracy

| Field | Accuracy | Correct | Total |
|---|---|---|---|
| `evidence_standard_met` | **90.0%** | 18 | 20 |
| `claim_status` | **85.0%** | 17 | 20 |
| `issue_type` | **50.0%** | 10 | 20 |
| `object_part` | **80.0%** | 16 | 20 |
| `valid_image` | **90.0%** | 18 | 20 |
| `severity` | **55.0%** | 11 | 20 |
| `risk_flags` | **60.0%** | 12 | 20 |
| `supporting_image_ids` | **75.0%** | 15 | 20 |

**Overall Mean Accuracy: 73.1%**

**Weighted Accuracy: 73.1%**

## Set-Field Jaccard Similarity

- **`risk_flags`**: 0.648
- **`supporting_image_ids`**: 0.775

## Detailed Mismatches

### Row 2 — `user_002`
- **risk_flags**: predicted `wrong_object` vs expected `none` (Jaccard 0.00)

### Row 3 — `user_004`
- **severity**: predicted `high` vs expected `medium`

### Row 4 — `user_007`
- **issue_type**: predicted `crack` vs expected `broken_part`

### Row 5 — `user_005`
- **issue_type**: predicted `dent` vs expected `scratch`
- **object_part**: predicted `body` vs expected `rear_bumper`
- **risk_flags**: predicted `damage_not_visible;wrong_object_part` vs expected `claim_mismatch;manual_review_required;user_history_risk` (Jaccard 0.00)

### Row 6 — `user_006`
- **object_part**: predicted `unknown` vs expected `headlight`

### Row 8 — `user_008`
- **issue_type**: predicted `crushed_packaging` vs expected `broken_part`
- **object_part**: predicted `hood` vs expected `front_bumper`
- **valid_image**: predicted `true` vs expected `false`
- **severity**: predicted `unknown` vs expected `high`
- **risk_flags**: predicted `claim_mismatch;possible_manipulation;wrong_object_part` vs expected `claim_mismatch;manual_review_required;non_original_image;user_history_risk` (Jaccard 0.17)
- **supporting_image_ids**: predicted `none` vs expected `img_1` (Jaccard 0.00)

### Row 9 — `user_009`
- **issue_type**: predicted `glass_shatter` vs expected `crack`
- **severity**: predicted `high` vs expected `medium`

### Row 11 — `user_011`
- **issue_type**: predicted `water_damage` vs expected `stain`
- **severity**: predicted `low` vs expected `medium`

### Row 12 — `user_012`
- **severity**: predicted `medium` vs expected `low`

### Row 13 — `user_018`
- **issue_type**: predicted `glass_shatter` vs expected `crack`
- **severity**: predicted `high` vs expected `medium`

### Row 14 — `user_020`
- **claim_status**: predicted `not_enough_information` vs expected `contradicted`
- **issue_type**: predicted `scratch` vs expected `none`
- **object_part**: predicted `base` vs expected `trackpad`
- **severity**: predicted `low` vs expected `none`
- **risk_flags**: predicted `none` vs expected `damage_not_visible;manual_review_required;user_history_risk` (Jaccard 0.00)
- **supporting_image_ids**: predicted `none` vs expected `img_1` (Jaccard 0.00)

### Row 17 — `user_031`
- **risk_flags**: predicted `none` vs expected `manual_review_required;user_history_risk` (Jaccard 0.00)

### Row 18 — `user_032`
- **evidence_standard_met**: predicted `true` vs expected `false`
- **claim_status**: predicted `supported` vs expected `not_enough_information`
- **issue_type**: predicted `missing_part` vs expected `unknown`
- **valid_image**: predicted `true` vs expected `false`
- **risk_flags**: predicted `none` vs expected `cropped_or_obstructed;damage_not_visible;manual_review_required` (Jaccard 0.00)
- **supporting_image_ids**: predicted `img_1` vs expected `none` (Jaccard 0.00)

### Row 19 — `user_033`
- **evidence_standard_met**: predicted `false` vs expected `true`
- **issue_type**: predicted `none` vs expected `unknown`
- **severity**: predicted `none` vs expected `low`
- **risk_flags**: predicted `claim_mismatch;wrong_object;wrong_object_part` vs expected `claim_mismatch;manual_review_required;user_history_risk;wrong_object` (Jaccard 0.40)
- **supporting_image_ids**: predicted `none` vs expected `img_1` (Jaccard 0.00)

### Row 20 — `user_034`
- **claim_status**: predicted `supported` vs expected `contradicted`
- **issue_type**: predicted `torn_packaging` vs expected `none`
- **severity**: predicted `medium` vs expected `none`
- **risk_flags**: predicted `possible_manipulation;text_instruction_present;user_history_risk` vs expected `damage_not_visible;manual_review_required;text_instruction_present;user_history_risk` (Jaccard 0.40)
- **supporting_image_ids**: predicted `img_1` vs expected `img_1;img_2` (Jaccard 0.50)

## Operational Analysis

- **Model**: meta-llama/llama-4-scout-17b-16e-instruct
- **Model calls (sample set)**: 20
- **Input tokens**: ~69,719
- **Output tokens**: ~4,514
- **Images processed**: 29
- **Runtime**: 216.9s (3.6m)

### Full test-set cost projection

- **Test claims**: 45 rows
- **Estimated model calls**: 45 (one per claim)
- **Estimated input tokens**: ~156,867
- **Estimated output tokens**: ~10,156
- **Cost**: $0.00 (Groq free tier)
- **Estimated runtime**: ~488s

### Rate-limit & efficiency strategy

- 2.0 s delay between API calls (well within 60 RPM free-tier limit)
- One VLM call per claim (all images sent together)
- Key Rotation (automatically rotates through GROQ_API_KEYS)
- Model Rotation (automatically rotates through working models on 429 errors)
- JSON response mode avoids output parsing failures
- Low temperature (0.1) for deterministic outputs
