"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  getCapabilities,
  getHistory,
  solve as solveQuestion,
  uploadSolveImage,
} from "../../lib/api";
import { SolveWorkbenchComposer } from "./SolveWorkbenchComposer";
import { SolveWorkbenchSidebar } from "./SolveWorkbenchSidebar";
import { workbenchCopy } from "./solveWorkbenchCopy";
import {
  toCapabilityViewModel,
  toHistoryItemViewModels,
  toSidebarViewModel,
  type CapabilityViewModel,
  type HistoryItemViewModel,
} from "./solveWorkbenchViewModel";
import styles from "./SolveWorkbench.module.css";

type SolveWorkbenchProps = {
  mode: "home" | "workspace";
  initialQuery?: string;
};

const EXAMPLE_QUESTION = workbenchCopy.exampleQuestion;

export function SolveWorkbench({ mode, initialQuery }: SolveWorkbenchProps) {
  const router = useRouter();
  const initialText = initialQuery?.trim() || EXAMPLE_QUESTION;
  const [question, setQuestion] = useState(initialText);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [subject, setSubject] = useState("");
  const [historyItems, setHistoryItems] = useState<HistoryItemViewModel[]>([]);
  const [capabilityData, setCapabilityData] = useState<CapabilityViewModel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);

  const sidebar = useMemo(
    () =>
      toSidebarViewModel({
        capability: capabilityData,
        solveMeta: null,
        historyItems,
      }),
    [capabilityData, historyItems],
  );

  const refreshHistory = useCallback(async () => {
    const payload = await getHistory(20, 0);
    setHistoryItems(toHistoryItemViewModels(payload.items));
  }, []);

  const refreshCapabilities = useCallback(async () => {
    const payload = await getCapabilities();
    setCapabilityData(toCapabilityViewModel(payload));
  }, []);

  const runSolve = useCallback(
    async (nextQuestion: string) => {
      const trimmed = nextQuestion.trim();
      if (!trimmed) {
        setError(workbenchCopy.errors.emptyQuestion);
        return;
      }

      setIsSubmitting(true);
      setError(null);

      try {
        const imagePaths = await Promise.all(attachments.map(uploadSolveImage));
        const response = await solveQuestion(trimmed, imagePaths, subject);
        await refreshHistory().catch(() => undefined);
        router.push(`/note/${response.solve_id}`);
      } catch (solveError) {
        setError(solveError instanceof Error ? solveError.message : workbenchCopy.errors.solveFailed);
      } finally {
        setIsSubmitting(false);
      }
    },
    [attachments, refreshHistory, router, subject],
  );

  useEffect(() => {
    if (mode !== "workspace") return;
    void refreshCapabilities().catch(() => setCapabilityData(null));
    void refreshHistory().catch(() => undefined);
  }, [mode, refreshCapabilities, refreshHistory]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runSolve(question);
  }

  function handleNewThread() {
    setQuestion(EXAMPLE_QUESTION);
    setAttachments([]);
    setSubject("");
    setError(null);
  }

  if (mode !== "workspace") return null;

  return (
    <main className={styles.page}>
      <div className={`${styles.shell} ${isSidebarCollapsed ? styles.shellSidebarCollapsed : ""}`}>
        <SolveWorkbenchSidebar
          sidebar={sidebar}
          onSelectHistory={(solveId) => router.push(`/note/${solveId}`)}
          onNewThread={handleNewThread}
          collapsed={isSidebarCollapsed}
          onToggleCollapsed={() => setIsSidebarCollapsed((value) => !value)}
        />

        <section className={styles.workspace}>
          {isSidebarCollapsed ? (
            <button
              type="button"
              className={styles.focusModeToggle}
              onClick={() => setIsSidebarCollapsed(false)}
              title="展开侧边栏"
            >
              ☰
            </button>
          ) : null}

          <div className={styles.workspaceContent}>
            <div className={styles.emptyPage}>
              {isSubmitting ? (
                <div className={styles.solveProgress} role="status" aria-live="polite">
                  <span />
                  <span />
                  <span />
                  <p>{workbenchCopy.messages.loadingWorkspace}</p>
                </div>
              ) : (
                <p className={styles.emptyPageText}>{workbenchCopy.messages.emptyWorkspace}</p>
              )}
            </div>
          </div>

          {error ? <p className={styles.composerError}>{error}</p> : null}
          <SolveWorkbenchComposer
            question={question}
            attachments={attachments}
            subject={subject}
            subjects={capabilityData?.subjects ?? []}
            isSubmitting={isSubmitting}
            onAttachmentsChange={setAttachments}
            onQuestionChange={setQuestion}
            onSubjectChange={setSubject}
            onSubmit={handleSubmit}
            onUseExample={() => {
              setQuestion(EXAMPLE_QUESTION);
              void runSolve(EXAMPLE_QUESTION);
            }}
          />
        </section>
      </div>
    </main>
  );
}
