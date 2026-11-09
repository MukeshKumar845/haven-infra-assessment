"""
Write tests here proving:
  1. A PropertyManager scoped to la-001 (pm-001) is DENIED access to la-002's tenant's
     screening report (rep-002).
  2. The same PropertyManager (pm-001) IS allowed access to their own account's screening
     report (rep-001).

Use the `property_managers`, `properties`, `tenants`, and `screening_reports` fixtures from
conftest.py — don't re-invent the seed data here.
"""
from app.models import Property, ScreeningReport, Tenant
from app.access_control import can_access_screening_report


def test_manager_cannot_access_other_landlord_account_report(
    property_managers, properties, tenants, screening_reports
):
    assert can_access_screening_report(
        property_managers[0],
        screening_reports[1],
        properties=properties,
        tenants=tenants,
    ) is False


def test_manager_can_access_own_landlord_account_report(
    property_managers, properties, tenants, screening_reports
):
    assert can_access_screening_report(
        property_managers[0],
        screening_reports[0],
        properties=properties,
        tenants=tenants,
    ) is True


def test_missing_tenant_denies_access(property_managers, properties, screening_reports):
    assert can_access_screening_report(
        property_managers[0], screening_reports[0], properties=properties, tenants=[]
    ) is False


def test_missing_property_denies_access(property_managers, screening_reports, tenants):
    assert can_access_screening_report(
        property_managers[0], screening_reports[0], properties=[], tenants=tenants
    ) is False


def test_tenant_with_unknown_property_denies_access(property_managers, screening_reports):
    orphan_tenant = Tenant(id="ten-001", name="J. Alvarez", property_id="missing")
    assert can_access_screening_report(
        property_managers[0],
        screening_reports[0],
        properties=[],
        tenants=[orphan_tenant],
    ) is False


def test_duplicate_tenant_ids_deny_ambiguous_access(
    property_managers, properties, screening_reports
):
    duplicate_tenants = [
        Tenant(id="ten-001", name="J. Alvarez", property_id="prop-001"),
        Tenant(id="ten-001", name="J. Alvarez duplicate", property_id="prop-002"),
    ]
    assert can_access_screening_report(
        property_managers[0],
        screening_reports[0],
        properties=properties,
        tenants=duplicate_tenants,
    ) is False


def test_duplicate_property_ids_deny_ambiguous_access(
    property_managers, properties, tenants, screening_reports
):
    duplicate_properties = properties + [
        Property(id="prop-001", landlord_account_id="la-002", address="Duplicate")
    ]
    assert can_access_screening_report(
        property_managers[0],
        screening_reports[0],
        properties=duplicate_properties,
        tenants=tenants,
    ) is False


def test_missing_ids_deny_access(
    property_managers, properties, tenants, screening_reports
):
    report_without_tenant_id = ScreeningReport(
        id="rep-001", tenant_id="", ssn_last4="1234", credit_score=710
    )
    assert can_access_screening_report(
        property_managers[0],
        report_without_tenant_id,
        properties=properties,
        tenants=tenants,
    ) is False

    manager_without_account_id = property_managers[0].__class__(
        id="pm-invalid", name="Invalid manager", landlord_account_id=""
    )
    assert can_access_screening_report(
        manager_without_account_id,
        screening_reports[0],
        properties=properties,
        tenants=tenants,
    ) is False
