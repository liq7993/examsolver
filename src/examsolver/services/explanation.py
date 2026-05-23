"""Optional student-explanation enhancement layer."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from typing import Any
from urllib import error, request

from examsolver.config import LLMConfig, load_llm_config
from examsolver.contracts import (
    ExplanationEnhancer,
    NormalizedQuestion,
    SolveResult,
    Step,
    StudentExplanation,
)

logger = logging.getLogger(__name__)

_LOCAL_LLM_PROBE_TIMEOUT_SECONDS = 1.5


class NullExplanationEnhancer:
    """Default no-op enhancer used when local LLM is not enabled."""

    name = "null"
    version = "0.1.0"

    def enhance(
        self,
        question: NormalizedQuestion,
        result: SolveResult,
    ) -> StudentExplanation | None:
        return None


class LocalOpenAIExplanationEnhancer:
    """OpenAI-compatible local LLM enhancer, intended for llama-server."""

    name = "local_gguf.gemma4"
    version = "0.1.0"

    def __init__(self, config: LLMConfig) -> None:
        self._config = config

    def enhance(
        self,
        question: NormalizedQuestion,
        result: SolveResult,
    ) -> StudentExplanation | None:
        payload = {
            "model": self._config.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return JSON only. No markdown fences. Chinese. "
                        "Keys: summary, intuition, step_by_step, common_mistake, "
                        "self_check_question. Each string <= 40 Chinese chars. "
                        "step_by_step has at most 2 items. Do not change solver facts."
                    ),
                },
                {"role": "user", "content": _prompt(question, result)},
            ],
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
            "stream": False,
        }
        content = self._post_chat_completion(payload)
        return _student_explanation_from_text(content)

    def _post_chat_completion(self, payload: dict[str, Any]) -> str:
        url = self._config.base_url.rstrip("/") + "/chat/completions"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        http_request = request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with _no_proxy_opener().open(
                http_request,
                timeout=self._config.timeout_seconds,
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError("local LLM request failed") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("local LLM response shape is invalid") from exc
        return str(content)


def build_default_enhancer() -> ExplanationEnhancer:
    """Return the configured enhancer without failing application startup."""

    config = load_llm_config()
    if config.enabled:
        return LocalOpenAIExplanationEnhancer(config)
    return NullExplanationEnhancer()


def enhance_if_needed(
    *,
    question: NormalizedQuestion,
    result: SolveResult,
    enhancer: ExplanationEnhancer,
) -> SolveResult:
    """Fill missing student explanation while preserving solved facts."""

    if result.student_explanation is not None:
        return result

    request_id = str(question.hints.get("request_id", "unknown"))
    try:
        explanation = enhancer.enhance(question, result)
    except Exception as exc:
        logger.warning("[%s] explanation enhancer skipped: %s", request_id, exc)
        return result

    if explanation is None:
        return result

    meta = {
        **result.meta,
        "explanation_enhancer": enhancer.name,
        "explanation_enhancer_version": enhancer.version,
    }
    return replace(result, student_explanation=explanation, meta=meta)


def llm_status() -> dict[str, str | bool | float | int | None]:
    """Return non-network status metadata for the optional local LLM."""

    config = load_llm_config()
    probe = probe_local_llm(config)
    return {
        "provider": config.provider,
        "enabled": config.enabled,
        "base_url": config.base_url,
        "model": config.model,
        "model_path": str(config.model_path) if config.model_path is not None else None,
        "model_path_exists": config.model_path_exists,
        "server_reachable": probe["server_reachable"],
        "server_model_count": probe["server_model_count"],
        "server_error": probe["server_error"],
        "timeout_seconds": config.timeout_seconds,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
    }


def probe_local_llm(config: LLMConfig) -> dict[str, bool | int | str | None]:
    """Probe the OpenAI-compatible local server with a short timeout."""

    if not config.enabled:
        return {
            "server_reachable": False,
            "server_model_count": None,
            "server_error": "local LLM is disabled",
        }

    url = config.base_url.rstrip("/") + "/models"
    http_request = request.Request(url, method="GET")
    try:
        with _no_proxy_opener().open(
            http_request,
            timeout=_LOCAL_LLM_PROBE_TIMEOUT_SECONDS,
        ) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, error.URLError, json.JSONDecodeError) as exc:
        return {
            "server_reachable": False,
            "server_model_count": None,
            "server_error": str(exc),
        }

    models = data.get("data") or data.get("models") or []
    model_count = len(models) if isinstance(models, list) else None
    return {
        "server_reachable": True,
        "server_model_count": model_count,
        "server_error": None,
    }


def _no_proxy_opener() -> request.OpenerDirector:
    return request.build_opener(request.ProxyHandler({}))


def _prompt(question: NormalizedQuestion, result: SolveResult) -> str:
    facts = {
        "question": question.raw_text[:500],
        "subject": question.subject,
        "type": result.question_type,
        "skill": result.skill,
        "success": bool(result.meta.get("success", result.skill != "unknown")),
        "answer": result.answer,
        "steps": [_step_to_text(step) for step in result.steps[:5]],
    }
    return "Explain these ExamSolver facts for a student in Chinese:\n" + json.dumps(
        facts,
        ensure_ascii=False,
    )


def _step_to_text(step: Step) -> str:
    if step.formula_latex:
        return f"{step.description}：${step.formula_latex}$"
    return step.description


def _student_explanation_from_text(content: str) -> StudentExplanation:
    data = _extract_json_object(content)
    if data is None:
        return StudentExplanation(
            summary=content.strip()[:360] or "Gemma 已返回解释，但内容为空。",
            intuition="",
            step_by_step=[],
            common_mistake="",
            self_check_question="",
        )

    return StudentExplanation(
        summary=str(data.get("summary") or ""),
        intuition=str(data.get("intuition") or ""),
        step_by_step=[str(step) for step in data.get("step_by_step", []) if str(step).strip()],
        common_mistake=str(data.get("common_mistake") or ""),
        self_check_question=str(data.get("self_check_question") or ""),
    )


def _extract_json_object(content: str) -> dict[str, Any] | None:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = "\n".join(lines[1:-1]).strip()

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            return None

    return parsed if isinstance(parsed, dict) else None
