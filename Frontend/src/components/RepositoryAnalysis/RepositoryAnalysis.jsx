import { useEffect, useState } from "react";
import "./RepositoryAnalysis.css";

import { FolderGit2, Star, GitFork, Trophy, Link2 } from "lucide-react";

import { useDashboardContext } from "../../context/DashboardContext";
import { getRepositoryAnalysis } from "../../services/githubService";

const RepositoryAnalysis = ({ username, onLoaded, refreshKey }) => {
  const { updateDashboardData } = useDashboardContext();

  const [state, setState] = useState({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let mounted = true;

    const fetchRepositoryAnalysis = async () => {
      try {
        console.log("🔄 Refetching RepositoryAnalysis");

        const data = await getRepositoryAnalysis(username);

        if (!mounted) return;

        setState({
          data,
          loading: false,
          error: null,
        });

        updateDashboardData("repositoryAnalysis", data);

        console.log("✅ RepositoryAnalysis Loaded");

        onLoaded?.();
      } catch (error) {
        console.error("Repository Analysis Error:", error);

        if (!mounted) return;

        setState({
          data: null,
          loading: false,
          error: "Unable to load repository analysis.",
        });
      }
    };

    fetchRepositoryAnalysis();

    return () => {
      mounted = false;
    };
  }, [username, refreshKey, updateDashboardData, onLoaded]);

  const { data: repositoryStats, loading, error } = state;

  if (loading || error) {
    const isError = !!error;
    const skeletonClass = isError ? "skeleton-error" : "skeleton";
    return (
      <div className="repository-analysis" style={{ position: 'relative' }}>
        <div className={`repo-analysis-card ${skeletonClass} skeleton-box`}></div>
        <div className={`repo-analysis-card ${skeletonClass} skeleton-box`}></div>
        <div className={`repo-analysis-card ${skeletonClass} skeleton-box`}></div>
        <div className={`repo-analysis-card top-repo-card ${skeletonClass} skeleton-box`}></div>
        {isError && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyItems: 'center', justifyContent: 'center', padding: '16px', zIndex: 10 }}>
            <span style={{ color: 'var(--danger-main)', fontWeight: 600, textAlign: 'center', background: 'var(--bg-card)', padding: '4px 12px', borderRadius: '8px' }}>
              {error}
            </span>
          </div>
        )}
      </div>
    );
  }

  const topRepo = repositoryStats?.top_repo;

  return (
    <div className="repository-analysis">
      {/* Repositories */}

      <div className="repo-analysis-card">
        <div className="repo-analysis-header">
          <FolderGit2 size={18} color="#60A5FA" />

          <span>Repositories</span>
        </div>

        <h2>{repositoryStats?.total_repos ?? 0}</h2>
      </div>

      {/* Stars */}

      <div className="repo-analysis-card">
        <div className="repo-analysis-header">
          <Star size={18} color="#FACC15" />

          <span>Total Stars</span>
        </div>

        <h2>{repositoryStats?.total_stars ?? 0}</h2>
      </div>

      {/* Forks */}

      <div className="repo-analysis-card">
        <div className="repo-analysis-header">
          <GitFork size={18} color="#A855F7" />

          <span>Total Forks</span>
        </div>

        <h2>{repositoryStats?.total_forks ?? 0}</h2>
      </div>

      {/* Top Repository */}

      <div className="repo-analysis-card top-repo-card">
        <div className="repo-analysis-header">
          <Trophy size={18} color="#F59E0B" />

          <span>Top Repository</span>

          <div className="tooltip-container">
            ⓘ
            <div className="repo-tooltip">
              <strong>Top Repository</strong>
              <br />
              • Highest stars
              <br />
              • If tied → Highest forks
              <br />• If still tied → Most recently updated
            </div>
          </div>
        </div>

        {topRepo ? (
          <>
            <a
              href={topRepo.html_url}
              target="_blank"
              rel="noopener noreferrer"
              className="top-repo-link"
            >
              <Link2 size={14} color="#94A3B8" />

              <span >{topRepo.name}</span>
            </a>

            <div className="top-repo-stats">
              <div className="repo-stat-item">
                <Star size={14} color="#FACC15" />

                <span>{topRepo.stars ?? 0}</span>
              </div>

              <div className="repo-stat-item">
                <GitFork size={14} color="#CBD5E1" />

                <span>{topRepo.forks ?? 0}</span>
              </div>
            </div>
          </>
        ) : (
          <div
            style={{
              color: "#94A3B8",
              marginTop: "12px",
            }}
          >
            No repository found.
          </div>
        )}
      </div>
    </div>
  );
};

export default RepositoryAnalysis;
