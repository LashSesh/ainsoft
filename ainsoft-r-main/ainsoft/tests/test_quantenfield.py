"""Tests for the CHAIOT-QDASH quantenfield integration."""

from ainsoft.pipeline.quantenfield import (
    CubeZoomLayer,
    EpigeneticOperator,
    FieldEmotionRegulationModule,
    FieldOperatorRegistry,
    FieldState,
    FieldTopologicalAdapter,
    GabrielFieldCell,
    MandorlaConvergenceField,
    OphanKernel,
    Oriphiel5DMemory,
    QLogicKernel,
    TINTATransducer,
    TripolarResonanceKernel,
    default_modulator,
    default_trident,
)


def test_field_state_entropy_and_projection() -> None:
    state = FieldState({"a": 1.0, "b": 2.0, "omega": 0.7})
    entropy = state.entropy()
    assert entropy > 0.0

    mandorla = MandorlaConvergenceField()
    projected = mandorla.project([0.1] * mandorla.dimension)
    assert len(projected) == mandorla.dimension
    assert -1.0 <= mandorla.overlap() <= 1.0


def test_gabriel_field_cell_pipeline() -> None:
    field_state = FieldState({"omega": 0.6, "phase_bias": 0.5})
    context = FieldState({"baseline": 0.55, "spectrum": 0.7})
    memory = Oriphiel5DMemory()
    mandorla = MandorlaConvergenceField()
    cell = GabrielFieldCell(default_trident, memory, mandorla, default_modulator)

    result = cell(None, context, field_state)
    assert "resonance" in result
    assert "mandorla" in result
    assert memory.proof_of_resonance(threshold=0.1)


def test_tripolar_qlogic_and_ophan_trigger() -> None:
    field_state = FieldState({"omega": 0.4})
    context = FieldState({"psi": 0.8, "rho": 0.5})
    tripolar = TripolarResonanceKernel()
    qlogic = QLogicKernel()
    events = []

    def trigger(state: FieldState) -> None:
        events.append(state.get("tripolar_output"))

    ophan = OphanKernel(trigger)
    tripolar(None, context, field_state)
    qlogic(None, context, field_state)

    # Force tripolar output above threshold to trigger the singularity
    field_state["tripolar_output"] = 1.0
    ophan(None, context, field_state)

    assert events and events[0] == 1.0


def test_epigenetic_operator_mutation_and_layers() -> None:
    registry = FieldOperatorRegistry()
    registry.register("tripolar", TripolarResonanceKernel())
    meta = EpigeneticOperator()
    meta.mutate(registry, seed=42)

    cube = CubeZoomLayer()
    field_state = FieldState()
    cube.mount(field_state, {"psi": 0.9, "rho": 0.4}, mode="inline")
    assert "psi" in field_state and "rho" in field_state
    cube.unmount(field_state)
    assert "psi" not in field_state


def test_field_output_transducers() -> None:
    field_state = FieldState({"tripolar_output": 0.75})
    adapter = FieldTopologicalAdapter()
    tinta = TINTATransducer()
    emotion = FieldEmotionRegulationModule()

    context = FieldState()
    actuator_value = adapter(None, context, field_state)
    payload = tinta(None, context, field_state)
    emotion_state = emotion(0.5, context, field_state)

    assert isinstance(actuator_value, int)
    assert payload["intention"] == field_state["tripolar_output"]
    assert emotion_state["valence"] != 0.0
