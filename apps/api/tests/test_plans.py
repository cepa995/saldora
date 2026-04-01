"""Tests for plan constants and feature hierarchy."""

import pytest

from app.plans import (
    PLANS,
    Feature,
    PlanTier,
    get_plan,
    plan_has_feature,
)


class TestPlanDefinitions:
    """Verify plan constants are consistent and complete."""

    def test_all_tiers_have_definitions(self):
        """Every PlanTier enum value must have a corresponding PlanDefinition."""
        for tier in PlanTier:
            assert tier in PLANS, f"Missing plan definition for {tier}"

    def test_feature_hierarchy_starter_subset_of_pro(self):
        """Starter features must be a subset of Pro features."""
        starter = PLANS[PlanTier.STARTER].features
        pro = PLANS[PlanTier.PRO].features
        assert starter.issubset(pro), f"Starter features not subset of Pro: {starter - pro}"

    def test_feature_hierarchy_pro_subset_of_agency(self):
        """Pro features must be a subset of Agency features."""
        pro = PLANS[PlanTier.PRO].features
        agency = PLANS[PlanTier.AGENCY].features
        assert pro.issubset(agency), f"Pro features not subset of Agency: {pro - agency}"

    def test_free_has_base_features(self):
        """Free plan should have OCR, export, MiniMax XML, and NBS."""
        free_plan = PLANS[PlanTier.FREE]
        assert Feature.OCR_EXTRACTION in free_plan.features
        assert Feature.EXPORT_CSV_XLSX_JSON in free_plan.features
        assert Feature.MINIMAX_XML_EXPORT in free_plan.features
        assert Feature.NBS_EXCHANGE_RATES in free_plan.features

    def test_pro_has_accounting(self):
        """Pro plan should include accounting intent and MiniMax push."""
        pro_plan = PLANS[PlanTier.PRO]
        assert Feature.ACCOUNTING_INTENT in pro_plan.features
        assert Feature.MINIMAX_DIRECT_PUSH in pro_plan.features

    def test_agency_has_automation_and_audit(self):
        """Agency plan should include automation rules and audit export."""
        agency = PLANS[PlanTier.AGENCY]
        assert Feature.AUTOMATION_RULES in agency.features
        assert Feature.AUDIT_EXPORT in agency.features

    def test_starter_does_not_have_pro_features(self):
        """Starter should NOT have Pro-only features."""
        starter = PLANS[PlanTier.STARTER]
        assert Feature.ACCOUNTING_INTENT not in starter.features
        assert Feature.AUTOMATION_RULES not in starter.features

    def test_invoice_limits(self):
        """Verify invoice limits match the agreed pricing table."""
        assert PLANS[PlanTier.FREE].invoice_limit == 10
        assert PLANS[PlanTier.STARTER].invoice_limit == 100
        assert PLANS[PlanTier.PRO].invoice_limit == 400
        assert PLANS[PlanTier.AGENCY].invoice_limit == 1500

    def test_user_limits(self):
        """Verify user limits match the agreed pricing table."""
        assert PLANS[PlanTier.FREE].user_limit == 1
        assert PLANS[PlanTier.STARTER].user_limit == 2
        assert PLANS[PlanTier.PRO].user_limit == 5
        assert PLANS[PlanTier.AGENCY].user_limit == 15


class TestGetPlan:
    """Test get_plan() lookup function."""

    def test_get_plan_valid(self):
        """get_plan returns correct definition for valid plan names."""
        plan = get_plan("starter")
        assert plan.tier == PlanTier.STARTER
        assert plan.invoice_limit == 100

    def test_get_plan_unknown_raises(self):
        """get_plan raises ValueError for unknown plan names."""
        with pytest.raises(ValueError, match="Unknown plan"):
            get_plan("platinum")

    def test_get_plan_all_tiers(self):
        """get_plan works for every valid tier name."""
        for tier in PlanTier:
            plan = get_plan(tier.value)
            assert plan.tier == tier


class TestPlanHasFeature:
    """Test plan_has_feature() check function."""

    def test_starter_has_ocr(self):
        """Starter plan includes OCR."""
        assert plan_has_feature("starter", Feature.OCR_EXTRACTION) is True

    def test_agency_has_automation(self):
        """Agency plan includes automation rules."""
        assert plan_has_feature("agency", Feature.AUTOMATION_RULES) is True

    def test_pro_lacks_automation(self):
        """Pro plan does not include automation rules."""
        assert plan_has_feature("pro", Feature.AUTOMATION_RULES) is False
