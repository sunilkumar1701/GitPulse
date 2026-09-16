import "./MostStarredRepo.css";

import { useEffect, useState, useCallback } from "react";

import { FaStar, FaCodeBranch } from "react-icons/fa";

import { useDashboardContext } from "../../context/DashboardContext";
import { getMostStarredRepository } from "../../services/githubService";

const MostStarredRepo = ({ username, onLoaded, refreshKey }) => {
  const { updateDashboardData } = useDashboardContext();

  const [repo, setRepo] = useState(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState(null);

  const fetchRepository = useCallback(
    async (isMounted) => {
      try {
        setLoading(true);
        setError(null);

        console.log("🔄 Refetching MostStarredRepo");

        const data = await getMostStarredRepository(username);

        if (!isMounted.current) return;

        setRepo(data ?? null);

        updateDashboardData("mostStarredRepo", data ?? null);

        console.log("✅ MostStarredRepo Loaded");

        onLoaded?.();
      } catch (err) {
        console.error("Most Starred Repo Error:", err);

        if (!isMounted.current) return;

        setError("Failed to load repository.");
      } finally {
        if (isMounted.current) {
          setLoading(false);
        }
      }
    },
    [username, updateDashboardData, onLoaded],
  );

  useEffect(() => {
    if (!username) return;

    const isMounted = {
      current: true,
    };

    fetchRepository(isMounted);

    return () => {
      isMounted.current = false;
    };
  }, [username, refreshKey, fetchRepository]);  if (loading || error) {
    const isError = !!error;
    const skeletonClass = isError ? "skeleton-error" : "skeleton";
    return (
      <div className="msr-card" style={{ position: 'relative' }}>
        <h3 className="msr-title">Most Starred Repository</h3>
        <div className="msr-content" style={{ gap: '12px', display: 'flex', flexDirection: 'column', marginTop: '12px' }}>
          <div className={`skeleton-text ${skeletonClass}`} style={{ width: '80%', margin: 0 }}></div>
          <div className={`skeleton-text ${skeletonClass}`} style={{ width: '40%', margin: 0 }}></div>
          <div className={`skeleton-text short ${skeletonClass}`} style={{ margin: 0 }}></div>
        </div>
        {isError && (
          <div style={{ position: 'absolute', inset: 0, top: '40px', display: 'flex', alignItems: 'center', justifyItems: 'center', justifyContent: 'center', padding: '16px', zIndex: 10 }}>
            <span style={{ color: 'var(--danger-main)', fontWeight: 600, textAlign: 'center', background: 'var(--bg-card)', padding: '4px 12px', borderRadius: '8px' }}>
              {error}
            </span>
          </div>
        )}
      </div>
    );
  }

  if (!repo) {
    return (
      <div className="msr-card">
        <h3 className="msr-title">Most Starred Repository</h3>

        <div className="msr-loading">No Repository Found</div>
      </div>
    );
  }

  return (
    <div className="msr-card">
      <h3 className="msr-title">Most Starred Repository</h3>

      <div className="msr-content">
        <a
          href={repo?.html_url}
          target="_blank"
          rel="noopener noreferrer"
          className="msr-repo-name"
        >
          <FaCodeBranch className="msr-repo-icon" />

          <span>{repo?.name || "Unknown"}</span>
        </a>

        <div className="msr-stars">
          <FaStar className="msr-star-icon" />

          <span>{repo?.stars ?? 0}</span>
        </div>

        <div className="msr-language">
          <span className="msr-dot"></span>

          <span>{repo?.language || "Unknown"}</span>
        </div>
      </div>
    </div>
  );
};

export default MostStarredRepo;
