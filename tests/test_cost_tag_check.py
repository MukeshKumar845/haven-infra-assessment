"""
Write tests here proving:
  1. Happy path: running the check against fixtures/plan.json correctly flags the resources
     missing `landlord_account_id` (listing_media, mls_feed_sync) and passes the ones that
     have it (landlord_media[0], screening_report_export). The fixture also has a "no-op"
     entry and a "delete" entry with no `after` block at all — neither should appear in the
     output or crash the check.
  2. Idempotency: running the check twice against the same plan file produces the same
     result both times, with no duplicated output.

check_plan() takes a file path, not a dict — for a case that needs its own plan contents
instead of the shared fixture, write one with pytest's `tmp_path` rather than editing
fixtures/plan.json. You don't need to shell out to the real script for every case.
"""
import json
from pathlib import Path

import pytest

from scripts.cost_tag_check import check_plan


PLAN_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "plan.json"


def write_plan(tmp_path, plan):
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    return plan_path


def test_fixture_reports_only_resources_missing_landlord_account_tag(capsys):
    result = check_plan(str(PLAN_FIXTURE))

    assert result == 1
    output = capsys.readouterr().out
    assert output.splitlines() == [
        "Missing landlord_account_id tag: aws_lambda_function.mls_feed_sync",
        "Missing landlord_account_id tag: aws_s3_bucket.listing_media",
    ]
    assert "landlord_media[0]" not in output
    assert "screening_report_export" not in output
    assert "archive_media" not in output
    assert "decommissioned_media" not in output


def test_repeated_runs_have_identical_output_and_exit_code(capsys):
    first_result = check_plan(str(PLAN_FIXTURE))
    first_output = capsys.readouterr().out
    second_result = check_plan(str(PLAN_FIXTURE))
    second_output = capsys.readouterr().out

    assert first_result == second_result == 1
    assert first_output == second_output


def test_tagged_create_and_update_pass_and_delete_noop_are_ignored(tmp_path, capsys):
    plan_path = write_plan(
        tmp_path,
        {
            "resource_changes": [
                {
                    "address": "aws_s3_bucket.created",
                    "change": {
                        "actions": ["create"],
                        "after": {"tags": {"landlord_account_id": "la-001"}},
                    },
                },
                {
                    "address": "aws_lambda_function.updated",
                    "change": {
                        "actions": ["update"],
                        "after": {"tags": {"landlord_account_id": "la-002"}},
                    },
                },
                {
                    "address": "aws_s3_bucket.noop",
                    "change": {"actions": ["no-op"], "after": {"tags": {}}},
                },
                {
                    "address": "aws_s3_bucket.deleted",
                    "change": {"actions": ["delete"], "after": None},
                },
            ]
        },
    )

    assert check_plan(str(plan_path)) == 0
    assert capsys.readouterr().out == ""


def test_replacement_requires_tag(tmp_path, capsys):
    plan_path = write_plan(
        tmp_path,
        {
            "resource_changes": [
                {
                    "address": "aws_s3_bucket.replaced",
                    "change": {"actions": ["delete", "create"], "after": {"tags": {}}},
                }
            ]
        },
    )

    assert check_plan(str(plan_path)) == 1
    assert capsys.readouterr().out.splitlines() == [
        "Missing landlord_account_id tag: aws_s3_bucket.replaced"
    ]


@pytest.mark.parametrize("tags", [{}, {"tenant_id": "ten-001"}, {"landlord_account_id": ""}])
def test_missing_or_empty_account_tag_fails(tmp_path, capsys, tags):
    plan_path = write_plan(
        tmp_path,
        {
            "resource_changes": [
                {
                    "address": "aws_s3_bucket.untagged",
                    "change": {"actions": ["create"], "after": {"tags": tags}},
                }
            ]
        },
    )

    assert check_plan(str(plan_path)) == 1
    assert "aws_s3_bucket.untagged" in capsys.readouterr().out


def test_duplicate_missing_resource_address_is_reported_once(tmp_path, capsys):
    resource = {
        "address": "aws_s3_bucket.duplicate",
        "change": {"actions": ["create"], "after": {"tags": {}}},
    }
    plan_path = write_plan(tmp_path, {"resource_changes": [resource, resource]})

    assert check_plan(str(plan_path)) == 1
    assert capsys.readouterr().out.splitlines() == [
        "Missing landlord_account_id tag: aws_s3_bucket.duplicate"
    ]


def test_invalid_json_and_invalid_plan_shape_fail(tmp_path, capsys):
    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{", encoding="utf-8")
    assert check_plan(str(invalid_json)) == 1
    assert "Unable to read Terraform plan" in capsys.readouterr().err

    invalid_shape = write_plan(tmp_path, {"planned_values": {}})
    assert check_plan(str(invalid_shape)) == 1
    assert "resource_changes" in capsys.readouterr().err
