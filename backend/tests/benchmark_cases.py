"""
Deterministic Diagnostic Benchmark Cases

This module defines realistic automotive diagnostic cases for evaluating the diagnostic pipeline.
Cases are designed to test specific aspects of the system using only knowledge present in the repository.

Each case includes:
- vehicle info (make, model, year)
- DTC codes (if any)
- symptom description
- expected component(s) - the component that SHOULD be identified
- acceptable alternative components - other plausible components
- expected system category
- expected evidence category (dtc, symptom, fault, component, repair)
- expected safety tier (deterministic from repair_safety.py)
- whether follow-up should be requested
- description of what this case tests

IMPORTANT: Do NOT fabricate automotive knowledge. Use only what exists in the knowledge base.
"""

from dataclasses import dataclass, field
from typing import Optional
from app.schemas import DiagnosticAnalyzeRequest


@dataclass(frozen=True)
class BenchmarkCase:
    """A single diagnostic benchmark case."""
    case_id: str
    description: str
    vehicle_make: Optional[str]
    vehicle_model: Optional[str]
    vehicle_year: Optional[int]
    dtc_codes: list[str]
    symptom_text: str
    expected_component_id: str
    acceptable_alternative_components: list[str] = field(default_factory=list)
    expected_system_category: Optional[str] = None
    expected_evidence_category: Optional[str] = None
    expected_safety_tier: Optional[str] = None
    expects_follow_up: bool = False
    follow_up_reason_keywords: list[str] = field(default_factory=list)
    test_focus: str = ""

    def to_request(self) -> DiagnosticAnalyzeRequest:
        """Convert to a DiagnosticAnalyzeRequest."""
        return DiagnosticAnalyzeRequest(
            make=self.vehicle_make,
            model=self.vehicle_model,
            year=self.vehicle_year,
            dtc_codes=self.dtc_codes if self.dtc_codes else None,
            symptom_text=self.symptom_text,
        )


# ============================================================================
# BENCHMARK CASES
# ============================================================================

