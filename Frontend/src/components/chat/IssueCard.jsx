/**
 * IssueCard — rich GitHub issue card.
 */

import { Circle, CheckCircle, ExternalLink, AlertCircle } from "lucide-react";

export default function IssueCard({ issue }) {
  if (!issue) return null;

  const {
    number,
    title,
    state,
    created_at,
    html_url,
    labels,
  } = issue;

  const isOpen = state === "open";
  const createdDate = created_at
    ? new Date(created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : null;

  return (
    <div
      className={`github-card issue-card ${isOpen ? "issue-open" : "issue-closed"}`}
      role="article"
      aria-label={`Issue #${number}: ${title}`}
    >
      <div className="github-card-header">
        {isOpen ? (
          <AlertCircle size={13} className="issue-open-icon" aria-label="Open issue" />
        ) : (
          <CheckCircle size={13} className="issue-closed-icon" aria-label="Closed issue" />
        )}
        <span className="github-card-number">#{number}</span>
        <span className="github-card-name">{title}</span>
        {html_url && (
          <a
            href={html_url}
            target="_blank"
            rel="noopener noreferrer"
            className="github-card-link"
            aria-label={`Open issue #${number} on GitHub`}
          >
            <ExternalLink size={12} />
          </a>
        )}
      </div>

      <div className="github-card-meta">
        <span className={`github-card-badge ${isOpen ? "badge-open" : "badge-closed"}`}>
          {isOpen ? "Open" : "Closed"}
        </span>
        {createdDate && (
          <span className="github-card-date">Opened {createdDate}</span>
        )}
        {Array.isArray(labels) && labels.slice(0, 3).map((label) => (
          <span
            key={label.name || label}
            className="github-label-tag"
            style={{ backgroundColor: `#${label.color || "555"}22`, borderColor: `#${label.color || "555"}55` }}
          >
            {label.name || label}
          </span>
        ))}
      </div>
    </div>
  );
}
