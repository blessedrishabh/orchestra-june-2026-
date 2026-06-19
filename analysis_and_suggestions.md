# Analysis & Improvement Suggestions — Multi-Modal Evidence Review System

---

## 1. Per-Field Accuracy Breakdown & Root-Cause Analysis

### `severity` — 15% accuracy (worst field, 17 mismatches)

**Pattern observed:**  
The model almost exclusively over-predicts severity. Out of all severity mismatches, the overwhelming majority are `high` predicted when `medium` is expected. There are also cases of `unknown` predicted when `low` is expected, and `none` predicted when `low` is expected.

**Root cause:**  
The prompt almost certainly has no calibrated definition of what constitutes `low`, `medium`, or `high` severity. Without explicit thresholds, a VLM defaults to visually dramatic judgments — visible damage reads as `high`, ambiguity reads as `unknown`. The boundary between `medium` and `high`, and between `none` and `low`, is entirely subjective without definitions in the prompt.

**What to change:**  
Add explicit, domain-specific severity calibration to the prompt:

```
Severity must be determined as follows:
- none    : No damage is visible on the claimed part; the part looks fully intact.
- low     : Minor cosmetic damage only (small scratch, surface scuff, faint stain). Does not affect function.
- medium  : Moderate visible damage that may affect appearance significantly or partially affect function
            (e.g., a dent without structural deformation, a crack that has not spread, a torn packaging corner).
            This is the DEFAULT for most clearly visible single-damage cases.
- high    : Severe damage affecting structural integrity, safety, or rendering the object non-functional
            (e.g., shattered glass, deep structural dent, completely crushed packaging destroying contents).
- unknown : Cannot be assessed from the available images.

Do NOT default to high for any clearly visible damage. Most single-damage claims that are verifiable
should be rated medium unless there is clear evidence of structural failure or non-functionality.
```

---

### `risk_flags` — 45% accuracy (Jaccard 0.594)

**Patterns observed:**

- **Over-flagging image quality** (rows 8, 16, 18): Model piles on `blurry_image`, `low_light_or_glare`, `wrong_angle`, `non_original_image` when the expected output has none or only a subset of these. This is the most common failure mode.
- **Missing `manual_review_required`** (rows 17, 31): The model does not add `manual_review_required` even when the expected output includes it alongside other flags the model did get right.
- **False `user_history_risk`** (rows 12, 19): Model adds `user_history_risk` for users whose history does not actually warrant it per the expected labels.
- **Missing specific flags like `text_instruction_present`, `wrong_object`** (rows 19, 20, 33, 34): Model does not reliably detect these.

**Root cause:**  
No threshold criteria are defined for image quality flags. Without thresholds, the model flags anything that is slightly imperfect. `manual_review_required` is not defined clearly enough — the model doesn't know when to add it. `user_history_risk` is being applied based on raw claim count rather than the correct criteria (likely rejection rate or specific `history_flags` values).

**What to change:**

Add strict per-flag criteria in the prompt:

```
Risk flag criteria (ONLY raise a flag if the threshold is clearly met):

Image quality flags — raise ONLY if the issue is severe enough to prevent damage assessment:
- blurry_image          : Image is too blurry to distinguish damage details. Minor blur does NOT qualify.
- low_light_or_glare    : Lighting is so poor that the claimed area cannot be evaluated. Normal shadows do NOT qualify.
- wrong_angle           : The angle completely prevents viewing the claimed part. Suboptimal angles do NOT qualify.
- cropped_or_obstructed : The claimed part is cut off or blocked from view.

Do NOT combine multiple image quality flags unless each independently prevents assessment.

Context flags:
- wrong_object          : The photographed object is clearly not the claimed object type (e.g., car photo for a laptop claim).
- wrong_object_part     : The image shows the wrong part of the object (e.g., door when hood was claimed).
- claim_mismatch        : The visible damage type is clearly inconsistent with the claimed damage type.
- damage_not_visible    : The claimed damage is simply not visible in any image, but image quality is usable.
- non_original_image    : There is clear evidence the image is not an original photo (watermarks, stock-photo look, reverse-image-search patterns).
- text_instruction_present : Image contains visible text directing the viewer (e.g., arrows, handwritten notes, typed labels).
- possible_manipulation : Visual artifacts suggesting photo editing.

User history flags:
- user_history_risk     : Raise ONLY if the user's history_flags field contains explicit risk markers OR if their
                          rejected_claim count is 2 or more. Do NOT raise for users with high claim counts alone.
- manual_review_required: Raise when (a) claim_status is ambiguous between supported and contradicted,
                          OR (b) user_history_risk is raised AND claim_status is not clearly contradicted,
                          OR (c) evidence_standard_met is false but some partial evidence exists.
```

