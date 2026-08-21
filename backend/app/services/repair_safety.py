from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.services.component_taxonomy import ComponentDefinition, get_component


class RepairSafetyTier(str, Enum):
    DIY_INSPECTION = "diy_inspection"
    DIY_REPAIR = "diy_repair"
    MECHANIC_RECOMMENDED = "mechanic_recommended"
    IMMEDIATE_PROFESSIONAL = "immediate_professional"


TIER_LABELS: dict[RepairSafetyTier, str] = {
    RepairSafetyTier.DIY_INSPECTION: "Safe to inspect yourself",
    RepairSafetyTier.DIY_REPAIR: "DIY repair may be possible",
    RepairSafetyTier.MECHANIC_RECOMMENDED: "Mechanic recommended",
    RepairSafetyTier.IMMEDIATE_PROFESSIONAL: "Seek professional service immediately",
}

TIER_DESCRIPTIONS: dict[RepairSafetyTier, str] = {
    RepairSafetyTier.DIY_INSPECTION: (
        "This issue can be safely inspected by a vehicle owner with basic tools. "
        "No specialized equipment or safety risk is involved."
    ),
    RepairSafetyTier.DIY_REPAIR: (
        "This repair may be performed by a confident DIYer with appropriate tools. "
        "Follow service manual procedures and torque specifications."
    ),
    RepairSafetyTier.MECHANIC_RECOMMENDED: (
        "This repair involves safety-critical systems or requires specialized tools/equipment. "
        "A qualified mechanic should perform the work."
    ),
    RepairSafetyTier.IMMEDIATE_PROFESSIONAL: (
        "This issue affects safety-critical systems (brakes, steering, airbags, structural) "
        "or poses immediate danger. Do not drive the vehicle. Seek professional service immediately."
    ),
}

SAFETY_CRITICAL_SYSTEM_CATEGORIES = {
    "brakes",
    "steering",
    "airbag",
    "restraint",
    "structural",
    "suspension",
}

HIGH_RISK_COMPONENT_IDS = {
    "brake_booster",
    "master_cylinder",
    "brake_caliper",
    "brake_line",
    "abs_module",
    "steering_rack",
    "steering_column",
    "tie_rod",
    "ball_joint",
    "control_arm",
    "airbag_module",
    "seatbelt_pretensioner",
    "head_gasket",
    "timing_belt",
    "timing_chain",
    "fuel_line",
    "fuel_tank",
}


@dataclass(frozen=True)
class SafetyTierDecision:
    tier: RepairSafetyTier
    label: str
    description: str
    reasoning: list[str]


def is_safety_critical_system(system_category: Optional[str]) -> bool:
    if not system_category:
        return False
    return system_category.lower() in SAFETY_CRITICAL_SYSTEM_CATEGORIES


def is_high_risk_component(component_id: Optional[str]) -> bool:
    if not component_id:
        return False
    return component_id.lower() in HIGH_RISK_COMPONENT_IDS


def classify_severity(severity: Optional[str]) -> int:
    """Map severity string to numeric weight."""
    severity_map = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }
    return severity_map.get((severity or "").lower(), 0)


