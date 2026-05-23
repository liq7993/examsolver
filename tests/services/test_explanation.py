from examsolver.contracts import NormalizedQuestion, SolveResult, Step, StudentExplanation
from examsolver.config import LLMConfig
from examsolver.services.explanation import (
    NullExplanationEnhancer,
    enhance_if_needed,
    probe_local_llm,
)


class FakeEnhancer:
    name = "fake"
    version = "0.1.0"

    def __init__(self) -> None:
        self.calls = 0

    def enhance(
        self,
        question: NormalizedQuestion,
        result: SolveResult,
    ) -> StudentExplanation:
        self.calls += 1
        return StudentExplanation(
            summary=f"解释：{question.raw_text}",
            intuition="先看已知条件，再看求什么。",
            step_by_step=["保持原始解题结果不变。"],
            common_mistake="不要让模型覆盖确定性答案。",
            self_check_question="结果字段有没有被改动？",
        )


class BrokenEnhancer:
    name = "broken"
    version = "0.1.0"

    def enhance(
        self,
        question: NormalizedQuestion,
        result: SolveResult,
    ) -> StudentExplanation:
        raise RuntimeError("boom")


def test_enhance_if_needed_fills_missing_explanation_without_changing_facts() -> None:
    question = NormalizedQuestion(raw_text="解释一下天气", normalized_text="解释一下天气", subject="unknown")
    result = SolveResult(
        question_type="unknown",
        skill="unknown",
        steps=[],
        answer=None,
        meta={"success": False, "message": "当前版本尚未支持此题型。"},
    )

    enhanced = enhance_if_needed(question=question, result=result, enhancer=FakeEnhancer())

    assert enhanced.question_type == "unknown"
    assert enhanced.skill == "unknown"
    assert enhanced.steps == []
    assert enhanced.answer is None
    assert enhanced.student_explanation is not None
    assert enhanced.student_explanation.summary == "解释：解释一下天气"
    assert enhanced.meta["explanation_enhancer"] == "fake"


def test_enhance_if_needed_skips_existing_explanation() -> None:
    explanation = StudentExplanation(
        summary="已有解释",
        intuition="",
        step_by_step=[],
        common_mistake="",
        self_check_question="",
    )
    result = SolveResult(
        question_type="derivative",
        skill="calculus.derivative",
        steps=[Step(index=1, description="step")],
        answer="answer",
        student_explanation=explanation,
        meta={"success": True},
    )
    enhancer = FakeEnhancer()

    enhanced = enhance_if_needed(
        question=NormalizedQuestion(raw_text="q", normalized_text="q", subject="calculus"),
        result=result,
        enhancer=enhancer,
    )

    assert enhanced is result
    assert enhancer.calls == 0


def test_enhance_if_needed_treats_enhancer_failure_as_optional() -> None:
    result = SolveResult(
        question_type="unknown",
        skill="unknown",
        steps=[],
        answer=None,
        meta={"success": False},
    )

    enhanced = enhance_if_needed(
        question=NormalizedQuestion(raw_text="q", normalized_text="q", subject="unknown"),
        result=result,
        enhancer=BrokenEnhancer(),
    )

    assert enhanced is result


def test_null_explanation_enhancer_is_noop() -> None:
    result = SolveResult(
        question_type="unknown",
        skill="unknown",
        steps=[],
        answer=None,
    )

    enhanced = enhance_if_needed(
        question=NormalizedQuestion(raw_text="q", normalized_text="q", subject="unknown"),
        result=result,
        enhancer=NullExplanationEnhancer(),
    )

    assert enhanced is result


def test_probe_local_llm_disabled_is_fast_non_reachable() -> None:
    status = probe_local_llm(
        LLMConfig(
            provider="none",
            base_url="http://127.0.0.1:8080/v1",
            model="gemma",
            model_path=None,
            timeout_seconds=60,
            max_tokens=256,
            temperature=0.2,
        )
    )

    assert status["server_reachable"] is False
    assert status["server_model_count"] is None
    assert status["server_error"] == "local LLM is disabled"
