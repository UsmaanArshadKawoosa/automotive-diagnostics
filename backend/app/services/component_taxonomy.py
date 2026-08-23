from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ComponentDefinition:
    component_id: str
    display_name: str
    system_category: str
    vehicle_region: str
    description: str


COMPONENT_REGISTRY: Dict[str, ComponentDefinition] = {}


def _register(definition: ComponentDefinition) -> None:
    COMPONENT_REGISTRY[definition.component_id] = definition


_register(ComponentDefinition(
    component_id="engine",
    display_name="Engine",
    system_category="engine",
    vehicle_region="engine_bay",
    description="The primary engine assembly, including block, heads, and internal components.",
))

_register(ComponentDefinition(
    component_id="ignition_coil",
    display_name="Ignition Coil",
    system_category="ignition",
    vehicle_region="engine_bay",
    description="Transforms battery voltage to the high voltage needed to create a spark at the spark plug.",
))

_register(ComponentDefinition(
    component_id="spark_plug",
    display_name="Spark Plug",
    system_category="ignition",
    vehicle_region="engine_bay",
    description="Ignites the air-fuel mixture inside the combustion chamber.",
))

_register(ComponentDefinition(
    component_id="starter_motor",
    display_name="Starter Motor",
    system_category="ignition",
    vehicle_region="engine_bay",
    description="Cranks the engine during start-up.",
))

_register(ComponentDefinition(
    component_id="battery",
    display_name="Battery",
    system_category="electrical",
    vehicle_region="engine_bay",
    description="Stores and supplies electrical energy to the vehicle's electrical systems.",
))

_register(ComponentDefinition(
    component_id="alternator",
    display_name="Alternator",
    system_category="electrical",
    vehicle_region="engine_bay",
    description="Generates electricity to charge the battery and power electrical systems while the engine runs.",
))

_register(ComponentDefinition(
    component_id="fuel_injector",
    display_name="Fuel Injector",
    system_category="fuel",
    vehicle_region="engine_bay",
    description="Sprays atomized fuel into the intake manifold or combustion chamber under pressure.",
))

_register(ComponentDefinition(
    component_id="fuel_pump",
    display_name="Fuel Pump",
    system_category="fuel",
    vehicle_region="fuel_tank",
    description="Delivers fuel from the tank to the engine at the required pressure.",
))

_register(ComponentDefinition(
    component_id="fuel_pressure_regulator",
    display_name="Fuel Pressure Regulator",
    system_category="fuel",
    vehicle_region="engine_bay",
    description="Maintains consistent fuel pressure to the injectors.",
))

_register(ComponentDefinition(
    component_id="fuel_filter",
    display_name="Fuel Filter",
    system_category="fuel",
    vehicle_region="fuel_tank",
    description="Removes contaminants from fuel before it reaches the injectors. A clogged filter restricts flow and causes low pressure.",
))

_register(ComponentDefinition(
    component_id="maf_sensor",
    display_name="Mass Air Flow Sensor",
    system_category="sensors",
    vehicle_region="intake",
    description="Measures the mass of air entering the engine so the ECM can calculate fuel delivery.",
))

_register(ComponentDefinition(
    component_id="map_sensor",
    display_name="Manifold Absolute Pressure Sensor",
    system_category="sensors",
    vehicle_region="engine_bay",
    description="Measures intake manifold pressure to determine engine load for fuel and ignition control.",
))

_register(ComponentDefinition(
    component_id="throttle_body",
    display_name="Throttle Body",
    system_category="intake",
    vehicle_region="intake",
    description="Controls airflow into the engine based on driver throttle input.",
))

_register(ComponentDefinition(
    component_id="iac_valve",
    display_name="Idle Air Control Valve",
    system_category="intake",
    vehicle_region="intake",
    description="Controls bypass airflow around the throttle plate to maintain commanded idle speed.",
))

_register(ComponentDefinition(
    component_id="throttle_position_sensor",
    display_name="Throttle Position Sensor",
    system_category="sensors",
    vehicle_region="intake",
    description="Reports throttle plate angle to the ECM for fuel and timing control.",
))

