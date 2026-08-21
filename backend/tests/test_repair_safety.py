import pytest
from app.services.repair_safety import (
    RepairSafetyTier,
    determine_repair_safety_tier,
    is_high_risk_component,
    is_safety_critical_system,
    classify_severity,
)


class TestRepairSafetyRules:
    def test_classify_severity(self):
        assert classify_severity("low") == 1
        assert classify_severity("medium") == 2
        assert classify_severity("high") == 3
        assert classify_severity("critical") == 4
        assert classify_severity("unknown") == 0
        assert classify_severity(None) == 0

    def test_is_high_risk_component(self):
        assert is_high_risk_component("brake_booster") is True
        assert is_high_risk_component("head_gasket") is True
        assert is_high_risk_component("timing_belt") is True
        assert is_high_risk_component("spark_plug") is False
        assert is_high_risk_component("oxygen_sensor") is False
        assert is_high_risk_component(None) is False
        assert is_high_risk_component("") is False

    def test_is_safety_critical_system(self):
        assert is_safety_critical_system("brakes") is True
        assert is_safety_critical_system("steering") is True
        assert is_safety_critical_system("airbag") is True
        assert is_safety_critical_system("suspension") is True
        assert is_safety_critical_system("engine") is False
        assert is_safety_critical_system("ignition") is False
        assert is_safety_critical_system(None) is False
        assert is_safety_critical_system("") is False

    def test_diy_inspection_low_severity_unknown_component(self):
        decision = determine_repair_safety_tier(
            component_id=None,
            system_category=None,
            severity="low",
            repair_suggestion=None,
        )
        assert decision.tier == RepairSafetyTier.DIY_INSPECTION
        assert "low or unknown" in decision.reasoning[0].lower()

    def test_diy_repair_medium_severity_no_safety_systems(self):
        # intake is not in safety-related systems
        decision = determine_repair_safety_tier(
            component_id="air_filter",
            system_category="intake",
            severity="medium",
            repair_suggestion=None,
        )
        assert decision.tier == RepairSafetyTier.DIY_REPAIR

    def test_mechanic_recommended_medium_severity_safety_related_system(self):
        # ignition is a safety-related system -> MECHANIC_RECOMMENDED
        decision = determine_repair_safety_tier(
            component_id="spark_plug",
            system_category="ignition",
            severity="medium",
            repair_suggestion=None,
        )
        assert decision.tier == RepairSafetyTier.MECHANIC_RECOMMENDED
        assert "safety-related" in decision.reasoning[0].lower()

    def test_mechanic_recommended_high_severity_non_safety_system(self):
        decision = determine_repair_safety_tier(
            component_id="air_filter",
            system_category="intake",
            severity="high",
            repair_suggestion=None,
        )
        assert decision.tier == RepairSafetyTier.MECHANIC_RECOMMENDED
        assert "high" in decision.reasoning[0].lower()

    def test_mechanic_recommended_safety_related_system_medium_severity(self):
        decision = determine_repair_safety_tier(
            component_id="fuel_injector",
            system_category="fuel",
            severity="medium",
            repair_suggestion=None,
        )
        assert decision.tier == RepairSafetyTier.MECHANIC_RECOMMENDED
        assert "safety-related" in decision.reasoning[0].lower()

    def test_immediate_professional_safety_related_system_high_severity(self):
        decision = determine_repair_safety_tier(
            component_id="fuel_injector",
            system_category="fuel",
            severity="high",
            repair_suggestion=None,
        )
        assert decision.tier == RepairSafetyTier.IMMEDIATE_PROFESSIONAL
        assert "high for safety-related system" in decision.reasoning[1].lower()

    def test_immediate_professional_major_disassembly_high_risk_component(self):
        # head_gasket is high-risk -> IMMEDIATE_PROFESSIONAL (Rule 1)
        decision = determine_repair_safety_tier(
            component_id="head_gasket",
            system_category="engine",
            severity="medium",
            repair_suggestion="Replace head gasket - requires engine disassembly and torque procedures",
        )
        assert decision.tier == RepairSafetyTier.IMMEDIATE_PROFESSIONAL
        assert "high-risk safety component" in decision.reasoning[0].lower()

    def test_immediate_professional_critical_severity(self):
        decision = determine_repair_safety_tier(
            component_id="spark_plug",
            system_category="ignition",
            severity="critical",
            repair_suggestion=None,
        )
        assert decision.tier == RepairSafetyTier.IMMEDIATE_PROFESSIONAL
        assert "critical" in decision.reasoning[0].lower()

    def test_immediate_professional_high_risk_component(self):
        decision = determine_repair_safety_tier(
            component_id="brake_booster",
            system_category="brakes",
            severity="low",
            repair_suggestion=None,
        )
        assert decision.tier == RepairSafetyTier.IMMEDIATE_PROFESSIONAL
        assert "high-risk safety component" in decision.reasoning[0].lower()

    def test_immediate_professional_safety_critical_system(self):
        # steering_rack is in HIGH_RISK_COMPONENT_IDS -> IMMEDIATE_PROFESSIONAL
        decision = determine_repair_safety_tier(
            component_id="steering_rack",
            system_category="steering",
            severity="medium",
            repair_suggestion=None,
        )
        assert decision.tier == RepairSafetyTier.IMMEDIATE_PROFESSIONAL
        assert "high-risk safety component" in decision.reasoning[0].lower()

    def test_immediate_professional_high_risk_with_high_severity(self):
        # head_gasket is high-risk -> IMMEDIATE_PROFESSIONAL
        decision = determine_repair_safety_tier(
            component_id="head_gasket",
            system_category="engine",
            severity="high",
            repair_suggestion=None,
        )
        assert decision.tier == RepairSafetyTier.IMMEDIATE_PROFESSIONAL
        assert "high-risk safety component" in decision.reasoning[0].lower()

    def test_unknown_component_defaults_to_inspection(self):
        decision = determine_repair_safety_tier(
            component_id="unknown_component",
            system_category=None,
            severity="low",
            repair_suggestion=None,
        )
        assert decision.tier == RepairSafetyTier.DIY_INSPECTION

    def test_case_insensitive_component_and_system(self):
        decision1 = determine_repair_safety_tier(
            component_id="BRAKE_BOOSTER",
            system_category="BRAKES",
            severity="medium",
            repair_suggestion=None,
        )
        decision2 = determine_repair_safety_tier(
            component_id="brake_booster",
            system_category="brakes",
            severity="medium",
            repair_suggestion=None,
        )
        assert decision1.tier == decision2.tier
        assert decision1.tier == RepairSafetyTier.IMMEDIATE_PROFESSIONAL

    def test_repair_suggestion_keywords(self):
        keywords = ["replace", "rebuild", "overhaul", "remove", "disassemble", "press", "machine", "torque", "alignment", "program", "calibrate"]
        for kw in keywords:
            decision = determine_repair_safety_tier(
                component_id="air_filter",
                system_category="intake",
                severity="low",
                repair_suggestion=f"Need to {kw} the component",
            )
            assert decision.tier == RepairSafetyTier.MECHANIC_RECOMMENDED, f"Keyword '{kw}' should trigger MECHANIC_RECOMMENDED"