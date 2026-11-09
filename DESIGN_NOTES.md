# Design Notes

## B2 — idempotency key

State exactly what key your `cost_tag_check.py` uses to decide whether two resources in the
same run are "the same" for dedup purposes, and why running it twice against an unchanged
plan file produces identical output and exit code without the script keeping any record
between runs. Use the word "idempotency" in your explanation.

The check uses each Terraform resource `address` as the idempotency key when deduplicating
missing-tag findings within a plan. It reads the plan without changing it and prints the unique
findings in sorted order, so the same unchanged plan produces the same output and exit code on
every run without storing state between runs.

## Any other decision with a non-obvious alternative

1. **Inspect Terraform plan JSON instead of parsing HCL.** The check needs the values Terraform
   will actually apply, including evaluated variables, module instances, and resource actions.
   Static HCL analysis would have to recreate Terraform's evaluation and expansion rules and
   could miss the final tags. `fixtures/plan.json` shows the `terraform show -json` structure the
   checker consumes: `resource_changes`, each change's `actions`, and the planned
   `change.after.tags`. The fixture also makes it possible to check creates, updates, no-ops, and
   deletes using the same input shape as a real plan.

2. **Traverse the ownership relationship instead of checking a report attribute.** A screening
   report has a `tenant_id`, not a `landlord_account_id`. The authorization check follows
   report → tenant → property, then compares the property's `landlord_account_id` with the
   property manager's account ID. This enforces the billing and access boundary from the domain
   model. If the tenant or property is missing or ambiguous, access is denied.

3. **Check only changes that can create or modify resources, and fail closed on missing tags.**
   No-op and delete-only changes do not introduce a resource configuration, so they are skipped;
   creates, updates, and replacements must have a nonempty `landlord_account_id` in their planned
   `after.tags`. A tenant-specific tag such as `tenant_id` is not enough because the landlord
   account is the platform's billing unit. Findings are deduplicated by resource address and
   sorted so the result stays stable for an unchanged plan.