_register(ComponentDefinition(
    component_id="oxygen_sensor",
    display_name="Oxygen Sensor",
    system_category="sensors",
    vehicle_region="exhaust",
    description="Measures oxygen content in exhaust gases to allow the ECM to adjust fuel mixture.",
))

_register(ComponentDefinition(
    component_id="coolant_temperature_sensor",
    display_name="Coolant Temperature Sensor",
    system_category="sensors",
    vehicle_region="engine_bay",
    description="Reports engine coolant temperature to the ECM for fuel enrichment and idle control.",
))

_register(ComponentDefinition(
    component_id="intake_air_temp_sensor",
    display_name="Intake Air Temperature Sensor",
    system_category="sensors",
    vehicle_region="intake",
    description="Reports intake air temperature to the ECM for fuel delivery adjustment.",
))

_register(ComponentDefinition(
    component_id="crankshaft_position_sensor",
    display_name="Crankshaft Position Sensor",
    system_category="sensors",
    vehicle_region="engine_bay",
    description="Provides engine speed and piston position to the ECM for injection and ignition timing.",
))

_register(ComponentDefinition(
    component_id="camshaft_position_sensor",
    display_name="Camshaft Position Sensor",
    system_category="sensors",
    vehicle_region="engine_bay",
    description="Provides camshaft position to the ECM for sequential fuel injection and VVT control.",
))

_register(ComponentDefinition(
    component_id="knock_sensor",
    display_name="Knock Sensor",
    system_category="sensors",
    vehicle_region="engine_bay",
    description="Detects engine detonation and signals the ECM to retard ignition timing.",
))

_register(ComponentDefinition(
    component_id="vehicle_speed_sensor",
    display_name="Vehicle Speed Sensor",
    system_category="sensors",
    vehicle_region="transmission",
    description="Provides vehicle speed data to the ECM and transmission control module for shift scheduling and speedometer function.",
))

_register(ComponentDefinition(
    component_id="catalytic_converter",
    display_name="Catalytic Converter",
    system_category="exhaust",
    vehicle_region="underbody",
    description="Reduces harmful emissions by converting exhaust gases into less toxic substances.",
))

_register(ComponentDefinition(
    component_id="egr_valve",
    display_name="EGR Valve",
    system_category="emissions",
    vehicle_region="engine_bay",
    description="Recirculates a portion of exhaust gases into the intake manifold to reduce NOx emissions.",
))

_register(ComponentDefinition(
    component_id="evap_purge_valve",
    display_name="EVAP Purge Valve",
    system_category="emissions",
    vehicle_region="engine_bay",
    description="Controls the flow of fuel vapors from the charcoal canister into the engine for combustion.",
))

_register(ComponentDefinition(
    component_id="evap_vent_valve",
    display_name="EVAP Vent Valve",
    system_category="emissions",
    vehicle_region="chassis",
    description="Allows air to enter the EVAP system during diagnostic tests and purging.",
))

_register(ComponentDefinition(
    component_id="charcoal_canister",
    display_name="Charcoal Canister",
    system_category="emissions",
    vehicle_region="chassis",
    description="Stores fuel vapors from the fuel tank and releases them to the engine for combustion via the purge valve.",
))

_register(ComponentDefinition(
    component_id="pcv_valve",
    display_name="PCV Valve",
    system_category="ventilation",
    vehicle_region="engine_bay",
    description="Routes crankcase gases back into the intake manifold to prevent pressure buildup and emissions.",
))

_register(ComponentDefinition(
    component_id="radiator",
    display_name="Radiator",
    system_category="cooling",
    vehicle_region="engine_bay",
    description="Dissipates heat from the engine coolant to the atmosphere.",
))

_register(ComponentDefinition(
    component_id="thermostat",
    display_name="Thermostat",
    system_category="cooling",
    vehicle_region="engine_bay",
    description="Regulates coolant flow to maintain optimal engine operating temperature.",
))

