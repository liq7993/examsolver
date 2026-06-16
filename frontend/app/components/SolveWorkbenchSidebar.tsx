import Link from "next/link";
import type { SidebarViewModel } from "./solveWorkbenchViewModel";
import { workbenchCopy } from "./solveWorkbenchCopy";
import styles from "./SolveWorkbench.module.css";

type SolveWorkbenchSidebarProps = {
  sidebar: SidebarViewModel;
  onSelectHistory: (solveId: string) => void;
  onNewThread: () => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

export function SolveWorkbenchSidebar({
  sidebar,
  onSelectHistory,
  onNewThread,
  collapsed,
  onToggleCollapsed,
}: SolveWorkbenchSidebarProps) {
  return (
    <aside className={`${styles.sidebar} ${collapsed ? styles.sidebarCollapsed : ""}`}>
      <div className={styles.sidebarHead}>
        <Link href="/" className={styles.brandLink}>
          {collapsed ? "E" : "ExamSolver"}
        </Link>
        <button
          type="button"
          className={styles.sidebarToggleBtn}
          onClick={onToggleCollapsed}
          aria-label={collapsed ? "展开侧边栏" : "压缩侧边栏"}
          title={collapsed ? "展开侧边栏" : "压缩侧边栏"}
        >
          {collapsed ? "›" : "‹"}
        </button>
        <button type="button" className={styles.newThreadBtn} onClick={onNewThread}>
          <span className={styles.newThreadIcon}>＋</span>
          {!collapsed ? "新对话" : null}
        </button>
      </div>

      {!collapsed ? <div className={styles.sidebarScroll}>
        <Link href="/history" className={styles.historyPageLink}>
          <span>历史笔记</span>
          <strong>查看全部</strong>
        </Link>

        {sidebar.historyGroups.length > 0 && (
          <>
            <p className={styles.sidebarGroupLabel}>{workbenchCopy.sections.recentHistory}</p>
            <div className={styles.historyTree}>
              {sidebar.historyGroups.map((subjectGroup) => (
                <details key={subjectGroup.id} className={styles.historySubjectGroup} open>
                  <summary>{subjectGroup.label}</summary>
                  <div className={styles.historyTypeList}>
                    {subjectGroup.typeGroups.map((typeGroup) => (
                      <details key={typeGroup.id} className={styles.historyTypeGroup} open>
                        <summary>{typeGroup.label}</summary>
                        <div className={styles.historyList}>
                          {typeGroup.items.map((item) => (
                            <button
                              key={item.id}
                              type="button"
                              className={styles.historyItem}
                              onClick={() => onSelectHistory(item.solveId)}
                            >
                              <strong>{item.archiveTitle}</strong>
                              <span>{item.timeLabel}</span>
                            </button>
                          ))}
                        </div>
                      </details>
                    ))}
                  </div>
                </details>
              ))}
            </div>
          </>
        )}

        {sidebar.statusRows.length > 0 && (
          <>
            <p className={styles.sidebarGroupLabel} style={{ marginTop: 20 }}>
              {workbenchCopy.sections.status}
            </p>
            <div className={styles.metaList}>
              {sidebar.statusRows.map((row) => (
                <div key={row.id} className={styles.metaRow}>
                  <span>{row.label}</span>
                  <strong>{row.value}</strong>
                </div>
              ))}
            </div>
          </>
        )}
      </div> : null}
    </aside>
  );
}
