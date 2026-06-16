"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { getHistory } from "../../lib/api";
import type { HistoryItem } from "../../lib/types";
import styles from "./history.module.css";

const PAGE_SIZE = 12;
const ALL_SUBJECTS = "all";

type LoadState = "loading" | "ready" | "error";

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [selectedSubject, setSelectedSubject] = useState(ALL_SUBJECTS);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const loadFirstPage = useCallback(async () => {
    setLoadState("loading");
    setErrorMessage("");

    try {
      const page = await getHistory(PAGE_SIZE, 0);
      setItems(sortNewestFirst(page.items));
      setNextOffset(page.next_offset);
      setLoadState("ready");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "历史记录加载失败，请稍后重试");
      setLoadState("error");
    }
  }, []);

  useEffect(() => {
    void loadFirstPage();
  }, [loadFirstPage]);

  const loadMore = useCallback(async () => {
    if (nextOffset === null || isLoadingMore) return;

    setIsLoadingMore(true);
    setErrorMessage("");

    try {
      const page = await getHistory(PAGE_SIZE, nextOffset);
      setItems((currentItems) => mergeHistoryItems(currentItems, page.items));
      setNextOffset(page.next_offset);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "更多历史记录加载失败，请稍后重试");
    } finally {
      setIsLoadingMore(false);
    }
  }, [isLoadingMore, nextOffset]);

  const subjects = useMemo(() => {
    const subjectSet = new Set(items.map((item) => item.subject ?? "unknown"));
    return [...subjectSet].sort((left, right) =>
      subjectLabel(left).localeCompare(subjectLabel(right), "zh-CN"),
    );
  }, [items]);

  const visibleItems = useMemo(
    () =>
      selectedSubject === ALL_SUBJECTS
        ? items
        : items.filter((item) => (item.subject ?? "unknown") === selectedSubject),
    [items, selectedSubject],
  );

  if (loadState === "loading") {
    return <HistoryLoading />;
  }

  if (loadState === "error") {
    return (
      <HistoryShell>
        <StatePanel
          eyebrow="Connection"
          title="暂时读不到历史记录"
          description={errorMessage}
          action={
            <button className={styles.primaryButton} type="button" onClick={() => void loadFirstPage()}>
              重新加载
            </button>
          }
        />
      </HistoryShell>
    );
  }

  return (
    <HistoryShell>
      <section className={styles.intro}>
        <div>
          <p className={styles.eyebrow}>History index</p>
          <h1>历史笔记</h1>
          <p className={styles.introCopy}>按时间回看每一道题，继续整理你的复习路径。</p>
        </div>
        <div className={styles.stats} aria-label="已加载历史统计">
          <strong>{String(items.length).padStart(2, "0")}</strong>
          <span>已加载笔记</span>
        </div>
      </section>

      {items.length === 0 ? (
        <EmptyHistory />
      ) : (
        <>
          <section className={styles.filterBar} aria-label="按学科筛选历史记录">
            <div>
              <p>学科筛选</p>
              <span>当前显示 {visibleItems.length} 条</span>
            </div>
            <div className={styles.chipList}>
              <FilterChip
                active={selectedSubject === ALL_SUBJECTS}
                count={items.length}
                label="全部"
                onClick={() => setSelectedSubject(ALL_SUBJECTS)}
              />
              {subjects.map((subject) => (
                <FilterChip
                  key={subject}
                  active={selectedSubject === subject}
                  count={items.filter((item) => (item.subject ?? "unknown") === subject).length}
                  label={subjectLabel(subject)}
                  onClick={() => setSelectedSubject(subject)}
                />
              ))}
            </div>
          </section>

          {visibleItems.length > 0 ? (
            <section className={styles.historyList} aria-label="历史记录">
              {visibleItems.map((item, index) => (
                <HistoryCard key={item.solve_id} item={item} index={index} />
              ))}
            </section>
          ) : (
            <StatePanel
              eyebrow="Filtered"
              title="这个学科还没有已加载的笔记"
              description={
                nextOffset === null
                  ? "切换到其他学科，或回工作台完成一道新题。"
                  : "可继续加载更早记录，或切换到其他学科。"
              }
              action={
                <button
                  className={styles.secondaryButton}
                  type="button"
                  onClick={() => setSelectedSubject(ALL_SUBJECTS)}
                >
                  查看全部
                </button>
              }
            />
          )}

          <footer className={styles.pagination}>
            <div>
              <p>{nextOffset === null ? "已到达最早一条记录" : "继续翻阅更早的笔记"}</p>
              {errorMessage ? <span role="alert">{errorMessage}</span> : null}
            </div>
            {nextOffset !== null ? (
              <button
                className={styles.primaryButton}
                type="button"
                disabled={isLoadingMore}
                onClick={() => void loadMore()}
              >
                {isLoadingMore ? "正在加载..." : "加载更多"}
              </button>
            ) : null}
          </footer>
        </>
      )}
    </HistoryShell>
  );
}

