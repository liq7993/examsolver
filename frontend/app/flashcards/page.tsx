"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getHistory, getSolve } from "../../lib/api";
import type { SolveResponse } from "../../lib/types";
import { StudyShell } from "../mistakes/MistakesClient";
import styles from "../study.module.css";

export default function FlashcardsPage() {
  const [solves, setSolves] = useState<SolveResponse[]>([]);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const history = await getHistory(30, 0);
        const loaded = await Promise.all(history.items.map((item) => getSolve(item.solve_id)));
        setSolves(loaded.filter((solve) => (solve.note?.flashcards.length ?? 0) > 0));
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : "卡片加载失败");
      }
    }
    void load();
  }, []);

  return (
    <StudyShell>
      <section className={styles.intro}>
        <div>
          <p className={styles.eyebrow}>Flashcards</p>
          <h1>突击卡片</h1>
          <p>从已生成笔记中抽取公式、概念和陷阱卡。</p>
        </div>
      </section>
      {errorMessage ? <section className={styles.panel}>{errorMessage}</section> : null}
      {!errorMessage && solves.length === 0 ? (
        <section className={styles.panel}>
          <p className={styles.eyebrow}>Empty</p>
          <h2>暂无卡片</h2>
          <p className={styles.muted}>完成一道题并生成卡片后，这里会出现练习入口。</p>
        </section>
      ) : null}
      <section className={styles.list}>
        {solves.map((solve) => (
          <Link className={styles.row} key={solve.solve_id} href={`/flashcards/session/${solve.solve_id}`}>
            <div>
              <div className={styles.meta}>
                <span className={styles.chip}>{solve.subject ?? "unknown"}</span>
                <span className={styles.muted}>{solve.question_type}</span>
              </div>
              <h2>{solve.note?.title ?? solve.solve_id}</h2>
            </div>
            <span className={styles.primaryButton}>{solve.note?.flashcards.length ?? 0} 张</span>
          </Link>
        ))}
      </section>
    </StudyShell>
  );
}
