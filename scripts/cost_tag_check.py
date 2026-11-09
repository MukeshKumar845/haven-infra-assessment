"""
B2, part 2 — implement the cost-tagging check.

Read fixtures/plan.json for the shape of a `terraform show -json` plan: a `resource_changes`
list, where each entry has a `type`, an `address`, and `change.after.tags`.

Implement check_plan() so it:
  - Looks at every resource being created or updated (skip anything whose change.actions
    isn't "create" or "update" — a "no-op"/"read" change, or a "delete" with no `after`
    block at all).
  - Fails (returns a non-zero exit code) if the resource is missing the tag that identifies
    the real billing unit, per README.md's domain model — not whatever tag the resource
    happens to already carry.
  - Is idempotent: running this twice against the same plan file produces the same result,
    with no duplicate output and no flipped pass/fail. This is about a single run being
    stable and repeatable — it does not require remembering anything between runs.
  - Prints which specific resource address(es) are missing the tag.

Run manually: python scripts/cost_tag_check.py fixtures/plan.json
"""
import json
import sys
from pathlib import Path


def check_plan(plan_path: str) -> int:
    """
    Returns an exit code: 0 if every resource being created or updated has
    `landlord_account_id`, non-zero otherwise.
    """
    try:
        with Path(plan_path).open(encoding="utf-8") as plan_file:
            plan = json.load(plan_file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Unable to read Terraform plan {plan_path!r}: {error}", file=sys.stderr)
        return 1

    resource_changes = plan.get("resource_changes") if isinstance(plan, dict) else None
    if not isinstance(resource_changes, list):
        print("Invalid Terraform plan: 'resource_changes' must be a list.", file=sys.stderr)
        return 1

    missing_addresses = set()
    for index, resource in enumerate(resource_changes):
        if not isinstance(resource, dict):
            print(
                f"Invalid Terraform plan: resource_changes[{index}] must be an object.",
                file=sys.stderr,
            )
            return 1

        change = resource.get("change")
        if not isinstance(change, dict):
            print(
                f"Invalid Terraform plan: resource_changes[{index}].change must be an object.",
                file=sys.stderr,
            )
            return 1

        actions = change.get("actions", [])
        if not isinstance(actions, list):
            print(
                f"Invalid Terraform plan: resource_changes[{index}].change.actions must be a list.",
                file=sys.stderr,
            )
            return 1
        if any(not isinstance(action, str) for action in actions):
            print(
                f"Invalid Terraform plan: resource_changes[{index}].change.actions "
                "must contain only strings.",
                file=sys.stderr,
            )
            return 1

        # A replacement includes a create action, so it must carry the tag too.
        if not {"create", "update"}.intersection(actions):
            continue

        address = resource.get("address")
        if not isinstance(address, str) or not address:
            address = f"<resource_changes[{index}]>"

        after = change.get("after")
        tags = after.get("tags") if isinstance(after, dict) else None
        landlord_account_id = tags.get("landlord_account_id") if isinstance(tags, dict) else None
        if not isinstance(landlord_account_id, str) or not landlord_account_id.strip():
            missing_addresses.add(address)

    if missing_addresses:
        for address in sorted(missing_addresses):
            print(f"Missing landlord_account_id tag: {address}")
        return 1

    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <terraform-plan.json>", file=sys.stderr)
        sys.exit(2)
    sys.exit(check_plan(sys.argv[1]))
