import csv

rows = list(csv.DictReader(open('../output.csv', 'r', encoding='utf-8')))
print(f"Total rows: {len(rows)}")

fallbacks = []
for i, r in enumerate(rows):
    reason = r.get('evidence_standard_met_reason', '')
    justification = r.get('claim_status_justification', '')
    status = r.get('claim_status', '')
    issue = r.get('issue_type', '')
    
    is_fallback = (
        'error' in reason.lower() or
        'unable' in justification.lower() or
        'processing error' in reason.lower() or
        'processing error' in justification.lower() or
        (status == 'not_enough_information' and issue == 'unknown' and r.get('severity') == 'unknown' and r.get('object_part') == 'unknown')
    )
    
    if is_fallback:
        fallbacks.append((i+1, r))

print(f"\nFailed/Fallback claims: {len(fallbacks)}")
print("=" * 80)
for idx, r in fallbacks:
    print(f"\nRow {idx}: {r['user_id']} ({r['claim_object']})")
    print(f"  Status: {r['claim_status']}")
    print(f"  Issue: {r['issue_type']} | Part: {r['object_part']} | Severity: {r['severity']}")
    print(f"  Reason: {r['evidence_standard_met_reason'][:100]}")
    print(f"  Justification: {r['claim_status_justification'][:100]}")
    print(f"  Images: {r['image_paths'][:80]}")

print(f"\nSuccessful claims: {len(rows) - len(fallbacks)}")
