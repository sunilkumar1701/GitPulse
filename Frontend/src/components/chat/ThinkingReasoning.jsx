import styles from "./ThinkingReasoning.module.css";
import { useEffect, useRef, useState } from "react";

const SENT_H = 20;
const GAP = 4;
const MAX_H = 180;
const FADE = 16;

export default function ThinkingReasoning({ activities = [], isActive = false }) {
  const [open, setOpen] = useState(false);
  const [fade, setFade] = useState({ top: false, bottom: true });
  const [elapsed, setElapsed] = useState(0);
  const viewportRef = useRef(null);

  const done = !isActive;
  const expanded = done ? open : true;
  const count = activities.length;

  const contentH = count > 0 ? count * SENT_H + (count - 1) * GAP : 0;
  const capped = contentH > MAX_H;
  const viewH = capped ? MAX_H : contentH;
  const scrollable = done && open;
  const translate = scrollable ? 0 : capped ? MAX_H - FADE - contentH : 0;

  useEffect(() => {
    if (!isActive) return;
    const interval = setInterval(() => {
      setElapsed((e) => e + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [isActive]);

  const showTop = scrollable ? fade.top : capped;
  const showBottom = scrollable ? fade.bottom : capped;
  const mask = capped
    ? `linear-gradient(to bottom, transparent 0, #000 ${showTop ? FADE : 0}px, #000 calc(100% - ${showBottom ? FADE : 0}px), transparent 100%)`
    : "none";

  const onScroll = () => {
    const el = viewportRef.current;
    if (!el) return;
    setFade({
      top: el.scrollTop > 1,
      bottom: el.scrollTop + el.clientHeight < el.scrollHeight - 1,
    });
  };

  const toggle = () => {
    const next = !open;
    if (next) {
      setFade({ top: false, bottom: true });
      if (viewportRef.current) viewportRef.current.scrollTop = 0;
    }
    setOpen(next);
  };

  if (!activities || activities.length === 0) return null;

  return (
    <div className={styles.tr}>
      <button
        type="button"
        className={styles.trHeader + (done ? " " + styles.isClickable : "")}
        aria-expanded={expanded}
        aria-label="Toggle thought"
        onClick={done ? toggle : undefined}
      >
        {done ? (
          <span className={styles.trLabel}>
            <span className={styles.trVerb}>Thought</span> for {elapsed}s
          </span>
        ) : (
          <span className={styles.trLabel + " " + styles.trShimmer}>Thinking…</span>
        )}
        {done && (
          <svg className={styles.trChevron} viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
            <path d="m4.5 15.75 7.5-7.5 7.5 7.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </button>

      <div className={styles.trCollapsible + (expanded ? "" : " " + styles.isCollapsed)}>
        <div className={styles.trInner}>
          <div
            ref={viewportRef}
            className={styles.trViewport + (scrollable ? " " + styles.isScroll : "")}
            style={{ height: `${viewH}px`, WebkitMaskImage: mask, maskImage: mask }}
            onScroll={scrollable ? onScroll : undefined}
          >
            <div className={styles.trStream} style={{ transform: `translateY(${translate}px)` }}>
              {activities.map((step, i) => (
                <p key={i} className={styles.trSentence}>{step.label}</p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