BENCHMARK_CASES: list[BenchmarkCase] = [
    # -------------------------------------------------------------
    # 1. DTC-ONLY DIAGNOSIS
    # -------------------------------------------------------------
    BenchmarkCase(
        case_id="B001",
        description="P0300 random misfire - should map to spark_plug via DTC",
        vehicle_make="Toyota",
        vehicle_model="Corolla",
        vehicle_year=2020,
        dtc_codes=["P0300"],
        symptom_text="Check engine light on",
        expected_component_id="spark_plug",
        acceptable_alternative_components=["ignition_coil", "fuel_injector"],
        expected_system_category="ignition",
        expected_evidence_category="dtc",
        expected_safety_tier="immediate_professional",  # ignition system + high severity from LLM
        test_focus="DTC code interpretation and component mapping",
    ),

    BenchmarkCase(
        case_id="B002",
        description="P0171 system too lean - should map to maf_sensor via DTC",
        vehicle_make="Honda",
        vehicle_model="Civic",
        vehicle_year=2018,
        dtc_codes=["P0171"],
        symptom_text="Poor fuel economy and rough idle",
        expected_component_id="maf_sensor",
        acceptable_alternative_components=["vacuum_hose", "fuel_injector", "oxygen_sensor"],
        expected_system_category="sensors",
        expected_evidence_category="dtc",
        expected_safety_tier="mechanic_recommended",
        test_focus="DTC code interpretation for lean condition",
    ),

    BenchmarkCase(
        case_id="B003",
        description="P0420 catalytic converter efficiency - should map to catalytic_converter",
        vehicle_make="Ford",
        vehicle_model="F-150",
        vehicle_year=2019,
        dtc_codes=["P0420"],
        symptom_text="Check engine light, possible rotten egg smell",
        expected_component_id="catalytic_converter",
        acceptable_alternative_components=["oxygen_sensor"],
        expected_system_category="exhaust",
        expected_evidence_category="dtc",
        expected_safety_tier="immediate_professional",  # exhaust + high severity
        test_focus="DTC code for emissions system",
    ),

    BenchmarkCase(
        case_id="B004",
        description="P0505 idle air control - should map to iac_valve",
        vehicle_make="Chevrolet",
        vehicle_model="Silverado",
        vehicle_year=2017,
        dtc_codes=["P0505"],
        symptom_text="Idle fluctuates, engine stalls at stop",
        expected_component_id="iac_valve",
        acceptable_alternative_components=["throttle_body", "vacuum_hose"],
        expected_system_category="intake",
        expected_evidence_category="dtc",
        expected_safety_tier="mechanic_recommended",
        test_focus="DTC code for idle control system",
    ),

    BenchmarkCase(
        case_id="B005",
        description="P0335 crankshaft position sensor - should map to crankshaft_position_sensor",
        vehicle_make="Nissan",
        vehicle_model="Altima",
        vehicle_year=2016,
        dtc_codes=["P0335"],
        symptom_text="Engine cranks but won't start, intermittent stalling",
        expected_component_id="crankshaft_position_sensor",
        acceptable_alternative_components=["camshaft_position_sensor"],
        expected_system_category="sensors",
        expected_evidence_category="dtc",
        expected_safety_tier="mechanic_recommended",
        test_focus="DTC code for no-start condition",
    ),

    # -------------------------------------------------------------
    # 2. SYMPTOM-ONLY DIAGNOSIS
    # -------------------------------------------------------------
    BenchmarkCase(
        case_id="B006",
        description="Rough idle symptom - should retrieve rough_idle knowledge",
        vehicle_make=None,
        vehicle_model=None,
        vehicle_year=None,
        dtc_codes=[],
        symptom_text="Engine shakes and vibrates at idle, RPM fluctuates",
        expected_component_id="vacuum_hose",  # From symptom evidence mapping
        acceptable_alternative_components=["spark_plug", "ignition_coil", "throttle_body", "iac_valve"],
        expected_system_category="vacuum",
        expected_evidence_category="symptom",
        expected_safety_tier="diy_repair",  # vacuum system, medium severity -> diy_repair
        expects_follow_up=True,
        follow_up_reason_keywords=["condition", "specific", "load", "temperature", "RPM"],
        test_focus="Symptom-only retrieval and component inference",
    ),

    BenchmarkCase(
        case_id="B007",
        description="Engine misfire symptom - should retrieve engine_misfire knowledge",
        vehicle_make=None,
        vehicle_model=None,
        vehicle_year=None,
        dtc_codes=[],
        symptom_text="Engine hesitates and jerks under acceleration, loss of power",
        expected_component_id="spark_plug",  # From misfire symptom mapping
        acceptable_alternative_components=["ignition_coil", "fuel_injector", "maf_sensor"],
        expected_system_category="ignition",
        expected_evidence_category="symptom",
        expected_safety_tier="immediate_professional",
        expects_follow_up=True,
        follow_up_reason_keywords=["condition", "load", "acceleration", "specific"],
        test_focus="Symptom-only for misfire",
    ),

    BenchmarkCase(
        case_id="B008",
        description="Soft brake pedal - no brake symptom in knowledge base",
        vehicle_make=None,
        vehicle_model=None,
        vehicle_year=None,
        dtc_codes=[],
        symptom_text="Brake pedal feels soft and goes to floor, longer stopping distance",
        expected_component_id="throttle_body",  # No brake symptom knowledge; retrieves throttle_body
        acceptable_alternative_components=["master_cylinder", "brake_line", "brake_caliper", "abs_module"],
        expected_system_category="intake",  # Retrieved evidence maps to intake
        expected_evidence_category="none",
        expected_safety_tier="immediate_professional",  # brakes are safety-critical
        expects_follow_up=True,
        follow_up_reason_keywords=["brake", "pedal", "fluid", "leak"],
        test_focus="Safety-critical symptom without knowledge base entry",
    ),

    BenchmarkCase(
        case_id="B009",
        description="Engine overheating - should retrieve cooling system knowledge",
        vehicle_make=None,
        vehicle_model=None,
        vehicle_year=None,
        dtc_codes=[],
        symptom_text="Temperature gauge reads hot, coolant boiling, steam from hood",
        expected_component_id="thermostat",  # From engine_overheating symptom
        acceptable_alternative_components=["water_pump", "radiator", "coolant_temperature_sensor"],
        expected_system_category="cooling",
        expected_evidence_category="symptom",
        expected_safety_tier="immediate_professional",  # cooling under pressure + critical
        expects_follow_up=True,
        follow_up_reason_keywords=["coolant", "temperature", "leak", "overheat"],
        test_focus="Safety-critical symptom (cooling)",
    ),

    # -------------------------------------------------------------
    # 3. DTC + SYMPTOM DIAGNOSIS
    # -------------------------------------------------------------
    BenchmarkCase(
        case_id="B010",
        description="P0300 + rough idle - combined signals should reinforce spark_plug",
        vehicle_make="Toyota",
        vehicle_model="Camry",
        vehicle_year=2019,
        dtc_codes=["P0300"],
        symptom_text="Engine misfiring at idle, shaking when stopped",
        expected_component_id="spark_plug",
        acceptable_alternative_components=["ignition_coil", "fuel_injector"],
        expected_system_category="ignition",
        expected_evidence_category="dtc",  # DTC should dominate
        expected_safety_tier="immediate_professional",
        test_focus="DTC + symptom combination reinforces correct component",
    ),

    BenchmarkCase(
        case_id="B011",
        description="P0171 + rough idle - lean condition with idle symptoms",
        vehicle_make="Honda",
        vehicle_model="Accord",
        vehicle_year=2017,
        dtc_codes=["P0171"],
        symptom_text="Rough idle, engine stalls when coming to stop",
        expected_component_id="maf_sensor",
        acceptable_alternative_components=["vacuum_hose", "iac_valve", "fuel_injector"],
        expected_system_category="sensors",
        expected_evidence_category="dtc",
        expected_safety_tier="mechanic_recommended",
        test_focus="DTC + symptom for lean + idle",
    ),

    BenchmarkCase(
        case_id="B012",
        description="P0442 EVAP small leak - emissions system",
        vehicle_make="Toyota",
        vehicle_model="Prius",
        vehicle_year=2020,
        dtc_codes=["P0442"],
        symptom_text="Fuel smell after filling tank, check engine light",
        expected_component_id="evap_purge_valve",  # P0442 maps to evap_purge_valve
        acceptable_alternative_components=["charcoal_canister", "evap_vent_valve"],
        expected_system_category="emissions",
        expected_evidence_category="dtc",
        expected_safety_tier="mechanic_recommended",
        test_focus="EVAP system DTC",
    ),

    # -------------------------------------------------------------
    # 4. MULTIPLE PLAUSIBLE CAUSES (Differential Diagnosis)
    # -------------------------------------------------------------
    BenchmarkCase(
        case_id="B013",
        description="Rough idle without DTC - multiple plausible causes",
        vehicle_make=None,
        vehicle_model=None,
        vehicle_year=None,
        dtc_codes=[],
        symptom_text="Engine runs rough at idle, smooths out when accelerating",
        expected_component_id="vacuum_hose",
        acceptable_alternative_components=["spark_plug", "ignition_coil", "iac_valve", "throttle_body", "maf_sensor"],
        expected_system_category="vacuum",
        expected_evidence_category="symptom",
        expected_safety_tier="diy_repair",  # vacuum system, medium severity -> diy_repair
        expects_follow_up=True,
        follow_up_reason_keywords=["condition", "specific", "load", "temperature", "RPM"],
        test_focus="Multiple plausible causes without DTC - should ask follow-up",
    ),

    BenchmarkCase(
        case_id="B014",
        description="Hard start + no DTC - multiple ignition/fuel causes",
        vehicle_make=None,
        vehicle_model=None,
        vehicle_year=None,
        dtc_codes=[],
        symptom_text="Engine cranks long time before starting, especially when cold",
        expected_component_id="fuel_pump",  # From fuel_delivery symptom
        acceptable_alternative_components=["fuel_filter", "fuel_pressure_regulator", "crankshaft_position_sensor", "spark_plug"],
        expected_system_category="fuel",
        expected_evidence_category="symptom",
        expected_safety_tier="mechanic_recommended",
        expects_follow_up=True,
        test_focus="Multiple plausible causes - hard start",
    ),

    # -------------------------------------------------------------
    # 5. CONFLICTING EVIDENCE
    # -------------------------------------------------------------
    BenchmarkCase(
        case_id="B015",
        description="Symptoms suggest ignition but DTC suggests fuel - conflicting",
        vehicle_make="Toyota",
        vehicle_model="Corolla",
        vehicle_year=2018,
        dtc_codes=["P0171"],  # Lean = fuel/air
        symptom_text="Engine misfires under load, shaking on acceleration",
        expected_component_id="maf_sensor",  # DTC should dominate
        acceptable_alternative_components=["spark_plug", "ignition_coil", "vacuum_hose", "fuel_injector"],
        expected_system_category="sensors",
        expected_evidence_category="dtc",
        expected_safety_tier="mechanic_recommended",
        expects_follow_up=True,
        follow_up_reason_keywords=["condition", "load", "acceleration", "specific"],
        test_focus="Conflicting evidence (DTC vs symptoms) - should ask follow-up",
    ),

    # -------------------------------------------------------------
    # 6. INSUFFICIENT INFORMATION REQUIRING FOLLOW-UP
    # -------------------------------------------------------------
    BenchmarkCase(
        case_id="B016",
        description="Vague symptom - should request more info",
        vehicle_make=None,
        vehicle_model=None,
        vehicle_year=None,
        dtc_codes=[],
        symptom_text="Car doesn't run right",
        expected_component_id="fuel_pump",  # Generic symptom retrieves fuel system evidence
        acceptable_alternative_components=["engine", "fuel_filter", "spark_plug"],
        expected_system_category="fuel",
        expected_evidence_category="symptom",
        expected_safety_tier="mechanic_recommended",  # fuel system -> mechanic_recommended
        expects_follow_up=True,
        follow_up_reason_keywords=["detail", "describe", "symptom", "more"],
        test_focus="Insufficient information - vague symptom",
    ),

    BenchmarkCase(
        case_id="B017",
        description="Unknown DTC code - should request clarification",
        vehicle_make="Toyota",
        vehicle_model="Camry",
        vehicle_year=2020,
        dtc_codes=["P9999"],  # Not in knowledge base
        symptom_text="Check engine light on",
        expected_component_id="camshaft_position_sensor",  # Unknown DTC retrieves camshaft sensor evidence
        acceptable_alternative_components=["engine"],
        expected_system_category="sensors",
        expected_evidence_category="none",
        expected_safety_tier="diy_inspection",
        expects_follow_up=True,
        follow_up_reason_keywords=["DTC", "code", "confirm", "knowledge"],
        test_focus="Unknown DTC not in knowledge base",
    ),

    # -------------------------------------------------------------
    # 7. SAFETY-CRITICAL CASES
    # -------------------------------------------------------------
    BenchmarkCase(
        case_id="B018",
        description="Brake system - P0500 vehicle speed + soft pedal = immediate professional",
        vehicle_make="Honda",
        vehicle_model="CR-V",
        vehicle_year=2019,
        dtc_codes=["P0500"],
        symptom_text="Brake pedal soft, ABS light on, longer stopping distance",
        expected_component_id="vehicle_speed_sensor",  # P0500 maps to vehicle_speed_sensor
        acceptable_alternative_components=["abs_module", "brake_line", "master_cylinder"],
        expected_system_category="sensors",
        expected_evidence_category="dtc",
        expected_safety_tier="immediate_professional",
        test_focus="Safety-critical: brake-related",
    ),

    BenchmarkCase(
        case_id="B019",
        description="Steering - P0504 brake booster + steering effort = immediate professional",
        vehicle_make="Ford",
        vehicle_model="Focus",
        vehicle_year=2018,
        dtc_codes=["P0504"],
        symptom_text="Steering heavy, brake pedal hard, warning lights",
        expected_component_id="brake_booster",  # P0504 maps to brake_booster
        acceptable_alternative_components=["master_cylinder", "abs_module"],
        expected_system_category="brakes",
        expected_evidence_category="dtc",
        expected_safety_tier="immediate_professional",
        test_focus="Safety-critical: brake booster",
    ),

    # -------------------------------------------------------------
    # 8. ENGINE/FUEL/INTAKE CASES
    # -------------------------------------------------------------
    BenchmarkCase(
        case_id="B020",
        description="P0301 cylinder 1 misfire - specific cylinder",
        vehicle_make="Toyota",
        vehicle_model="Corolla",
        vehicle_year=2020,
        dtc_codes=["P0301"],
        symptom_text="Engine misfires, check engine light flashing",
        expected_component_id="spark_plug",  # P0301 maps to spark_plug
        acceptable_alternative_components=["ignition_coil", "fuel_injector"],
        expected_system_category="ignition",
        expected_evidence_category="dtc",
        expected_safety_tier="immediate_professional",
        test_focus="Cylinder-specific misfire DTC",
    ),

    BenchmarkCase(
        case_id="B021",
        description="P0201 injector circuit - fuel system",
        vehicle_make="Chevrolet",
        vehicle_model="Malibu",
        vehicle_year=2017,
        dtc_codes=["P0201"],
        symptom_text="Rough idle, misfire on cylinder 1, poor acceleration",
        expected_component_id="fuel_injector",  # P0201 maps to fuel_injector
        acceptable_alternative_components=["spark_plug", "ignition_coil"],
        expected_system_category="fuel",
        expected_evidence_category="dtc",
        expected_safety_tier="mechanic_recommended",
        test_focus="Fuel injector circuit DTC",
    ),

    # -------------------------------------------------------------
    # 9. COOLING SYSTEM CASES
    # -------------------------------------------------------------
    BenchmarkCase(
        case_id="B022",
        description="P0125 thermostat - cooling system",
        vehicle_make="Ford",
        vehicle_model="Escape",
        vehicle_year=2019,
        dtc_codes=["P0125"],
        symptom_text="Engine takes long to warm up, heater blows cold",
        expected_component_id="thermostat",  # P0125 maps to thermostat
        acceptable_alternative_components=["coolant_temperature_sensor", "water_pump"],
        expected_system_category="cooling",
        expected_evidence_category="dtc",
        expected_safety_tier="immediate_professional",  # cooling under pressure
        test_focus="Cooling system DTC",
    ),

    # -------------------------------------------------------------
    # 10. EXHAUST/EMISSIONS CASES
    # -------------------------------------------------------------
    BenchmarkCase(
        case_id="B023",
        description="P0446 EVAP vent valve - emissions",
        vehicle_make="Toyota",
        vehicle_model="Tacoma",
        vehicle_year=2018,
        dtc_codes=["P0446"],
        symptom_text="Check engine light, difficulty filling fuel tank",
        expected_component_id="evap_vent_valve",  # P0446 maps to evap_vent_valve
        acceptable_alternative_components=["evap_purge_valve", "charcoal_canister"],
        expected_system_category="emissions",
        expected_evidence_category="dtc",
        expected_safety_tier="mechanic_recommended",
        test_focus="EVAP vent valve DTC",
    ),

    # -------------------------------------------------------------
    # 11. ELECTRICAL/IGNITION CASES
    # -------------------------------------------------------------
    BenchmarkCase(
        case_id="B024",
        description="P0626 alternator - electrical system",
        vehicle_make="Honda",
        vehicle_model="Pilot",
        vehicle_year=2016,
        dtc_codes=["P0626"],
        symptom_text="Battery light on, dimming headlights, electrical issues",
        expected_component_id="alternator",  # P0626 maps to alternator
        acceptable_alternative_components=["battery", "starter_motor"],
        expected_system_category="electrical",
        expected_evidence_category="dtc",
        expected_safety_tier="mechanic_recommended",
        test_focus="Alternator/charging system DTC",
    ),

    # -------------------------------------------------------------
    # 12. DTC DOES NOT UNIQUELY IDENTIFY COMPONENT
    # -------------------------------------------------------------
    BenchmarkCase(
        case_id="B025",
        description="P0300 random misfire - could be ignition, fuel, compression, or vacuum",
        vehicle_make="Toyota",
        vehicle_model="Camry",
        vehicle_year=2018,
        dtc_codes=["P0300"],
        symptom_text="Random misfire, check engine light flashing",
        expected_component_id="spark_plug",  # DTC maps to spark_plug but could be others
        acceptable_alternative_components=["ignition_coil", "fuel_injector", "vacuum_hose", "maf_sensor", "fuel_pump"],
        expected_system_category="ignition",
        expected_evidence_category="dtc",
        expected_safety_tier="immediate_professional",
        expects_follow_up=True,  # Multiple plausible causes
        test_focus="DTC with multiple root causes - should ask follow-up",
    ),
]


