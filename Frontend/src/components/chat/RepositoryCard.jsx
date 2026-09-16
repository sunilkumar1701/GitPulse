/**
 * RepositoryCard — rich GitHub repository card.
 */

import { Star, GitFork, ExternalLink, Code } from "lucide-react";

export default function RepositoryCard({ repo }) {
  if (!repo) return null;

  const {
    name,
    full_name,
    description,
    stargazers_count,
    forks_count,
    language,
    updated_at,
    html_url,
  } = repo;

  const updatedDate = updated_at
    ? new Date(updated_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : null;

  return (
    <div className="github-card repo-card" role="article" aria-label={`Repository: ${name || full_name}`}>
      <div className="github-card-header">
        <Code size={13} className="github-card-icon" aria-hidden="true" />
        <span className="github-card-name">{name || full_name}</span>
        {html_url && (
          <a
            href={html_url}
            target="_blank"
            rel="noopener noreferrer"
            className="github-card-link"
            aria-label={`Open ${name} on GitHub`}
          >
            <ExternalLink size={12} />
          </a>
        )}
      </div>

      {description && <p className="github-card-desc">{description}</p>}

      <div className="github-card-meta">
        {language && (
          <span className="github-card-tag">
            <span className="lang-dot" aria-hidden="true" />
            {language}
          </span>
        )}
        {typeof stargazers_count === "number" && (
          <span className="github-card-stat" aria-label={`${stargazers_count} stars`}>
            <Star size={11} aria-hidden="true" />
            {stargazers_count.toLocaleString()}
          </span>
        )}
        {typeof forks_count === "number" && (
          <span className="github-card-stat" aria-label={`${forks_count} forks`}>
            <GitFork size={11} aria-hidden="true" />
            {forks_count.toLocaleString()}
          </span>
        )}
        {updatedDate && (
          <span className="github-card-date">Updated {updatedDate}</span>
        )}
      </div>
    </div>
  );
}
