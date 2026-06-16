"use client";

import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { formatSubmitLabel, workbenchCopy } from "./solveWorkbenchCopy";
import styles from "./SolveWorkbench.module.css";

type SolveWorkbenchComposerProps = {
  question: string;
  attachments: File[];
  subject: string;
  subjects: Array<{ label: string; value: string }>;
  isSubmitting: boolean;
  onAttachmentsChange: (files: File[]) => void;
  onQuestionChange: (question: string) => void;
  onSubjectChange: (subject: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  onUseExample: () => void;
};

export function SolveWorkbenchComposer({
  question,
  attachments,
  subject,
  subjects,
  isSubmitting,
  onAttachmentsChange,
  onQuestionChange,
  onSubjectChange,
  onSubmit,
  onUseExample,
}: SolveWorkbenchComposerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [previews, setPreviews] = useState<Array<{ file: File; url: string }>>([]);

  useEffect(() => {
    const nextPreviews = attachments.map((file) => ({ file, url: URL.createObjectURL(file) }));
    setPreviews(nextPreviews);
    return () => nextPreviews.forEach((preview) => URL.revokeObjectURL(preview.url));
  }, [attachments]);

  function handleTextareaKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (files.length === 0) return;
    onAttachmentsChange([...attachments, ...files].slice(0, 3));
  }

  const busy = isSubmitting;

  return (
    <div className={styles.composerBar}>
      <form className={styles.composerInner} onSubmit={onSubmit}>
        {previews.length > 0 ? (
          <div className={styles.attachmentList} aria-label="已附图片">
            {previews.map((preview, index) => (
              <figure className={styles.attachmentPreview} key={`${preview.file.name}-${index}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={preview.url} alt={preview.file.name} />
                <button
                  type="button"
                  aria-label={`移除 ${preview.file.name}`}
                  onClick={() => onAttachmentsChange(attachments.filter((_, itemIndex) => itemIndex !== index))}
                >
                  ×
                </button>
              </figure>
            ))}
          </div>
        ) : null}
        <div className={styles.composerRow}>
          <textarea
            value={question}
            onChange={(e) => onQuestionChange(e.target.value)}
            onKeyDown={handleTextareaKeyDown}
            className={styles.textarea}
            rows={1}
            placeholder={workbenchCopy.header.placeholder}
          />
          <div className={styles.composerTools}>
            <button
              type="button"
              className={styles.iconButton}
              title="附加题目图片（最多 3 张）"
              onClick={() => fileInputRef.current?.click()}
              disabled={busy}
              aria-label="上传图片"
            >
              📎
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif,image/bmp"
              multiple
              style={{ display: "none" }}
              onChange={handleFileChange}
            />
            <button
              type="submit"
              className={styles.primaryButton}
              disabled={busy}
              title={formatSubmitLabel(isSubmitting)}
            >
              {isSubmitting ? "…" : "↑"}
            </button>
          </div>
        </div>

        <div className={styles.composerActions}>
          <label className={styles.subjectSelectLabel}>
            <span>学科</span>
            <select value={subject} onChange={(event) => onSubjectChange(event.target.value)} disabled={busy}>
              <option value="">自动判断</option>
              {subjects.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className={styles.secondaryButton}
            disabled={busy}
            onClick={onUseExample}
          >
            {workbenchCopy.header.exampleButton}
          </button>
        </div>
      </form>
    </div>
  );
}