_register(ComponentDefinition(
    component_id="water_pump",
    display_name="Water Pump",
    system_category="cooling",
    vehicle_region="engine_bay",
    description="Circulates coolant through the engine and radiator.",
))

_register(ComponentDefinition(
    component_id="transmission",
    display_name="Transmission",
    system_category="transmission",
    vehicle_region="transmission",
    description="Transmits power from the engine to the drive wheels through gear ratios.",
))

_register(ComponentDefinition(
    component_id="torque_converter",
    display_name="Torque Converter",
    system_category="transmission",
    vehicle_region="transmission",
    description="Fluid coupling that transfers rotating power from the engine to the automatic transmission.",
))

_register(ComponentDefinition(
    component_id="brake_booster",
    display_name="Brake Booster",
    system_category="brakes",
    vehicle_region="engine_bay",
    description="Uses vacuum pressure to amplify braking force applied by the driver.",
))

_register(ComponentDefinition(
    component_id="vacuum_hose",
    display_name="Vacuum Hose",
    system_category="vacuum",
    vehicle_region="engine_bay",
    description="Carries vacuum pressure from the engine to various accessories and systems.",
))

_register(ComponentDefinition(
    component_id="cruise_control",
    display_name="Cruise Control System",
    system_category="electrical",
    vehicle_region="engine_bay",
    description="Maintains vehicle speed without driver throttle input. Includes servo, switches, and control module.",
))

_register(ComponentDefinition(
    component_id="intake_manifold",
    display_name="Intake Manifold",
    system_category="intake",
    vehicle_region="intake",
    description="Distributes air (or air-fuel mixture) to each cylinder intake port.",
))

_register(ComponentDefinition(
    component_id="exhaust_manifold",
    display_name="Exhaust Manifold",
    system_category="exhaust",
    vehicle_region="engine_bay",
    description="Collects exhaust gases from multiple cylinders into a single exhaust pipe.",
))

_register(ComponentDefinition(
    component_id="air_filter",
    display_name="Air Filter",
    system_category="intake",
    vehicle_region="engine_bay",
    description="Removes contaminants from incoming air before it enters the engine. A restricted filter reduces airflow and power.",
))

_register(ComponentDefinition(
    component_id="timing_belt",
    display_name="Timing Belt",
    system_category="engine",
    vehicle_region="engine_bay",
    description="Synchronizes crankshaft and camshaft rotation. A broken or skipped timing belt causes no-start or catastrophic engine damage in interference engines.",
))

_register(ComponentDefinition(
    component_id="timing_chain",
    display_name="Timing Chain",
    system_category="engine",
    vehicle_region="engine_bay",
    description="Synchronizes crankshaft and camshaft rotation via a metal chain. A stretched or failed timing chain causes variable valve timing errors and rough running.",
))

_register(ComponentDefinition(
    component_id="head_gasket",
    display_name="Head Gasket",
    system_category="engine",
    vehicle_region="engine_bay",
    description="Seals the interface between the cylinder head and engine block. A blown head gasket causes coolant mixing with oil, white smoke, overheating, and misfire.",
))


