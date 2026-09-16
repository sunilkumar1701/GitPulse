/**
 * SourceList — shows data source attribution below assistant messages.
 * Only shown when MCP tools were used.
 */

import { Database } from "lucide-react";

export default function SourceList({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="source-list" aria-label="Data sources">
      <div className="source-list-header">
        <Database size={11} aria-hidden="true" />
        <span>Sources</span>
      </div>
      <ul className="source-list-items">
        {sources.map((source, i) => (
          <li key={i} className="source-item">
            <span className="source-label">{source.label}</span>
            {source.detail && (
              <span className="source-detail">{source.detail}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
