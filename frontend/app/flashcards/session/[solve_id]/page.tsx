"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getSolve } from "../../../../lib/api";
import type { Flashcard } from "../../../../lib/types";
import { StudyShell } from "../../../mistakes/MistakesClient";
import styles from "../../../study.module.css";

type SessionPageProps = {
  params: Promise<{
    solve_id: string;
  }>;
};

export default function FlashcardSessionPage({ params }: SessionPageProps) {
  const [solveId, setSolveId] = useState("");
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [known, setKnown] = useState(0);
  const [unknown, setUnknown] = useState(0);
  const current = cards[index];

  useEffect(() => {
    void params.then(({ solve_id: id }) => setSolveId(id));
  }, [params]);

  useEffect(() => {
    if (!solveId) return;
    async function load() {
      const response = await getSolve(solveId);
      setCards(response.note?.flashcards ?? []);
    }
    void load();
  }, [solveId]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.code === "Space") {
        event.preventDefault();
        setFlipped((value) => !value);
      }
      if (event.key === "ArrowRight") mark(true);
      if (event.key === "ArrowLeft") mark(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  const done = useMemo(() => cards.length > 0 && index >= cards.length, [cards.length, index]);

  function mark(isKnown: boolean) {
    if (!current) return;
    if (isKnown) setKnown((value) => value + 1);
    else setUnknown((value) => value + 1);
    setIndex((value) => value + 1);
    setFlipped(false);
  }

  return (
    <StudyShell>
      <section className={styles.intro}>
        <div>
          <p className={styles.eyebrow}>Session</p>
          <h1>卡片练习</h1>
          <p>{cards.length ? `${index + 1}/${cards.length}` : "正在读取卡片"}</p>
        </div>
      </section>
      {cards.length === 0 ? (
        <section className={styles.panel}>
          <h2>暂无卡片</h2>
          <Link className={styles.primaryButton} href="/flashcards">
            返回卡片库
          </Link>
        </section>
      ) : done ? (
        <section className={styles.panel}>
          <p className={styles.eyebrow}>Finished</p>
          <h2>会 {known} / 不会 {unknown}</h2>
          <Link className={styles.primaryButton} href="/flashcards">
            回到卡片库
          </Link>
        </section>
      ) : (
        <section className={styles.sessionCard} onClick={() => setFlipped((value) => !value)}>
          <span className={`${styles.chip} ${styles.cardType}`}>{current.card_type}</span>
          <p className={styles.cardFace}>{flipped ? current.back : current.front}</p>
          <div className={styles.sessionStats}>
            <span>Space 翻面</span>
            <span>← 不会</span>
            <span>→ 会</span>
          </div>
          <div className={styles.actions}>
            <button className={styles.secondaryButton} type="button" onClick={() => mark(false)}>
              不会
            </button>
            <button className={styles.primaryButton} type="button" onClick={() => mark(true)}>
              会
            </button>
          </div>
        </section>
      )}
    </StudyShell>
  );
}
