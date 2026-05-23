# Examsolver Baseline Data Flow

M0 baseline captured on 2026-05-20. The current code already uses the M1
LangGraph-backed orchestration path: `services.solve_service.solve()` delegates to
`graph.run_solve_graph()`, while the deterministic pipeline modules remain the
business implementation behind graph nodes.

## Current `solve_service.solve()` chain

```mermaid
flowchart LR
    A[HTTP route / CLI script] --> B[SolveRequest]
    B --> C[services.solve_service.solve]
    C --> D[graph.run_solve_graph]
    D --> E[build_graph().invoke]
    E --> F[normalize_node]
    F --> G[router_agent_node]
    G -->|known type| H[skill_node]
    G -->|unknown| I[general_node]
    H --> J[explanation_enhancer_node]
    I --> J
    J --> K[note_builder_node]
    K --> L[format_node]
    L --> M[persist_node]
    M --> N[SolveResponse]
```

## Node-to-module mapping

| Graph node | Wrapped module | M1 status | Future direction |
|---|---|---|---|
| `normalize_node` | `pipeline.normalizer.normalize` | preserved | extend `SolveRequest.image_paths` / OCR text |
| `router_agent_node` | `pipeline.classifier.classify` | graph wrapper added | M2 replaces fallback with LLM router |
| `skill_node` | `pipeline.dispatcher.dispatch_or_unknown` | preserved | keep skills as business center |
| `general_node` | `skills.unknown_skill.UnknownSkill` | placeholder fallback | M2 replaces with `general.cot_with_textbook` |
| `explanation_enhancer_node` | `services.explanation.enhance_if_needed` | preserved | M2 can inject LLM enhancer |
| `note_builder_node` | inline minimal `NoteEntry` builder | M1 added | move to `notes.note_builder` and enrich cards/formulas |
| `format_node` | `pipeline.formatter.format_response` | preserved | preserve public Solve Contract |
| `persist_node` | `storage.history_repo.save_history` | preserved | persistence failure stays non-blocking |

## Preserved boundaries

- `services.solve_service.solve()` keeps the public service signature stable.
- Graph nodes orchestrate only; solving remains in skills and pipeline modules.
- Deterministic skills remain callable without LangGraph, FastAPI, or SQLite.
- `format_response()` is still the only public SolveResponse sealing point.
- History persistence is best-effort; SQLite failure should not fail a solve response.
- Unknown or unsupported questions still return the normal unknown SolveResponse.

## M1 / later modification map

- Already M1-shaped: `graph/build.py`, `graph/nodes.py`, `graph/state.py`, and
  `services/solve_service.py`.
- Keep during M1: `pipeline/normalizer.py`, `pipeline/classifier.py`,
  `pipeline/dispatcher.py`, `pipeline/formatter.py`, existing deterministic skills,
  and `storage/history_repo.py`.
- Replace or extend later: `router_agent_node` in M2, `general_node` in M2,
  multimodal OCR/VLM nodes in M3/M5, RAG nodes in M3, and rich note/card building in M4/M5.
