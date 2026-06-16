"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ApiError, addMistake, getDocxExportUrl, getSolve } from "../../../lib/api";
import type { FormulaCard, NoteEntry, SolveResponse, Step } from "../../../lib/types";
import { MathText } from "../../components/MathText";
import styles from "./note.module.css";

type LoadState =
  | {
      status: "loading";
    }
  | {
      status: "ready";
      response: SolveResponse;
    }
  | {
      status: "not-found";
    }
  | {
      status: "error";
      message: string;
    };

type NotePageClientProps = {
  solveId: string;
};

export function NotePageClient({ solveId }: NotePageClientProps) {
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function loadNote() {
      setLoadState({ status: "loading" });

      try {
        const response = await getSolve(solveId);
        if (!cancelled) {
          setLoadState({ status: "ready", response });
        }
      } catch (error) {
        if (cancelled) return;

        if (error instanceof ApiError && error.status === 404) {
          setLoadState({ status: "not-found" });
          return;
        }

        setLoadState({
          status: "error",
          message: error instanceof Error ? error.message : "题目加载失败，请稍后重试",
        });
      }
    }

    void loadNote();

    return () => {
      cancelled = true;
    };
  }, [solveId]);

  if (loadState.status === "loading") {
    return <NoteScaffold title="正在加载题目" solveId={solveId} />;
  }

  if (loadState.status === "not-found") {
    return (
      <NoteScaffold title="未找到该题" solveId={solveId}>
        <section className={styles.emptyState}>
          <p>未找到该题。请从历史记录重新打开，或返回首页重新求解。</p>
          <Link className={styles.primaryLink} href="/">
            返回工作台
          </Link>
        </section>
      </NoteScaffold>
    );
  }

  if (loadState.status === "error") {
    return (
      <NoteScaffold title="加载失败" solveId={solveId}>
        <section className={styles.emptyState}>
          <p>{loadState.message}</p>
          <Link className={styles.primaryLink} href="/">
            返回工作台
          </Link>
        </section>
      </NoteScaffold>
    );
  }

  return <ReadyNote response={loadState.response} />;
}

function ReadyNote({ response }: { response: SolveResponse }) {
  const note = response.note;
  const title = note?.title || response.message || "单题笔记";
  const questionText = note?.question_latex || response.message || "题目内容暂缺";
  const subjectLabel = response.subject ?? note?.subject ?? "unknown";
  const questionTypeLabel = response.question_type || note?.question_type || "unknown";
  const answerText = formatAnswer(response.answer ?? note?.answer ?? null);
  const steps = useMemo(() => normalizeSteps(note, response), [note, response]);
  const formulas = note?.related_formulas ?? [];
  const fallbackReasons = response.fallback_reasons ?? [];
  const commonMistakes = normalizeCommonMistakes(note, response);

  return (
    <NoteScaffold
      title={title}
      solveId={response.solve_id}
      subject={subjectLabel}
      flashcardCount={note?.flashcards.length ?? 0}
    >
      <article className={styles.noteLayout}>
        <div className={styles.noteMain}>
          {fallbackReasons.length > 0 ? (
            <section className={styles.alertBand}>
              <strong>已诚实降级</strong>
              <span>{fallbackReasons.join(" / ")}</span>
            </section>
          ) : null}

          <section className={styles.heroSection}>
            <div>
              <p className={styles.kicker}>{questionTypeLabel}</p>
              <h1>{title}</h1>
            </div>
            <div className={styles.heroMeta}>
              <span>{subjectLabel}</span>
              <span>{response.skill || "unknown skill"}</span>
            </div>
          </section>

          <NoteSection eyebrow="题目" title="原题">
            <div className={styles.problemText}>
              <MathText text={questionText} />
            </div>
          </NoteSection>

          <NoteSection eyebrow="思路" title="解题直觉">
            <ExplanationContent response={response} />
          </NoteSection>

          <NoteSection eyebrow="步骤" title="推导过程" meta={`${steps.length} 步`}>
            <ol className={styles.stepList}>
              {steps.map((step) => (
                <li key={`${step.index}-${step.description}`} className={styles.stepItem}>
                  <span>{String(step.index).padStart(2, "0")}</span>
                  <div>
                    <p>
                      <MathText text={step.description} />
                    </p>
                    {step.formula_latex ? <MathText text={step.formula_latex} display /> : null}
                  </div>
                </li>
              ))}
            </ol>
          </NoteSection>

          <NoteSection eyebrow="答案" title="最终结果">
            <div className={styles.answerBox}>
              <MathText text={answerText || "暂无答案"} display />
            </div>
          </NoteSection>

          <NoteSection eyebrow="易错点" title="常见误区">
            {commonMistakes.length > 0 ? (
              <ul className={styles.mistakeList}>
                {commonMistakes.map((mistake) => (
                  <li key={mistake}>
                    <MathText text={mistake} />
                  </li>
                ))}
              </ul>
            ) : (
              <p className={styles.mutedText}>这道题暂未生成易错点。</p>
            )}
          </NoteSection>
        </div>

        <FormulaSidebar formulas={formulas} />
      </article>
    </NoteScaffold>
  );
}

