/**
 * PullRequestCard — rich GitHub pull request card.
 */

import { GitPullRequest, GitMerge, XCircle, ExternalLink } from "lucide-react";

export default function PullRequestCard({ pr }) {
  if (!pr) return null;

  const {
    number,
    title,
    state,
    merged,
    created_at,
    updated_at,
    html_url,
    draft,
  } = pr;

  const isMerged = merged || state === "merged";
  const isClosed = state === "closed" && !isMerged;
  const isOpen = state === "open";

  const createdDate = created_at
    ? new Date(created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : null;

  const statusLabel = isMerged ? "Merged" : isClosed ? "Closed" : draft ? "Draft" : "Open";
  const statusClass = isMerged ? "badge-merged" : isClosed ? "badge-closed" : "badge-open";

  return (
    <div
      className={`github-card pr-card`}
      role="article"
      aria-label={`Pull Request #${number}: ${title}`}
    >
      <div className="github-card-header">
        {isMerged ? (
          <GitMerge size={13} className="pr-merged-icon" aria-label="Merged PR" />
        ) : isClosed ? (
          <XCircle size={13} className="issue-closed-icon" aria-label="Closed PR" />
        ) : (
          <GitPullRequest size={13} className="issue-open-icon" aria-label="Open PR" />
        )}
        <span className="github-card-number">#{number}</span>
        <span className="github-card-name">{title}</span>
        {html_url && (
          <a
            href={html_url}
            target="_blank"
            rel="noopener noreferrer"
            className="github-card-link"
            aria-label={`Open PR #${number} on GitHub`}
          >
            <ExternalLink size={12} />
          </a>
        )}
      </div>

      <div className="github-card-meta">
        <span className={`github-card-badge ${statusClass}`}>{statusLabel}</span>
        {createdDate && (
          <span className="github-card-date">Opened {createdDate}</span>
        )}
      </div>
    </div>
  );
}
