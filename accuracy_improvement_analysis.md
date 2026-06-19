# Accuracy Improvement Analysis

## 1. Prompt Design Problems

### 1.1 Too Many Tasks in One Prompt
The model is being asked to:
- Extract claim
- Detect issue type
- Detect object part
- Evaluate evidence sufficiency
- Determine claim status
- Determine severity
- Determine risk flags
- Evaluate user history
- Detect manipulation

This creates task interference.

### Recommended Change
Split reasoning into explicit stages inside the prompt:

1. Claim extraction
2. Object-part identification
3. Damage classification
4. Evidence sufficiency
5. Claim decision
6. Risk assessment
7. Severity assignment

Require the model to complete earlier stages before later stages.

---

### 1.2 User History Is Mixed Into Visual Analysis
User history is presented before final classification and risk assessment.

Observed errors:
- Missing `user_history_risk`
- Incorrect risk combinations
- Incorrect claim decisions influenced by history context

### Recommended Change
Move user history into a separate section used only for risk flag generation.

Explicitly state:

> User history must never influence issue_type, object_part, severity, valid_image, evidence_standard_met, or claim_status.

---

### 1.3 Evidence Standard Definition Is Too Loose

Current instruction:

> Set evidence_standard_met=true if at least one image provides usable visual information about the claimed part.

This causes:
- False positives for evidence_standard_met
- False positives for valid_image
- False supported decisions

Examples:
- Row 18
- Row 19

### Recommended Change

Replace with:

> evidence_standard_met=true only when the claimed object part is sufficiently visible to evaluate the existence or absence of the claimed damage.

and

> If the part cannot be inspected, evidence_standard_met=false.

---

### 1.4 Contradiction Rules Are Weak

Current prompt strongly favors:

> not_enough_information

Observed failure:
- Row 20
- Expected contradicted
- Predicted supported

### Recommended Change

Add:

> If the claimed part is clearly visible and no claimed damage exists, output:
>
> claim_status=contradicted
>
> issue_type=none
>
> severity=none

This should be treated separately from ambiguity cases.

---

## 2. Issue-Type Classification Problems

Issue-type accuracy is only 50%.

This is the largest accuracy bottleneck.

### 2.1 Weak Distinction Between Similar Classes

Observed failures:

| Predicted | Expected |
|------------|------------|
| crack | broken_part |
| glass_shatter | crack |
| water_damage | stain |
| dent | scratch |

### Recommended Change

Add a dedicated decision table:

| Class | Definition |
|---------|---------|
| scratch | Surface mark only |
| dent | Physical deformation without fracture |
| crack | Single visible fracture |
| glass_shatter | Multiple fracture lines/spider-web pattern |
| broken_part | Physical separation, breakage, missing structure |
| stain | Surface discoloration only |
| water_damage | Swelling, warping, liquid ingress evidence |

Require the model to select from this table before final output.

---

### 2.2 Missing Explicit Priority Rules

Models frequently over-predict:
- glass_shatter
- water_damage
- dent

### Recommended Change

Add:

> When uncertain between two issue types, choose the less severe category.

Examples:

- crack over glass_shatter
- stain over water_damage
- scratch over dent

This directly addresses Rows 3, 9, 11 and 13.

---

## 3. Object-Part Identification Problems

Object-part accuracy is 80%.

Observed failures:

- rear_bumper → body
- headlight → unknown
- trackpad → base
- front_bumper → hood

### Root Cause

The model is directly generating object_part without first localizing the claimed region.

### Recommended Change

Add an intermediate step:

1. Extract claimed part from conversation.
2. Verify whether that part is visible.
3. Only then output object_part.

Prompt addition:

> When the conversation explicitly names a part, prefer that part unless the image clearly disproves it.

---

## 4. Severity Problems

Severity accuracy is only 55%.

Observed failures:

- high instead of medium
- medium instead of low
- low instead of medium

### Root Cause

Current severity definitions are subjective.

### Recommended Change

Replace current definitions with:

| Severity | Rule |
|-----------|------|
| none | No damage visible |
| low | Small cosmetic damage |
| medium | Visible damage but object remains functional |
| high | Structural failure, shattered component, major breakage |
| unknown | Cannot determine |

Add:

> Do not assign high severity unless functionality is likely impaired.

This should reduce high→medium errors.

---

## 5. Risk Flag Problems

Risk flag accuracy is only 60%.

### 5.1 Missing Mandatory User-History Logic

Current prompt:

> ONLY if history_flags contains explicit risk markers or rejected_claim >= 2

Model often ignores this.

Observed failures:
- Row 5
- Row 17
- Row 20
- Row 33
- Row 34

### Recommended Change

Remove interpretation.

Use deterministic code after model output:

```python
if history_flags != "none" or rejected_claim >= 2:
    add("user_history_risk")
```

Do not leave this to the model.

---

### 5.2 Missing Mandatory Manual Review Logic

Observed repeatedly.

### Recommended Change

Move to deterministic post-processing:

```python
if (
    evidence_standard_met == "false"
    or "user_history_risk" in risk_flags
    or claim_status == "not_enough_information"
):
    add("manual_review_required")
```

Do not rely on the model.

---

### 5.3 Wrong-Object-Part Overprediction

Observed:

- wrong_object_part used where claim_mismatch expected

### Recommended Change

Prompt distinction:

> wrong_object_part = claimed part is not visible.
>
> claim_mismatch = visible damage exists but differs from the claimed damage.

---

## 6. Validation Layer Problems

### 6.1 High Severity Correction

Current code:

```python
if row["severity"] == "high" and row["claim_status"] != "supported":
    row["severity"] = "unknown"
```

This can overwrite valid predictions.

### Recommended Change

Remove this rule entirely.

Severity and claim_status should remain independent.

---

### 6.2 Supporting Image Removal

Current code:

```python
if row["claim_status"] == "not_enough_information":
    row["supporting_image_ids"] = "none"
```

Problem:

Expected labels sometimes preserve informative image IDs.

Observed:
- Row 19

### Recommended Change

Remove this rule.

Allow informative image references even when claim_status is not_enough_information.

---

## 7. Architecture Problem

### Single-Pass Prediction

Current system performs:

One prompt → All fields.

This creates correlated mistakes.

### Recommended Change

Use a two-stage pipeline.

Stage 1:
- object_part
- issue_type
- valid_image
- evidence_standard_met

Stage 2:
- claim_status
- severity
- risk_flags
- supporting_image_ids

Feed Stage 1 outputs into Stage 2.

This is the single change most likely to improve overall accuracy.

---

## Expected Impact

Largest gains are likely from:

1. Deterministic user_history_risk generation
2. Deterministic manual_review_required generation
3. Stronger issue-type decision table
4. Stricter evidence_standard_met definition
5. Two-stage inference pipeline
6. Removing supporting_image_ids suppression
7. Removing severity overwrite rule

Based on the current error distribution, most of the lost accuracy originates from:
- issue_type
- severity
- risk_flags

Improving those three fields should provide the largest overall score increase.