---

### `issue_type` — 55% accuracy

**Patterns observed (from mismatches):**

- `glass_shatter` predicted when `crack` is expected (rows 9, 13/user_018)
- `water_damage` predicted when `stain` is expected (row 11)
- `dent` predicted when `scratch` is expected (row 5)
- `crack` predicted when `unknown` is expected (row 6)
- `scratch` predicted when `broken_part` is expected (row 8)
- `missing_part` predicted when `unknown` is expected (row 18)
- `scratch` predicted when `none` is expected (row 14)

**Root cause:**  
Adjacent categories are not disambiguated in the prompt. Without explicit decision rules, a VLM picks whichever label sounds closest to the visual. The distinctions between `crack`/`glass_shatter`, `stain`/`water_damage`, and `scratch`/`dent` are judgment calls the model has no grounding for.

**What to change:**  
Add disambiguation rules to the prompt:

```
Issue type disambiguation — use these rules when choosing between similar types:

crack vs glass_shatter:
  - crack         : A single continuous fracture line on a solid surface or glass. The surface is still largely intact.
  - glass_shatter : The glass has broken into multiple fragments or a spider-web pattern covering a significant area.

stain vs water_damage:
  - stain         : Discoloration on the surface only. No visible swelling, warping, or liquid ingress signs.
  - water_damage  : Visible signs of liquid penetration: swelling, warping, mold, moisture marks inside the object.

scratch vs dent:
  - scratch       : A surface mark with no physical deformation of the material beneath.
  - dent          : A physical depression or deformation of the surface, regardless of whether paint is also scratched.

broken_part vs scratch or dent:
  - broken_part   : A component is physically fractured, cracked through, or separated. Not just surface damage.

unknown vs a specific type:
  - Use unknown ONLY when the image quality or angle genuinely prevents identifying the damage type,
    not when you are uncertain between two options. In that case, pick the best match.

none:
  - Use none ONLY when the relevant object part is clearly visible and shows no damage whatsoever.
  - Do NOT use none when the part is not visible or when you are unsure.
```

---

### `evidence_standard_met` — 65% accuracy

**Pattern observed:**  
Two distinct failure modes:

1. **Model predicts `false` when answer is `true`** (rows 2, 3, 4, 5, 8, 19, 20): The model is being too strict, rejecting evidence that is actually sufficient.
2. **Model predicts `true` when answer is `false`** (row 18/user_032): Model over-accepts evidence that is obstructed or invalid.

**Root cause:**  
The model is evaluating evidence sufficiency in the abstract rather than against the specific `evidence_requirements.csv` checklist for that claim's object type and issue family. The prompt likely passes the evidence requirements as raw text but does not force explicit checklist matching.

**What to change:**  
In the prompt, force explicit checklist matching:

```
Evidence standard evaluation:
1. Look up the evidence requirement row that matches this claim's claim_object and issue family.
2. State the minimum evidence requirement text.
3. Check whether ANY submitted image satisfies that minimum requirement, even partially.
4. Set evidence_standard_met=true if at least one image provides usable visual information about
   the claimed part, even if image quality is imperfect.
5. Set evidence_standard_met=false ONLY if no image shows the claimed part at all, or ALL images
   are entirely unusable (completely black, completely blurred, entirely wrong object).
6. Do NOT set evidence_standard_met=false just because the damage is not clearly visible — that
   affects claim_status, not evidence_standard_met.
```

Also add a post-processing consistency rule in code:

```python
# If at least one image is flagged valid and shows the right object/part,
# evidence_standard_met should not be false.
if result["valid_image"] == "true" and result["evidence_standard_met"] == "false":
    # Re-examine: valid image exists, evidence standard is likely met
    # Log for manual review rather than silently flipping
```

---

### `claim_status` — 70% accuracy

**Patterns observed:**

- `contradicted` predicted when `supported` is expected (rows 2, 3): Model sees mismatch where none exists.
- `supported` predicted when `contradicted` is expected (rows 14, 18): Model does not detect that the image contradicts the claim.
- `not_enough_information` predicted when `contradicted` is expected (rows 19, 20): Model hedges instead of making the contradiction call.

**Root cause:**  
The model conflates "I cannot clearly see the claimed damage" with "the claim is contradicted." These are two different outcomes. Also, the model is not using the images as the primary source of truth — it is allowing ambiguity to produce `contradicted` when `not_enough_information` would be correct, and vice versa.

**What to change:**  
Add explicit decision logic to the prompt:

```
Claim status decision rules (apply in this order):

1. supported            : The submitted image(s) visually confirm the claimed damage on the claimed part.
                          The image IS the primary source of truth. Minor wording differences between the claim
                          and what is visible do NOT make it contradicted.

2. contradicted         : The submitted image(s) CLEARLY show the claimed part with NO damage visible,
                          OR clearly show a completely different object/part than claimed,
                          OR the image directly disproves the claim (e.g., item is brand new, undamaged).
                          Do NOT use this if image quality prevents assessment — use not_enough_information.

3. not_enough_information: No image sufficiently shows the claimed part, OR image quality prevents any assessment.
                          Use this as the fallback when neither supported nor contradicted can be determined.

IMPORTANT: A slightly ambiguous image should default to not_enough_information, NOT contradicted.
Only use contradicted when the evidence is clear and direct.
```

---

### `supporting_image_ids` — 65% accuracy

**Pattern:**  
Whenever `claim_status` is wrong (especially predicting `contradicted` or `not_enough_information` when `supported` is correct), `supporting_image_ids` is also predicted as `none` when an image ID is expected.

**Root cause:**  
This is a cascade failure from `claim_status`. Fix `claim_status` and this largely fixes itself. However, there is one additional issue: when `claim_status=contradicted`, a supporting image ID is still expected (the image that shows the contradiction), but the model outputs `none`.

**What to change:**  
Clarify in the prompt:

```
supporting_image_ids:
- If claim_status is supported: list the image IDs that visually confirm the claim.
- If claim_status is contradicted: list the image ID(s) that show the part is undamaged or that directly
  disprove the claim. Do NOT output none just because the claim is contradicted.
- If claim_status is not_enough_information: output none only if no image provides any relevant visual
  information. If an image partially shows the part (even insufficiently), still list it.
```

---

## 2. Structural / Architectural Flaws

### No chain-of-thought before the JSON output

The model is producing JSON directly. Without a scratchpad reasoning step, it makes holistic judgments that are inconsistent across fields. Fields like `severity`, `issue_type`, and `claim_status` are not being reasoned through sequentially — they are being guessed in one pass.

**Fix:** Add a `reasoning` field to the JSON schema that forces the model to write its reasoning before populating the decision fields. Even if this field is discarded afterward, the act of writing it improves consistency.