FAULT_DESCRIPTION_PREFIXES: Dict[str, str] = {
    "faulty ignition coil": "ignition_coil",
    "failed ignition coil": "ignition_coil",
    "ignition coil failure": "ignition_coil",
    "worn spark plug": "spark_plug",
    "fouled spark plug": "spark_plug",
    "spark plug wear": "spark_plug",
    "faulty spark plug": "spark_plug",
    "bad spark plug": "spark_plug",
    "faulty fuel injector": "fuel_injector",
    "clogged fuel injector": "fuel_injector",
    "fuel injector failure": "fuel_injector",
    "fuel injector malfunction": "fuel_injector",
    "faulty fuel pump": "fuel_pump",
    "failed fuel pump": "fuel_pump",
    "weak fuel pump": "fuel_pump",
    "fuel pump weakness": "fuel_pump",
    "fuel pump failure": "fuel_pump",
    "dirty maf sensor": "maf_sensor",
    "faulty maf sensor": "maf_sensor",
    "maf sensor fault": "maf_sensor",
    "faulty map sensor": "map_sensor",
    "failed map sensor": "map_sensor",
    "map sensor fault": "map_sensor",
    "faulty throttle body": "throttle_body",
    "dirty throttle body": "throttle_body",
    "throttle body failure": "throttle_body",
    "throttle body malfunction": "throttle_body",
    "faulty throttle position sensor": "throttle_position_sensor",
    "failed throttle position sensor": "throttle_position_sensor",
    "faulty oxygen sensor": "oxygen_sensor",
    "failed oxygen sensor": "oxygen_sensor",
    "oxygen sensor failure": "oxygen_sensor",
    "faulty coolant temperature sensor": "coolant_temperature_sensor",
    "failed coolant temperature sensor": "coolant_temperature_sensor",
    "coolant temperature sensor failure": "coolant_temperature_sensor",
    "faulty intake air temp sensor": "intake_air_temp_sensor",
    "failed crankshaft position sensor": "crankshaft_position_sensor",
    "faulty crankshaft position sensor": "crankshaft_position_sensor",
    "crankshaft position sensor failure": "crankshaft_position_sensor",
    "failed camshaft position sensor": "camshaft_position_sensor",
    "faulty camshaft position sensor": "camshaft_position_sensor",
    "camshaft position sensor failure": "camshaft_position_sensor",
    "failed knock sensor": "knock_sensor",
    "faulty knock sensor": "knock_sensor",
    "knock sensor failure": "knock_sensor",
    "restricted catalytic converter": "catalytic_converter",
    "clogged catalytic converter": "catalytic_converter",
    "faulty catalytic converter": "catalytic_converter",
    "catalytic converter degradation": "catalytic_converter",
    "catalytic converter physical damage": "catalytic_converter",
    "failed egr valve": "egr_valve",
    "faulty egr valve": "egr_valve",
    "stuck egr valve": "egr_valve",
    "egr valve malfunction": "egr_valve",
    "egr valve stuck open": "egr_valve",
    "egr valve stuck closed": "egr_valve",
    "failed evap purge valve": "evap_purge_valve",
    "faulty evap purge valve": "evap_purge_valve",
    "failed pcv valve": "pcv_valve",
    "faulty pcv valve": "pcv_valve",
    "pcv system failure": "pcv_valve",
    "leaking radiator": "radiator",
    "faulty radiator": "radiator",
    "failed thermostat": "thermostat",
    "faulty thermostat": "thermostat",
    "failed water pump": "water_pump",
    "faulty water pump": "water_pump",
    "failed starter motor": "starter_motor",
    "faulty starter motor": "starter_motor",
    "failed alternator": "alternator",
    "faulty alternator": "alternator",
    "bad alternator": "alternator",
    "vacuum leak": "vacuum_hose",
    "vacuum hose leak": "vacuum_hose",
    "iac valve failure": "iac_valve",
    "faulty iac valve": "iac_valve",
    "idle air control valve failure": "iac_valve",
    "faulty idle air control valve": "iac_valve",
    "failed idle air control valve": "iac_valve",
    "failed torque converter": "torque_converter",
    "faulty torque converter": "torque_converter",
    "failed brake booster": "brake_booster",
    "faulty brake booster": "brake_booster",
    "faulty fuel pressure regulator": "fuel_pressure_regulator",
    "failed fuel pressure regulator": "fuel_pressure_regulator",
    "fuel pressure regulator failure": "fuel_pressure_regulator",
    "fuel pressure regulator leak": "fuel_pressure_regulator",
    "faulty intake manifold": "intake_manifold",
    "cracked intake manifold": "intake_manifold",
    "intake manifold gasket failure": "intake_manifold",
    "faulty exhaust manifold": "exhaust_manifold",
    "cracked exhaust manifold": "exhaust_manifold",
    "exhaust manifold leak": "exhaust_manifold",
    "failed charcoal canister": "charcoal_canister",
    "faulty charcoal canister": "charcoal_canister",
    "evap system leak": "charcoal_canister",
    "evap leak": "charcoal_canister",
    "air filter restriction": "air_filter",
    "clogged air filter": "air_filter",
    "fuel filter clog": "fuel_filter",
    "timing chain wear": "timing_chain",
    "timing belt failure": "timing_belt",
    "head gasket failure": "head_gasket",
    "blown head gasket": "head_gasket",
}