function HistoryShell({ children }: { children: React.ReactNode }) {
  return (
    <main className={styles.page}>
      <header className={styles.toolbar}>
        <Link className={styles.brand} href="/">
          <span>ES</span>
          <strong>Examsolver</strong>
        </Link>
        <nav aria-label="历史页导航">
          <Link className={styles.toolbarLink} href="/">
            返回工作台
          </Link>
        </nav>
      </header>
      <div className={styles.shell}>{children}</div>
    </main>
  );
}

function HistoryCard({ item, index }: { item: HistoryItem; index: number }) {
  return (
    <Link
      className={styles.historyCard}
      href={`/note/${encodeURIComponent(item.solve_id)}`}
      style={{ "--entrance-index": index } as React.CSSProperties}
    >
      <span className={styles.cardIndex}>{String(index + 1).padStart(2, "0")}</span>
      <div className={styles.cardBody}>
        <div className={styles.cardMeta}>
          <span className={styles.subjectChip}>{subjectLabel(item.subject)}</span>
          <span>{questionTypeLabel(item.question_type)}</span>
          <span>{formatDate(item.created_at)}</span>
        </div>
        <h2>{item.question_snippet || "题目内容暂缺"}</h2>
        <div className={styles.cardFooter}>
          <span className={item.success ? styles.successStatus : styles.fallbackStatus}>
            {item.success ? "已生成笔记" : "已诚实降级"}
          </span>
          <span className={styles.skillName}>{item.skill || "unknown skill"}</span>
        </div>
      </div>
      <span className={styles.cardArrow} aria-hidden="true">
        ↗
      </span>
    </Link>
  );
}

function FilterChip({
  active,
  count,
  label,
  onClick,
}: {
  active: boolean;
  count: number;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className={active ? styles.activeChip : styles.filterChip}
      type="button"
      aria-pressed={active}
      onClick={onClick}
    >
      <span>{label}</span>
      <small>{count}</small>
    </button>
  );
}

function EmptyHistory() {
  return (
    <section className={styles.emptyState}>
      <div className={styles.emptyIllustration} aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div>
        <p className={styles.eyebrow}>Blank notebook</p>
        <h2>这里还没有历史笔记</h2>
        <p>完成第一道题后，它会按时间出现在这里。</p>
        <Link className={styles.primaryButton} href="/">
          去解一道题
        </Link>
      </div>
    </section>
  );
}

function StatePanel({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action: React.ReactNode;
}) {
  return (
    <section className={styles.statePanel}>
      <p className={styles.eyebrow}>{eyebrow}</p>
      <h2>{title}</h2>
      <p>{description}</p>
      {action}
    </section>
  );
}

function HistoryLoading() {
  return (
    <HistoryShell>
      <section className={styles.intro}>
        <div>
          <p className={styles.eyebrow}>History index</p>
          <h1>历史笔记</h1>
          <p className={styles.introCopy}>正在整理你的笔记索引...</p>
        </div>
      </section>
      <section className={styles.loadingList} aria-label="正在加载历史记录">
        {Array.from({ length: 4 }, (_, index) => (
          <div className={styles.loadingCard} key={index}>
            <span />
            <div>
              <span />
              <span />
              <span />
            </div>
          </div>
        ))}
      </section>
    </HistoryShell>
  );
}

function mergeHistoryItems(currentItems: HistoryItem[], incomingItems: HistoryItem[]): HistoryItem[] {
  const byId = new Map(currentItems.map((item) => [item.solve_id, item]));
  incomingItems.forEach((item) => byId.set(item.solve_id, item));
  return sortNewestFirst([...byId.values()]);
}

function sortNewestFirst(items: HistoryItem[]): HistoryItem[] {
  return [...items].sort(
    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
}

function subjectLabel(subject: string | null): string {
  const labels: Record<string, string> = {
    calculus: "高等数学",
    engineering_mechanics: "工程力学",
    general: "通用",
    mechanism: "机械原理",
    tolerance: "公差与测量",
    unknown: "待分类",
  };

  return labels[subject ?? "unknown"] ?? subject ?? labels.unknown;
}

function questionTypeLabel(questionType: string): string {
  return questionType.replaceAll("_", " ");
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "时间未知";

  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}