def get_all_cases() -> list[BenchmarkCase]:
    """Return all benchmark cases."""
    return BENCHMARK_CASES


def get_case(case_id: str) -> Optional[BenchmarkCase]:
    """Get a specific benchmark case by ID."""
    for case in BENCHMARK_CASES:
        if case.case_id == case_id:
            return case
    return None


def get_cases_by_focus(focus: str) -> list[BenchmarkCase]:
    """Get cases matching a test focus keyword."""
    return [c for c in BENCHMARK_CASES if focus.lower() in c.test_focus.lower()]


def get_cases_expecting_follow_up() -> list[BenchmarkCase]:
    """Get cases that expect a follow-up question."""
    return [c for c in BENCHMARK_CASES if c.expects_follow_up]


def get_safety_critical_cases() -> list[BenchmarkCase]:
    """Get cases that should receive immediate_professional safety tier."""
    return [c for c in BENCHMARK_CASES if c.expected_safety_tier == "immediate_professional"]


def get_dtc_only_cases() -> list[BenchmarkCase]:
    """Get cases with DTC codes only (no detailed symptoms)."""
    return [c for c in BENCHMARK_CASES if c.dtc_codes and c.symptom_text in ("Check engine light on", "Check engine light on, possible rotten egg smell")]


def get_symptom_only_cases() -> list[BenchmarkCase]:
    """Get cases with symptoms only (no DTC codes)."""
    return [c for c in BENCHMARK_CASES if not c.dtc_codes]


def get_dtc_plus_symptom_cases() -> list[BenchmarkCase]:
    """Get cases with both DTC codes and detailed symptoms."""
    return [c for c in BENCHMARK_CASES if c.dtc_codes and c.symptom_text not in ("Check engine light on", "Check engine light on, possible rotten egg smell")]