KNOWLEDGE_ENTRY_KEY_TO_COMPONENT: Dict[str, str] = {
    "ignition_coil_failure": "ignition_coil",
    "spark_plug_wear": "spark_plug",
    "maf_sensor_fault": "maf_sensor",
    "restricted_catalytic_converter": "catalytic_converter",
    "vacuum_leak": "vacuum_hose",
    "throttle_position_sensor": "throttle_position_sensor",
    "accelerator_pedal_position_sensor": "throttle_body",
    "intake_air_temp_sensor": "intake_air_temp_sensor",
    "engine_coolant_temp_sensor": "coolant_temperature_sensor",
    "crankshaft_position_sensor": "crankshaft_position_sensor",
    "camshaft_position_sensor": "camshaft_position_sensor",
    "knock_sensor": "knock_sensor",
    "p0100": "maf_sensor",
    "p0101": "maf_sensor",
    "p0102": "maf_sensor",
    "p0103": "maf_sensor",
    "p0107": "map_sensor",
    "p0108": "map_sensor",
    "p0110": "intake_air_temp_sensor",
    "p0112": "intake_air_temp_sensor",
    "p0113": "intake_air_temp_sensor",
    "p0115": "coolant_temperature_sensor",
    "p0116": "coolant_temperature_sensor",
    "p0117": "coolant_temperature_sensor",
    "p0118": "coolant_temperature_sensor",
    "p0119": "coolant_temperature_sensor",
    "p0120": "throttle_position_sensor",
    "p0121": "throttle_position_sensor",
    "p0122": "throttle_position_sensor",
    "p0123": "throttle_position_sensor",
    "p0125": "thermostat",
    "p0130": "oxygen_sensor",
    "p0131": "oxygen_sensor",
    "p0132": "oxygen_sensor",
    "p0133": "oxygen_sensor",
    "p0134": "oxygen_sensor",
    "p0135": "oxygen_sensor",
    "p0140": "oxygen_sensor",
    "p0141": "oxygen_sensor",
    "p0142": "oxygen_sensor",
    "p0143": "oxygen_sensor",
    "p0300": "spark_plug",
    "p0301": "spark_plug",
    "p0302": "spark_plug",
    "p0303": "spark_plug",
    "p0304": "spark_plug",
    "p0170": "maf_sensor",
    "p0171": "maf_sensor",
    "p0172": "fuel_injector",
    "p0173": "maf_sensor",
    "p0174": "maf_sensor",
    "p0175": "fuel_injector",
    "p0201": "fuel_injector",
    "p0202": "fuel_injector",
    "p0203": "fuel_injector",
    "p0204": "fuel_injector",
    "p0210": "fuel_injector",
    "p0211": "fuel_injector",
    "p0212": "fuel_injector",
    "p0219": "engine",
    "p0320": "knock_sensor",
    "p0322": "knock_sensor",
    "p0323": "knock_sensor",
    "p0324": "knock_sensor",
    "p0325": "knock_sensor",
    "p0326": "knock_sensor",
    "p0327": "knock_sensor",
    "p0328": "knock_sensor",
    "p0329": "knock_sensor",
    "p0330": "knock_sensor",
    "p0331": "knock_sensor",
    "p0332": "knock_sensor",
    "p0333": "knock_sensor",
    "p0334": "knock_sensor",
    "p0335": "crankshaft_position_sensor",
    "p0336": "crankshaft_position_sensor",
    "p0337": "crankshaft_position_sensor",
    "p0338": "crankshaft_position_sensor",
    "p0340": "camshaft_position_sensor",
    "p0341": "camshaft_position_sensor",
    "p0342": "camshaft_position_sensor",
    "p0343": "camshaft_position_sensor",
    "p0344": "camshaft_position_sensor",
    "p0345": "camshaft_position_sensor",
    "p0346": "camshaft_position_sensor",
    "p0347": "camshaft_position_sensor",
    "p0400": "egr_valve",
    "p0401": "egr_valve",
    "p0402": "egr_valve",
    "p0403": "egr_valve",
    "p0404": "egr_valve",
    "p0405": "egr_valve",
    "p0406": "egr_valve",
    "p0420": "catalytic_converter",
    "p0422": "catalytic_converter",
    "p0430": "catalytic_converter",
    "p0432": "catalytic_converter",
    "p0440": "evap_purge_valve",
    "p0441": "evap_purge_valve",
    "p0442": "evap_purge_valve",
    "p0443": "evap_purge_valve",
    "p0444": "evap_purge_valve",
    "p0445": "evap_purge_valve",
    "p0446": "evap_vent_valve",
    "p0447": "evap_vent_valve",
    "p0448": "evap_vent_valve",
    "p0449": "evap_vent_valve",
    "p0450": "evap_purge_valve",
    "p0451": "evap_purge_valve",
    "p0452": "evap_purge_valve",
    "p0453": "evap_purge_valve",
    "p0455": "charcoal_canister",
    "p0456": "charcoal_canister",
    "p0457": "charcoal_canister",
    "p0500": "vehicle_speed_sensor",
    "p0501": "vehicle_speed_sensor",
    "p0502": "vehicle_speed_sensor",
    "p0503": "vehicle_speed_sensor",
    "p0504": "brake_booster",
    "p0505": "iac_valve",
    "p0506": "iac_valve",
    "p0507": "iac_valve",
    "p0510": "throttle_position_sensor",
    "p0511": "iac_valve",
    "p0512": "starter_motor",
    "p0513": "battery",
    "p0514": "battery",
    "p0515": "battery",
    "p0516": "battery",
    "p0517": "battery",
    "p0518": "iac_valve",
    "p0519": "iac_valve",
    "p0595": "cruise_control",
    "p0596": "cruise_control",
    "p0597": "cruise_control",
    "p0598": "cruise_control",
    "p0599": "cruise_control",
    "p0610": "engine",
    "p0620": "alternator",
    "p0630": "engine",
    "p0625": "alternator",
    "p0626": "alternator",
    "p0627": "fuel_pump",
    "p0628": "fuel_pump",
    "p0629": "fuel_pump",
    "fuel_injector_malfunction": "fuel_injector",
    "fuel_pump_weakness": "fuel_pump",
    "fuel_pressure_regulator_leak": "fuel_pressure_regulator",
    "fuel_contamination": "fuel_pump",
    "fuel_filter_clog": "fuel_filter",
    "timing_chain_wear": "timing_chain",
    "timing_belt_failure": "timing_belt",
    "valve_train_wear": "engine",
    "head_gasket_failure": "head_gasket",
    "low_compression": "engine",
    "throttle_body_failure": "throttle_body",
    "intake_manifold_gasket_failure": "intake_manifold",
    "vacuum_hose_leak": "vacuum_hose",
    "exhaust_manifold_leak": "exhaust_manifold",
    "air_filter_restriction": "air_filter",
    "map_sensor_fault": "map_sensor",
    "oxygen_sensor_failure": "oxygen_sensor",
    "intake_leak": "intake_manifold",
    "exhaust_leak": "exhaust_manifold",
    "egr_valve_malfunction": "egr_valve",
    "evap_leak": "charcoal_canister",
    "crankshaft_position_sensor_failure": "crankshaft_position_sensor",
    "camshaft_position_sensor_failure": "camshaft_position_sensor",
    "throttle_body_malfunction": "throttle_body",
    "coolant_temperature_sensor_failure": "coolant_temperature_sensor",
    "knock_sensor_failure": "knock_sensor",
    "pcv_system_failure": "pcv_valve",
    "fuel_pump_failure": "fuel_pump",
    "fuel_pressure_regulator_failure": "fuel_pressure_regulator",
    "catalytic_converter_degradation": "catalytic_converter",
    "evap_system_leak": "charcoal_canister",
    "egr_valve_stuck_open": "egr_valve",
    "egr_valve_stuck_closed": "egr_valve",
    "oxygen_sensor_contamination": "oxygen_sensor",
    "catalytic_converter_physical_damage": "catalytic_converter",
    "spark_plug_replacement": "spark_plug",
    "ignition_coil_replacement": "ignition_coil",
    "vacuum_leak_repair": "vacuum_hose",
    "maf_sensor_service": "maf_sensor",
    "oxygen_sensor_replacement": "oxygen_sensor",
    "throttle_body_cleaning": "throttle_body",
    "maf_sensor_replacement": "maf_sensor",
    "map_sensor_replacement": "map_sensor",
    "crankshaft_position_sensor_replacement": "crankshaft_position_sensor",
    "camshaft_position_sensor_replacement": "camshaft_position_sensor",
    "coolant_temperature_sensor_replacement": "coolant_temperature_sensor",
    "knock_sensor_replacement": "knock_sensor",
    "fuel_injector_cleaning": "fuel_injector",
    "fuel_injector_replacement": "fuel_injector",
    "fuel_pump_replacement": "fuel_pump",
    "fuel_pressure_regulator_replacement": "fuel_pressure_regulator",
    "fuel_filter_replacement": "fuel_filter",
    "catalytic_converter_replacement": "catalytic_converter",
    "exhaust_manifold_gasket_replacement": "exhaust_manifold",
    "muffler_resonator_replacement": "exhaust_manifold",
    "egr_valve_cleaning": "egr_valve",
    "egr_valve_replacement": "egr_valve",
    "evap_system_leak_repair": "charcoal_canister",
    "evap_purge_valve_replacement": "evap_purge_valve",
    "evap_vent_valve_replacement": "evap_vent_valve",
    "timing_belt_replacement": "timing_belt",
    "timing_chain_replacement": "timing_chain",
    "head_gasket_replacement": "head_gasket",
    "valve_cover_gasket_replacement": "engine",
    "pcv_valve_replacement": "pcv_valve",
}


