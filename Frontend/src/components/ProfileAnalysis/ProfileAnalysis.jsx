import { useEffect, useMemo, useState } from "react";
import "./ProfileAnalysis.css";

import { Users, UserRound, FolderGit2, Clock3, Link2 } from "lucide-react";

import { useDashboardContext } from "../../context/DashboardContext";
import { getProfileAnalysis } from "../../services/githubService";

const ProfileAnalysis = ({ username, onLoaded, refreshKey }) => {
  const { updateDashboardData } = useDashboardContext();

  const [state, setState] = useState({
    analysis: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let mounted = true;

    const fetchAnalysis = async () => {
      try {
        console.log("🔄 Refetching ProfileAnalysis");

        const data = await getProfileAnalysis(username);

        if (!mounted) return;

        setState({
          analysis: data,
          loading: false,
          error: null,
        });

        updateDashboardData("profileAnalysis", data);

        console.log("✅ ProfileAnalysis Loaded");

        onLoaded?.();
      } catch (error) {
        console.error("ProfileAnalysis Error:", error);

        if (!mounted) return;

        setState({
          analysis: null,
          loading: false,
          error: "Unable to load profile analysis.",
        });
      }
    };

    fetchAnalysis();

    return () => {
      mounted = false;
    };
  }, [username, refreshKey, updateDashboardData, onLoaded]);

  const { analysis, loading, error } = state;

  const recentRepo = analysis?.recent_repo;

  const relativeTime = useMemo(() => {
    if (!recentRepo?.updated_at) return "";

    const now = new Date();

    const updated = new Date(recentRepo.updated_at);

    const seconds = Math.floor((now - updated) / 1000);

    if (seconds < 60) return `${seconds} sec ago`;

    const minutes = Math.floor(seconds / 60);

    if (minutes < 60) return `${minutes} min ago`;

    const hours = Math.floor(minutes / 60);

    if (hours < 24) return `${hours} hr ago`;

    const days = Math.floor(hours / 24);

    if (days < 30) return `${days} day${days > 1 ? "s" : ""} ago`;

    const months = Math.floor(days / 30);

    if (months < 12) return `${months} month${months > 1 ? "s" : ""} ago`;

    const years = Math.floor(months / 12);

    return `${years} year${years > 1 ? "s" : ""} ago`;
  }, [recentRepo?.updated_at]);

  if (loading || error) {
    const isError = !!error;
    const skeletonClass = isError ? "skeleton-error" : "skeleton";
    return (
      <div className="profile-analysis" style={{ position: 'relative' }}>
        <div className={`analysis-card ${skeletonClass} skeleton-box`}></div>
        <div className={`analysis-card ${skeletonClass} skeleton-box`}></div>
        <div className={`analysis-card repo-card ${skeletonClass} skeleton-box`}></div>
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

  return (
    <div className="profile-analysis">
      {/* Followers */}

      <div className="analysis-card">
        <div className="analysis-header">
          <Users size={18} color="#8B5CF6" />

          <span className="analysis-title">Followers</span>
        </div>

        <h2 className="analysis-count">{analysis?.followers ?? 0}</h2>
      </div>

      {/* Following */}

      <div className="analysis-card">
        <div className="analysis-header">
          <UserRound size={18} color="#A855F7" />

          <span className="analysis-title">Following</span>
        </div>

        <h2 className="analysis-count">{analysis?.following ?? 0}</h2>
      </div>

      {/* Repo Card */}

      <div className="analysis-card repo-card">
        {/* Left */}

        <div className="repo-left">
          <div className="analysis-header">
            <FolderGit2 size={18} color="#F59E0B" />

            <span className="analysis-title">Public Repos</span>
          </div>

          <h2 className="analysis-count">{analysis?.public_repos ?? 0}</h2>
        </div>

        <div className="repo-divider"></div>

        {/* Right */}

        <div className="repo-right">
          <div className="analysis-header">
            <Clock3 size={16} color="#60A5FA" />

            <span className="analysis-title recent-title">
              Recent Active Repo
            </span>
          </div>

          {recentRepo ? (
            <>
              <a
                href={recentRepo.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="repo-link"
              >
                <Link2 size={14} color="#94A3B8" />

                <span>{recentRepo.name}</span>
              </a>

              <div className="repo-time">Updated {relativeTime}</div>
            </>
          ) : (
            <div className="repo-time">No recent repository found.</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProfileAnalysis;
