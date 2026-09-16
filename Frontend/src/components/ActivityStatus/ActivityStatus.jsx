import "./ActivityStatus.css";

import { Activity } from "lucide-react";
import { useEffect, useState, useCallback } from "react";

import { useDashboardContext } from "../../context/DashboardContext";
import { getActivityStatus } from "../../services/githubService";

const ActivityStatus = ({ username, onLoaded, refreshKey }) => {
  const { updateDashboardData } = useDashboardContext();

  const [activityData, setActivityData] = useState(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState(null);

  const fetchActivityStatus = useCallback(
    async (isMounted) => {
      try {
        setLoading(true);
        setError(null);

        console.log("🔄 Refetching ActivityStatus");

        const data = await getActivityStatus(username);

        if (!isMounted.current) return;

        setActivityData(data ?? null);

        updateDashboardData("activityStatus", data ?? null);

        console.log("✅ ActivityStatus Loaded");

        onLoaded?.();
      } catch (err) {
        console.error("Activity Status Error:", err);

        if (!isMounted.current) return;

        setError("Failed to load activity status.");
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

    fetchActivityStatus(isMounted);

    return () => {
      isMounted.current = false;
    };
  }, [username, refreshKey, fetchActivityStatus]);

  const formatLastActive = (dateString) => {
    if (!dateString) {
      return "Unknown";
    }

    const lastDate = new Date(dateString);

    if (Number.isNaN(lastDate.getTime())) {
      return "Unknown";
    }

    const now = new Date();

    const diffMs = now.getTime() - lastDate.getTime();

    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) {
      return "Just now";
    }

    if (diffHours < 24) {
      return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    }

    return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
  };

  const getStatusClass = () => {
    switch (activityData?.status) {
      case "Highly Active":
        return "highly-active";

      case "Moderate":
        return "moderate-active";

      case "Low":
        return "low-active";

      default:
        return "inactive";
    }
  };

  if (loading || error) {
    const isError = !!error;
    const skeletonClass = isError ? "skeleton-error" : "skeleton";
    return (
      <div className="status-card" style={{ position: 'relative' }}>
        <h3 className="status-title">Activity Status</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '12px' }}>
          <div className={`${skeletonClass} skeleton-text`} style={{ width: '80%', margin: 0 }}></div>
          <div className={`${skeletonClass} skeleton-text`} style={{ width: '60%', margin: 0 }}></div>
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

  if (!activityData) {
    return (
      <div className="status-card">
        <h3 className="status-title">Activity Status</h3>

        <div className="status-loading">No Data</div>
      </div>
    );
  }

  return (
    <div className="status-card">
      <h3 className="status-title">Activity Status</h3>

      <div className="status-row">
        <div className={`status-icon-wrapper ${getStatusClass()}`}>
          <Activity size={18} className={`status-icon ${getStatusClass()}`} />
        </div>

        <span className={`status-text ${getStatusClass()}`}>
          {activityData?.status || "Inactive"}
        </span>

        <span className="status-last-active">
          {formatLastActive(activityData?.lastActive)}
        </span>
      </div>

      <div className="status-divider"></div>

      <div className="status-streak">
        <span className="status-streak-label">Streak</span>

        <span className="status-fire">🔥</span>

        <span className="status-streak-value">
          {activityData?.streak ?? 0} days
        </span>
      </div>
    </div>
  );
};

export default ActivityStatus;