function NoteScaffold({
  title,
  solveId,
  subject,
  flashcardCount = 0,
  children,
}: {
  title: string;
  solveId: string;
  subject?: string;
  flashcardCount?: number;
  children?: React.ReactNode;
}) {
  const [mistakeState, setMistakeState] = useState<"idle" | "saving" | "saved" | "error">("idle");

  async function handleAddMistake() {
    setMistakeState("saving");
    try {
      await addMistake(solveId);
      setMistakeState("saved");
    } catch {
      setMistakeState("error");
    }
  }

  return (
    <main className={styles.page}>
      <header className={styles.toolbar}>
        <div className={styles.toolbarLeft}>
          <Link className={styles.toolButton} href="/" title="返回工作台">
            ← 返回
          </Link>
          {subject ? <span className={styles.subjectChip}>{subject}</span> : null}
          <span className={styles.solveId}>{solveId}</span>
        </div>
        <div className={styles.toolbarRight}>
          <button
            className={styles.toolButton}
            type="button"
            disabled={mistakeState === "saving" || mistakeState === "saved"}
            title={mistakeState === "error" ? "加入失败，请稍后重试" : "加入错题本"}
            onClick={() => void handleAddMistake()}
          >
            {mistakeState === "saving" ? "加入中" : mistakeState === "saved" ? "已加入" : "+ 错题"}
          </button>
          <Link className={styles.toolButton} href="/mistakes">
            错题本
          </Link>
          <Link className={styles.toolButton} href={`/flashcards/session/${encodeURIComponent(solveId)}`}>
            练卡片{flashcardCount ? ` ${flashcardCount}` : ""}
          </Link>
          <a
            className={styles.toolButton}
            href={getDocxExportUrl(solveId)}
            title="导出可编辑公式的 Word 文档"
          >
            导出 docx
          </a>
          <button className={styles.primaryToolButton} type="button" onClick={() => window.print()}>
            打印
          </button>
        </div>
      </header>

      {children ?? (
        <section className={styles.loadingShell}>
          <div className={styles.loadingLine} />
          <div className={styles.loadingLineShort} />
          <p>{title}</p>
        </section>
      )}
    </main>
  );
}

function NoteSection({
  eyebrow,
  title,
  meta,
  children,
}: {
  eyebrow: string;
  title: string;
  meta?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={styles.noteSection}>
      <div className={styles.sectionHeader}>
        <div>
          <p>{eyebrow}</p>
          <h2>{title}</h2>
        </div>
        {meta ? <span>{meta}</span> : null}
      </div>
      {children}
    </section>
  );
}

function ExplanationContent({ response }: { response: SolveResponse }) {
  const explanation = response.student_explanation ?? response.note?.student_explanation;

  if (!explanation) {
    return <p className={styles.mutedText}>这道题暂未生成思路说明。</p>;
  }

  return (
    <div className={styles.explanationGrid}>
      {explanation.intuition ? (
        <div>
          <span>Intuition</span>
          <p>
            <MathText text={explanation.intuition} />
          </p>
        </div>
      ) : null}
      {explanation.summary ? (
        <div>
          <span>Summary</span>
          <p>
            <MathText text={explanation.summary} />
          </p>
        </div>
      ) : null}
      {explanation.step_by_step?.length ? (
        <div>
          <span>Checklist</span>
          <ul>
            {explanation.step_by_step.map((item) => (
              <li key={item}>
                <MathText text={item} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function FormulaSidebar({ formulas }: { formulas: FormulaCard[] }) {
  return (
    <aside className={styles.formulaSidebar}>
      <div className={styles.formulaSidebarInner}>
        <p className={styles.kicker}>公式速查</p>
        <h2>Related Formulas</h2>
        {formulas.length > 0 ? (
          <div className={styles.formulaList}>
            {formulas.map((formula) => (
              <section key={`${formula.title}-${formula.formula_latex}`} className={styles.formulaItem}>
                <h3>{formula.title}</h3>
                <MathText text={formula.formula_latex} display />
                <p>
                  <MathText text={formula.explanation} />
                </p>
              </section>
            ))}
          </div>
        ) : (
          <p className={styles.mutedText}>暂无公式卡。</p>
        )}
      </div>
    </aside>
  );
}

function normalizeSteps(note: NoteEntry | null, response: SolveResponse): Step[] {
  if (note?.steps.length) {
    return note.steps;
  }

  return response.steps.map((description, index) => ({
    index: index + 1,
    description,
    formula_latex: null,
    image_hint: null,
  }));
}

function normalizeCommonMistakes(note: NoteEntry | null, response: SolveResponse): string[] {
  const mistakes = [...(note?.common_mistakes ?? [])];
  const generated = response.student_explanation?.common_mistake ?? note?.student_explanation?.common_mistake;

  if (generated && !mistakes.includes(generated)) {
    mistakes.push(generated);
  }

  return mistakes.filter((item) => item.trim().length > 0);
}

function formatAnswer(answer: SolveResponse["answer"] | NoteEntry["answer"]): string {
  if (answer === null || answer === undefined) {
    return "";
  }

  if (typeof answer === "string") {
    return answer;
  }

  return JSON.stringify(answer, null, 2);
}