def determine_repair_safety_tier(
    component_id: Optional[str],
    system_category: Optional[str],
    severity: Optional[str],
    repair_suggestion: Optional[str] = None,
) -> SafetyTierDecision:
    """
    Deterministically determine the repair safety tier based on available information.
    
    Rules (in priority order):
    1. If component or system is safety-critical → IMMEDIATE_PROFESSIONAL
    2. If severity is critical → IMMEDIATE_PROFESSIONAL
    3. If component is high-risk → MECHANIC_RECOMMENDED (or IMMEDIATE_PROFESSIONAL if critical)
    4. If system is safety-related (emissions, fuel, cooling under pressure) → MECHANIC_RECOMMENDED
    5. If severity is high → MECHANIC_RECOMMENDED
    6. If repair involves disassembly of major components → MECHANIC_RECOMMENDED
    7. If severity is medium → DIY_REPAIR
    8. If severity is low or unknown → DIY_INSPECTION
    """
    reasoning: list[str] = []
    comp = get_component(component_id) if component_id else None

    # Rule 1: Safety-critical component or system
    if is_high_risk_component(component_id):
        reasoning.append(f"Component '{component_id}' is a high-risk safety component")
        return SafetyTierDecision(
            tier=RepairSafetyTier.IMMEDIATE_PROFESSIONAL,
            label=TIER_LABELS[RepairSafetyTier.IMMEDIATE_PROFESSIONAL],
            description=TIER_DESCRIPTIONS[RepairSafetyTier.IMMEDIATE_PROFESSIONAL],
            reasoning=reasoning,
        )

    if is_safety_critical_system(system_category):
        reasoning.append(f"System category '{system_category}' is safety-critical")
        return SafetyTierDecision(
            tier=RepairSafetyTier.IMMEDIATE_PROFESSIONAL,
            label=TIER_LABELS[RepairSafetyTier.IMMEDIATE_PROFESSIONAL],
            description=TIER_DESCRIPTIONS[RepairSafetyTier.IMMEDIATE_PROFESSIONAL],
            reasoning=reasoning,
        )

    # Rule 2: Critical severity
    if classify_severity(severity) >= 4:
        reasoning.append(f"Severity '{severity}' is critical")
        return SafetyTierDecision(
            tier=RepairSafetyTier.IMMEDIATE_PROFESSIONAL,
            label=TIER_LABELS[RepairSafetyTier.IMMEDIATE_PROFESSIONAL],
            description=TIER_DESCRIPTIONS[RepairSafetyTier.IMMEDIATE_PROFESSIONAL],
            reasoning=reasoning,
        )

    # Rule 3: High-risk component with high severity
    if is_high_risk_component(component_id) and classify_severity(severity) >= 3:
        reasoning.append(f"High-risk component '{component_id}' with high severity")
        return SafetyTierDecision(
            tier=RepairSafetyTier.IMMEDIATE_PROFESSIONAL,
            label=TIER_LABELS[RepairSafetyTier.IMMEDIATE_PROFESSIONAL],
            description=TIER_DESCRIPTIONS[RepairSafetyTier.IMMEDIATE_PROFESSIONAL],
            reasoning=reasoning,
        )

    # Rule 4: Safety-related systems (fuel, emissions, cooling under pressure, etc.)
    safety_related_systems = {
        "fuel",
        "emissions",
        "cooling",
        "exhaust",
        "electrical",
        "ignition",
    }
    if system_category and system_category.lower() in safety_related_systems:
        reasoning.append(f"System '{system_category}' involves safety-related components")
        # If high severity, bump to immediate professional
        if classify_severity(severity) >= 3:
            reasoning.append(f"Severity '{severity}' is high for safety-related system")
            return SafetyTierDecision(
                tier=RepairSafetyTier.IMMEDIATE_PROFESSIONAL,
                label=TIER_LABELS[RepairSafetyTier.IMMEDIATE_PROFESSIONAL],
                description=TIER_DESCRIPTIONS[RepairSafetyTier.IMMEDIATE_PROFESSIONAL],
                reasoning=reasoning,
            )
        return SafetyTierDecision(
            tier=RepairSafetyTier.MECHANIC_RECOMMENDED,
            label=TIER_LABELS[RepairSafetyTier.MECHANIC_RECOMMENDED],
            description=TIER_DESCRIPTIONS[RepairSafetyTier.MECHANIC_RECOMMENDED],
            reasoning=reasoning,
        )

    # Rule 5: High severity
    if classify_severity(severity) >= 3:
        reasoning.append(f"Severity '{severity}' is high")
        return SafetyTierDecision(
            tier=RepairSafetyTier.MECHANIC_RECOMMENDED,
            label=TIER_LABELS[RepairSafetyTier.MECHANIC_RECOMMENDED],
            description=TIER_DESCRIPTIONS[RepairSafetyTier.MECHANIC_RECOMMENDED],
            reasoning=reasoning,
        )

    # Rule 6: Major component disassembly suggested in repair
    if repair_suggestion:
        major_keywords = [
            "replace",
            "rebuild",
            "overhaul",
            "remove",
            "disassemble",
            "press",
            "machine",
            "torque",
            "alignment",
            "program",
            "calibrate",
        ]
        suggestion_lower = repair_suggestion.lower()
        if any(kw in suggestion_lower for kw in major_keywords):
            reasoning.append("Repair suggestion indicates major disassembly or specialized procedure")
            return SafetyTierDecision(
                tier=RepairSafetyTier.MECHANIC_RECOMMENDED,
                label=TIER_LABELS[RepairSafetyTier.MECHANIC_RECOMMENDED],
                description=TIER_DESCRIPTIONS[RepairSafetyTier.MECHANIC_RECOMMENDED],
                reasoning=reasoning,
            )

    # Rule 7: Medium severity
    if classify_severity(severity) >= 2:
        reasoning.append(f"Severity '{severity}' is medium")
        return SafetyTierDecision(
            tier=RepairSafetyTier.DIY_REPAIR,
            label=TIER_LABELS[RepairSafetyTier.DIY_REPAIR],
            description=TIER_DESCRIPTIONS[RepairSafetyTier.DIY_REPAIR],
            reasoning=reasoning,
        )

    # Rule 8: Low severity or unknown
    reasoning.append(f"Severity '{severity or 'unknown'}' is low or unknown; inspection is safe")
    return SafetyTierDecision(
        tier=RepairSafetyTier.DIY_INSPECTION,
        label=TIER_LABELS[RepairSafetyTier.DIY_INSPECTION],
        description=TIER_DESCRIPTIONS[RepairSafetyTier.DIY_INSPECTION],
        reasoning=reasoning,
    )