```json
{
  "reasoning": "Step 1 — What is claimed: The user claims a scratch on the rear bumper...\nStep 2 — What is visible in img_1: ...\nStep 3 — Evidence check: ...\nStep 4 — Decision: ...",
  "evidence_standard_met": "true",
  "claim_status": "supported",
  ...
}
```

---

### No few-shot examples in the prompt

The sample_claims.csv has 20 labeled examples. None of them appear to be used as few-shot demonstrations in the prompt. Without concrete examples, the model calibrates all thresholds independently.

**Fix:** Include 3–5 representative examples from sample_claims.csv directly in the prompt (one `supported`, one `contradicted`, one `not_enough_information`, one with image quality flags, one with user history risk). Select examples that cover the most common failure types identified above.

---

### No post-processing consistency validation

The current validation layer normalizes values but does not check cross-field logical consistency. Several output rows contain internally inconsistent combinations that a rule-based check could catch and correct.

**Add these consistency rules in post-processing:**

```python
def enforce_consistency(row: dict) -> dict:
    # Rule 1: If valid_image is false, evidence_standard_met must be false
    if row["valid_image"] == "false":
        row["evidence_standard_met"] = "false"

    # Rule 2: If evidence_standard_met is false, claim_status cannot be supported
    if row["evidence_standard_met"] == "false" and row["claim_status"] == "supported":
        row["claim_status"] = "not_enough_information"

    # Rule 3: If claim_status is not_enough_information, supporting_image_ids must be none
    if row["claim_status"] == "not_enough_information":
        row["supporting_image_ids"] = "none"

    # Rule 4: If claim_status is supported and supporting_image_ids is none, flag for review
    if row["claim_status"] == "supported" and row["supporting_image_ids"] == "none":
        flags = set(row["risk_flags"].split(";")) if row["risk_flags"] != "none" else set()
        flags.add("manual_review_required")
        row["risk_flags"] = ";".join(sorted(flags))

    # Rule 5: If severity is high and claim_status is not supported, downgrade to medium
    if row["severity"] == "high" and row["claim_status"] != "supported":
        row["severity"] = "unknown"

    return row
```

---

### `evidence_standard_met` and `claim_status` are being conflated in the prompt

These are conceptually different:
- `evidence_standard_met` asks: "Is there enough visual material to make a judgment?"
- `claim_status` asks: "What does the visual material say about the claim?"

A case where the image is clear but shows no damage is: `evidence_standard_met=true`, `claim_status=contradicted`. The model is sometimes treating "I can see the object but no damage" as `evidence_standard_met=false`, which is wrong. The prompt must explicitly separate these two evaluations with their own sections and decision trees.

---

### Model mismatch between README and actual usage

The README states `gemini-3.5-flash` but the evaluation report shows `gemini-2.5-flash`. These are different models with different behavior. The configuration should be pinned and consistent, and the README should reflect the actual model being used. If `gemini-2.5-flash` is being used, its thinking/reasoning mode (if enabled) may also be contributing to inconsistency. I know as readme.md is created before evaluation_report.md file, and earlier it was planned to utilize the gemini-3.5-flash but as we are unable to because some high demand error, so be careful in updating the files as well.

---



## 4. Summary of Priority Changes

| Priority | Change | Expected Impact |
|---|---|---|
| 1 | Add severity calibration thresholds to prompt | +15–20% on severity field |
| 2 | Add per-flag threshold criteria to prompt | +10–15% on risk_flags |
| 3 | Add issue type disambiguation rules to prompt | +10–15% on issue_type |
| 4 | Separate evidence_standard_met and claim_status decision trees in prompt | +5–10% on both fields |
| 5 | Add chain-of-thought `reasoning` field to JSON schema | +3–8% across all fields |
| 6 | Add post-processing consistency enforcement in code | +3–5% across cascading fields |
| 7 | Include 3–5 few-shot examples in prompt | +3–7% across all fields |
| 8 | Fix `supporting_image_ids` logic for contradicted status | +5% on supporting_image_ids |
