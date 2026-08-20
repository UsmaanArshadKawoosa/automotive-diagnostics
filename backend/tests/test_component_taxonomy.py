from app.services.component_taxonomy import (
    COMPONENT_REGISTRY,
    ComponentDefinition,
    get_all_components,
    get_component,
    is_valid_component_id,
    map_evidence_to_component,
    map_fault_description,
    map_knowledge_entry,
)


class TestComponentTaxonomy:
    def test_get_component_known(self):
        component = get_component("ignition_coil")
        assert component is not None
        assert component.display_name == "Ignition Coil"
        assert component.system_category == "ignition"
        assert component.vehicle_region == "engine_bay"

    def test_get_component_unknown(self):
        component = get_component("nonexistent_component")
        assert component is None

    def test_is_valid_component_id_known(self):
        assert is_valid_component_id("ignition_coil") is True

    def test_is_valid_component_id_unknown(self):
        assert is_valid_component_id("nonexistent_component") is False

    def test_is_valid_component_id_empty(self):
        assert is_valid_component_id("") is False

    def test_get_all_components_returns_nonempty(self):
        components = get_all_components()
        assert len(components) > 0
        ids = [c.component_id for c in components]
        assert "ignition_coil" in ids
        assert "catalytic_converter" in ids
        assert "fuel_filter" in ids
        assert "air_filter" in ids
        assert "iac_valve" in ids
        assert "vehicle_speed_sensor" in ids
        assert "timing_belt" in ids
        assert "timing_chain" in ids
        assert "head_gasket" in ids

    def test_all_components_have_required_fields(self):
        for component in get_all_components():
            assert component.component_id
            assert component.display_name
            assert component.system_category
            assert component.vehicle_region
            assert component.description

    def test_registry_immutability(self):
        original_count = len(COMPONENT_REGISTRY)
        get_all_components()
        assert len(COMPONENT_REGISTRY) == original_count

    def test_map_fault_description_exact_match(self):
        component = map_fault_description("Faulty ignition coil")
        assert component is not None
        assert component.component_id == "ignition_coil"
        assert component.system_category == "ignition"
        assert component.vehicle_region == "engine_bay"

    def test_map_fault_description_clogged_catalytic(self):
        component = map_fault_description("Clogged catalytic converter")
        assert component is not None
        assert component.component_id == "catalytic_converter"
        assert component.system_category == "exhaust"
        assert component.vehicle_region == "underbody"

    def test_map_fault_description_new_components(self):
        assert map_fault_description("Fuel filter clog").component_id == "fuel_filter"
        assert map_fault_description("Air filter restriction").component_id == "air_filter"
        assert map_fault_description("Timing chain wear").component_id == "timing_chain"
        assert map_fault_description("Timing belt failure").component_id == "timing_belt"
        assert map_fault_description("Head gasket failure").component_id == "head_gasket"

    def test_map_fault_description_unknown_returns_none(self):
        component = map_fault_description("Some completely unknown fault description")
        assert component is None

    def test_map_fault_description_empty_returns_none(self):
        component = map_fault_description("")
        assert component is None

    def test_map_fault_description_case_insensitive(self):
        component = map_fault_description("FAULTY IGNITION COIL")
        assert component is not None
        assert component.component_id == "ignition_coil"

    def test_map_knowledge_entry_exact_match(self):
        component = map_knowledge_entry("ignition_coil_failure", "fault")
        assert component is not None
        assert component.component_id == "ignition_coil"

    def test_map_knowledge_entry_dtc_match(self):
        component = map_knowledge_entry("P0300", "dtc")
        assert component is not None
        assert component.component_id == "spark_plug"

    def test_map_knowledge_entry_new_dtc_mappings(self):
        assert map_knowledge_entry("P0201", "dtc").component_id == "fuel_injector"
        assert map_knowledge_entry("P0172", "dtc").component_id == "fuel_injector"
        assert map_knowledge_entry("P0500", "dtc").component_id == "vehicle_speed_sensor"
        assert map_knowledge_entry("P0505", "dtc").component_id == "iac_valve"
        assert map_knowledge_entry("P0620", "dtc").component_id == "alternator"
        assert map_knowledge_entry("P0455", "dtc").component_id == "charcoal_canister"

    def test_map_knowledge_entry_new_fault_mappings(self):
        assert map_knowledge_entry("fuel_filter_clog", "fault").component_id == "fuel_filter"
        assert map_knowledge_entry("air_filter_restriction", "fault").component_id == "air_filter"
        assert map_knowledge_entry("timing_chain_wear", "fault").component_id == "timing_chain"
        assert map_knowledge_entry("head_gasket_failure", "fault").component_id == "head_gasket"

    def test_map_knowledge_entry_unknown_returns_none(self):
        component = map_knowledge_entry("unknown_entry_key", "fault")
        assert component is None

    def test_map_evidence_to_component_first_match_wins(self):
        class FakeEvidence:
            def __init__(self, entry_key, category):
                self.entry_key = entry_key
                self.category = category

        evidence = [
            FakeEvidence("unknown_entry", "fault"),
            FakeEvidence("ignition_coil_failure", "fault"),
            FakeEvidence("catalytic_converter_failure", "fault"),
        ]
        component = map_evidence_to_component(evidence)
        assert component is not None
        assert component.component_id == "ignition_coil"

    def test_map_evidence_to_component_empty_list(self):
        component = map_evidence_to_component([])
        assert component is None
