"""Tests for Hyperbion sensorium blueprints."""

from ainsoft.pipeline.hyperbion import (
    HyperbionModule,
    SensoriumCell,
    FSMCore,
    MandorlaField,
    Oriphiel5DMemory,
    SeraphicFeedbackModule,
)


def test_hyperbion_growth_and_split():
    root = HyperbionModule(name="root")
    child = root.grow()
    assert child.name.startswith("root_child")
    root.mutate()
    fused = child.fuse(root)
    split_a, split_b = root.split()
    assert fused.name.startswith("root_child") or fused.name.startswith("root_fused")
    assert fused.active
    assert split_a.name.endswith("split1")
    assert split_b.name.endswith("split2")


def test_sensorium_resonance_and_fsm_audit():
    cells = [SensoriumCell() for _ in range(3)]
    for idx in range(2):
        cells[idx].add_neighbor(cells[idx + 1])
        cells[idx + 1].add_neighbor(cells[idx])

    fsm = FSMCore(threshold=0.0)
    for cell in cells:
        fsm.gate(cell)
    assert fsm.get_audit()


def test_seraphic_feedback_and_memory():
    field = MandorlaField()
    memory = Oriphiel5DMemory()
    feedback = SeraphicFeedbackModule()

    overlap = field.update([0.1] * 5, [0.9] * 5)
    stored = memory.add_state(overlap)
    pulse = feedback.process_feedback([0.5] * 5)

    assert len(stored) == 5
    assert any(pulse)
