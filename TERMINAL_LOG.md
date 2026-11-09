# Terminal Log

All commands ran from the repository root unless marked with `-chdir=terraform`. Python 3.13.11 and Terraform 1.11.3 meet the assignment minimums (Python 3.10+, Terraform 1.7+).

## Setup

```text
$ python3.13 --version
Python 3.13.11

$ python3.13 -m venv .venv
(no output; virtual environment created at .venv)

$ .venv/bin/python -m pip install -r requirements.txt
Successfully installed pytest-9.2.0 in .venv

$ .venv/bin/python -m pytest --version
pytest 9.2.0

$ terraform version
Terraform v1.11.3
on darwin_arm64

$ terraform -chdir=terraform init
Initializing the backend...
Initializing provider plugins...
- Installing hashicorp/aws v5.100.0...
- Installed hashicorp/aws v5.100.0 (signed by HashiCorp)
Terraform has been successfully initialized!
```

## B0 plan reproduction

Removed the middle account by overriding the list for this plan; `variables.tf` and the seeded state were not edited. `-refresh=false` compares configuration to the supplied state without refreshing against AWS.

```text
$ terraform -chdir=terraform plan -refresh=false -no-color -var='landlord_accounts=["la-001","la-003","la-004"]'
# aws_s3_bucket.landlord_media[1] must be replaced
# aws_s3_bucket.landlord_media[2] must be replaced
# aws_s3_bucket.landlord_media[3] will be destroyed (index [3] is out of range for count)
Plan: 4 to add, 0 to change, 3 to destroy.
Exit code: 0
```

The other planned creates are `listing_media` and its lifecycle configuration, which are not present in the seeded state.

## B2 access-control tests

```text
$ .venv/bin/python -m pytest -v tests/test_access_control.py
============================= test session starts ==============================
platform darwin -- Python 3.13.11, pytest-9.2.0, pluggy-1.7.0 -- .venv/bin/python
collecting ... collected 8 items
tests/test_access_control.py::test_manager_cannot_access_other_landlord_account_report PASSED
tests/test_access_control.py::test_manager_can_access_own_landlord_account_report PASSED
tests/test_access_control.py::test_missing_tenant_denies_access PASSED
tests/test_access_control.py::test_missing_property_denies_access PASSED
tests/test_access_control.py::test_tenant_with_unknown_property_denies_access PASSED
tests/test_access_control.py::test_duplicate_tenant_ids_deny_ambiguous_access PASSED
tests/test_access_control.py::test_duplicate_property_ids_deny_ambiguous_access PASSED
tests/test_access_control.py::test_missing_ids_deny_access PASSED
============================== 8 passed in 0.03s ===============================
Exit code: 0
```

## B2 cost-tag tests

```text
$ .venv/bin/python -m pytest -v tests/test_cost_tag_check.py
============================= test session starts ==============================
platform darwin -- Python 3.13.11, pytest-9.2.0, pluggy-1.7.0 -- .venv/bin/python
collecting ... collected 9 items
tests/test_cost_tag_check.py::test_fixture_reports_only_resources_missing_landlord_account_tag PASSED
tests/test_cost_tag_check.py::test_repeated_runs_have_identical_output_and_exit_code PASSED
tests/test_cost_tag_check.py::test_tagged_create_and_update_pass_and_delete_noop_are_ignored PASSED
tests/test_cost_tag_check.py::test_replacement_requires_tag PASSED
tests/test_cost_tag_check.py::test_missing_or_empty_account_tag_fails[tags0] PASSED
tests/test_cost_tag_check.py::test_missing_or_empty_account_tag_fails[tags1] PASSED
tests/test_cost_tag_check.py::test_missing_or_empty_account_tag_fails[tags2] PASSED
tests/test_cost_tag_check.py::test_duplicate_missing_resource_address_is_reported_once PASSED
tests/test_cost_tag_check.py::test_invalid_json_and_invalid_plan_shape_fail PASSED
============================== 9 passed in 0.04s ===============================
Exit code: 0
```

## Cost-tag checker run 1

```text
$ .venv/bin/python scripts/cost_tag_check.py fixtures/plan.json
Missing landlord_account_id tag: aws_lambda_function.mls_feed_sync
Missing landlord_account_id tag: aws_s3_bucket.listing_media
Exit code: 1 (expected: fixture contains missing billing tags)
```

## Cost-tag checker run 2

```text
$ .venv/bin/python scripts/cost_tag_check.py fixtures/plan.json
Missing landlord_account_id tag: aws_lambda_function.mls_feed_sync
Missing landlord_account_id tag: aws_s3_bucket.listing_media
Exit code: 1 (same output and exit code as run 1)
```
