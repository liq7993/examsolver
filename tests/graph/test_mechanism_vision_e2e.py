"""End-to-end graph test: image -> VLM describe -> mechanism routing -> gear ratio.

This is the automated proxy for M5-04 / M5-09's "上传齿轮图 -> 返回正确传动比".
It drives the *real* compiled graph (`run_solve_graph`) and fakes only the two
external dependencies that cannot run in CI: the cloud VLM (`describe_images`)
and the extraction LLM the skill asks for (`pick_llm`). PaddleOCR is stubbed so
the test does not load the heavy model. Everything between -- routing,
needs_vision detection, vlm_node wiring, skill dispatch and the deterministic
Fraction-based ratio math -- is exercised for real.

A *live* real-image + real-Claude-VLM acceptance run remains a manual step.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _helpers.fake_llm import FakeLLMClient
from examsolver.contracts import SolveRequest
from examsolver.graph import run_solve_graph
from examsolver.multimodal.ocr_paddle import OCRResult


def test_vision_gear_train_returns_correct_ratio(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "gear.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    # PaddleOCR yields only a short snippet -> keeps needs_vision True and avoids
    # loading the real model.
    monkeypatch.setattr(
        "examsolver.graph.nodes.recognize",
        lambda _paths: OCRResult(text="z1", bboxes=[], confidence=0.9),
    )
    # Cloud is reachable and the VLM describes the gears it can see (no solving).
    monkeypatch.setattr("examsolver.graph.nodes.check_cloud_reachable", lambda: True)
    monkeypatch.setattr(
        "examsolver.graph.nodes.describe_images",
        lambda _images, _prompt: (
            "图中为两级齿轮传动：第一对 z1=24、z2=72，第二对 z3=20、z4=40。"
        ),
    )
    # The skill's extraction LLM reads that description and returns gear stages.
    fake = FakeLLMClient.from_recorded(
        {
            "stages": [
                {"driving_teeth": 24, "driven_teeth": 72},
                {"driving_teeth": 20, "driven_teeth": 40},
            ]
        }
    )
    monkeypatch.setattr(
        "examsolver.pipeline.dispatcher.pick_llm",
        lambda *_args, **_kwargs: fake,
    )

    response = run_solve_graph(
        SolveRequest(
            question="图中所示齿轮机构的总传动比是多少？",
            image_paths=[str(image_path)],
        )
    )

    assert response.success is True
    assert response.subject == "mechanism"
    assert response.question_type == "gear_train"
    assert response.skill == "mechanism.gear_train"
    # 72/24 * 40/20 = 3 * 2 = 6
    assert "6" in str(response.answer)
    assert "vlm_offline" not in response.fallback_reasons
    assert "vlm_failed" not in response.fallback_reasons
    assert response.note is not None
    assert response.note.solve_id == response.solve_id
    # The extraction LLM was actually consulted with the vision description.
    assert fake.call_count == 1
    assert "z1=24" in (fake.last_messages or [])[-1].content


def test_vision_gear_train_offline_degrades_without_fabricating(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "gear.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    monkeypatch.setattr(
        "examsolver.graph.nodes.recognize",
        lambda _paths: OCRResult(text="z1", bboxes=[], confidence=0.9),
    )
    # Cloud is unreachable: vlm_node must skip and flag the degradation honestly.
    monkeypatch.setattr("examsolver.graph.nodes.check_cloud_reachable", lambda: False)
    monkeypatch.setattr(
        "examsolver.graph.nodes.describe_images",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("VLM must not be called while offline")
        ),
    )
    # No usable vision text -> extractor returns no stages -> skill refuses to guess.
    fake = FakeLLMClient.from_recorded({"stages": []})
    monkeypatch.setattr(
        "examsolver.pipeline.dispatcher.pick_llm",
        lambda *_args, **_kwargs: fake,
    )

    response = run_solve_graph(
        SolveRequest(
            question="图中所示齿轮机构的总传动比是多少？",
            image_paths=[str(image_path)],
        )
    )

    assert "vlm_offline" in response.fallback_reasons
    # Honest degradation: the skill failed rather than inventing a ratio.
    assert "primary_skill_failed" in response.fallback_reasons