def get_component(component_id: str) -> Optional[ComponentDefinition]:
    return COMPONENT_REGISTRY.get(component_id)


def get_all_components() -> List[ComponentDefinition]:
    return list(COMPONENT_REGISTRY.values())


def is_valid_component_id(component_id: str) -> bool:
    return component_id in COMPONENT_REGISTRY


def map_fault_description(description: str) -> Optional[ComponentDefinition]:
    if not description:
        return None
    lower = description.strip().lower()
    for prefix, component_id in FAULT_DESCRIPTION_PREFIXES.items():
        if lower.startswith(prefix):
            return get_component(component_id)
    return None


def map_knowledge_entry(entry_key: str, category: str) -> Optional[ComponentDefinition]:
    if not entry_key:
        return None
    lower_key = entry_key.strip().lower()
    component_id = KNOWLEDGE_ENTRY_KEY_TO_COMPONENT.get(lower_key)
    if component_id:
        return get_component(component_id)
    return None


def map_evidence_to_component(evidence: List["KnowledgeSearchResult"]) -> Optional[ComponentDefinition]:
    from app.schemas import KnowledgeSearchResult
    from collections import Counter

    component_counts: Counter[str] = Counter()
    for item in evidence:
        component = map_knowledge_entry(item.entry_key or "", item.category)
        if component:
            component_counts[component.component_id] += 1

    if not component_counts:
        return None

    # Return the most frequently mapped component
    most_common_id = component_counts.most_common(1)[0][0]
    return get_component(most_common_id)
