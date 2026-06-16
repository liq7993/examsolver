"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  deleteMistake,
  getMistakes,
  getMistakesExportUrl,
  updateMistakeNote,
} from "../../lib/api";
import type { MistakeEntry } from "../../lib/types";
import styles from "../study.module.css";

type LoadState = "loading" | "ready" | "error";

export function MistakesClient({ subject }: { subject?: string }) {
  const [items, setItems] = useState<MistakeEntry[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [errorMessage, setErrorMessage] = useState("");

  const load = useCallback(async () => {
    setLoadState("loading");
    setErrorMessage("");
    try {
      setItems(await getMistakes(subject));
      setLoadState("ready");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "错题本加载失败");
      setLoadState("error");
    }
  }, [subject]);

  useEffect(() => {
    void load();
  }, [load]);

  const grouped = useMemo(() => groupBySubject(items), [items]);

  return (
    <StudyShell>
      <section className={styles.intro}>
        <div>
          <p className={styles.eyebrow}>Mistake book</p>
          <h1>{subject ? subjectLabel(subject) : "错题本"}</h1>
          <p>按学科回收薄弱题，保留批注和复盘入口。</p>
        </div>
        <a className={styles.primaryButton} href={getMistakesExportUrl(subject)}>
          批量导出
        </a>
      </section>

      {loadState === "loading" ? <StatePanel title="正在加载错题" /> : null}
      {loadState === "error" ? (
        <StatePanel title="暂时读不到错题本" body={errorMessage} action={load} />
      ) : null}
      {loadState === "ready" && items.length === 0 ? (
        <StatePanel title="错题本为空" body="在笔记页点击 + 错题后，这里会按学科归档。" />
      ) : null}
      {loadState === "ready"
        ? Object.entries(grouped).map(([groupSubject, entries]) => (
            <section className={styles.panel} key={groupSubject}>
              <div className={styles.intro}>
                <div>
                  <p className={styles.eyebrow}>{groupSubject}</p>
                  <h2>{subjectLabel(groupSubject)}</h2>
                </div>
                {!subject ? (
                  <Link className={styles.secondaryButton} href={`/mistakes/${groupSubject}`}>
                    只看此学科
                  </Link>
                ) : null}
              </div>
              <div className={styles.list}>
                {entries.map((entry) => (
                  <MistakeRow key={entry.id} entry={entry} onChanged={load} />
                ))}
              </div>
            </section>
          ))
        : null}
    </StudyShell>
  );
}

function MistakeRow({ entry, onChanged }: { entry: MistakeEntry; onChanged: () => void }) {
  const [note, setNote] = useState(entry.user_note ?? "");
  const [saving, setSaving] = useState(false);

  async function saveNote() {
    setSaving(true);
    await updateMistakeNote(entry.id, note);
    setSaving(false);
    onChanged();
  }

  async function remove() {
    await deleteMistake(entry.id);
    onChanged();
  }

  return (
    <article className={styles.row}>
      <div>
        <div className={styles.meta}>
          <span className={styles.chip}>{subjectLabel(entry.subject)}</span>
          <span className={styles.muted}>{entry.question_type}</span>
        </div>
        <h2>{entry.solve_id}</h2>
        <textarea
          className={styles.noteInput}
          value={note}
          placeholder="添加复盘批注"
          onChange={(event) => setNote(event.target.value)}
        />
      </div>
      <div className={styles.actions}>
        <Link className={styles.secondaryButton} href={`/note/${entry.solve_id}`}>
          打开笔记
        </Link>
        <button className={styles.primaryButton} type="button" disabled={saving} onClick={saveNote}>
          {saving ? "保存中" : "保存批注"}
        </button>
        <button className={styles.secondaryButton} type="button" onClick={remove}>
          移除
        </button>
      </div>
    </article>
  );
}

export function StudyShell({ children }: { children: React.ReactNode }) {
  return (
    <main className={styles.page}>
      <header className={styles.toolbar}>
        <Link className={styles.brand} href="/">
          <span>ES</span>
          <strong>Examsolver</strong>
        </Link>
        <nav>
          <Link className={styles.toolbarLink} href="/history">
            历史
          </Link>
          <Link className={styles.toolbarLink} href="/mistakes">
            错题本
          </Link>
          <Link className={styles.toolbarLink} href="/flashcards">
            卡片
          </Link>
        </nav>
      </header>
      <div className={styles.shell}>{children}</div>
    </main>
  );
}

function StatePanel({ title, body, action }: { title: string; body?: string; action?: () => void }) {
  return (
    <section className={styles.panel}>
      <p className={styles.eyebrow}>Status</p>
      <h2>{title}</h2>
      {body ? <p className={styles.muted}>{body}</p> : null}
      {action ? (
        <button className={styles.primaryButton} type="button" onClick={() => void action()}>
          重新加载
        </button>
      ) : null}
    </section>
  );
}

function groupBySubject(items: MistakeEntry[]): Record<string, MistakeEntry[]> {
  return items.reduce<Record<string, MistakeEntry[]>>((groups, item) => {
    const key = item.subject || "unknown";
    groups[key] = [...(groups[key] ?? []), item];
    return groups;
  }, {});
}

function subjectLabel(subject: string): string {
  const labels: Record<string, string> = {
    calculus: "高等数学",
    mechanics: "工程力学",
    mechanism: "机械原理",
    tolerance: "公差与测量",
    general: "通用",
    unknown: "待分类",
  };
  return labels[subject] ?? subject;
}
