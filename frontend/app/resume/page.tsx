import Link from "next/link";
import styles from "./page.module.css";

const resumeItems = [
  {
    label: "最近页面",
    value: "康奈尔笔记 / 工作区",
  },
  {
    label: "最近动作",
    value: "重做了解题前端入口，回到更克制的工作区布局。",
  },
  {
    label: "下一步",
    value: "继续补更多题型，再决定哪些后端信息值得暴露。",
  },
];

export default function ResumePage() {
  return (
    <main className={styles.page}>
      <section className={styles.shell}>
        <header className={styles.topbar}>
          <div>
            <p className={styles.wordmark}>ExamSolver</p>
            <p className={styles.topline}>恢复会话</p>
          </div>
          <nav className={styles.nav} aria-label="恢复会话导航">
            <Link href="/">首页</Link>
            <Link href="/workspace">工作区</Link>
          </nav>
        </header>

        <section className={styles.panel}>
          <p className={styles.kicker}>恢复</p>
          <h1 className={styles.title}>继续当前会话</h1>
          <p className={styles.lead}>
            这里保留最近一次工作状态的摘要入口，方便回到当前解题页面继续处理。
          </p>

          <div className={styles.timeline}>
            {resumeItems.map((item) => (
              <div key={item.label} className={styles.timelineRow}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>

          <div className={styles.actions}>
            <Link href="/workspace" className={styles.primaryAction}>
              返回工作区
            </Link>
            <Link href="/" className={styles.secondaryAction}>
              返回首页
            </Link>
          </div>
        </section>
      </section>
    </main>
  );
}
