import "./ActivityAnalysis.css";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

import { useEffect, useState, useCallback, useMemo } from "react";

import { useDashboardContext } from "../../context/DashboardContext";
import { getActivityAnalysis } from "../../services/githubService";

const labelMap = {
  commits: "Commits",
  pullRequests: "Pull Requests",
  repositoriesCreated: "Repositories",
};

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="activity-tooltip">
      <div className="tooltip-title">{label}</div>

      {payload.map((item) => (
        <div key={item.dataKey} className="tooltip-row">
          <span
            style={{
              color: item.color,
            }}
          >
            {labelMap[item.dataKey]}
          </span>

          <strong>{item.value}</strong>
        </div>
      ))}
    </div>
  );
};

const ActivityAnalysis = ({ username, onLoaded, refreshKey }) => {
  const { updateDashboardData } = useDashboardContext();

  const [activityData, setActivityData] = useState([]);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState(null);

  const fetchActivityData = useCallback(
    async (isMounted) => {
      try {
        setLoading(true);
        setError(null);

        console.log("🔄 Refetching ActivityAnalysis");

        const data = await getActivityAnalysis(username);

        const activity = Array.isArray(data?.activity) ? data.activity : [];

        if (!isMounted.current) return;

        setActivityData(activity);

        updateDashboardData("activityAnalysis", activity);

        console.log("✅ ActivityAnalysis Loaded");

        onLoaded?.();
      } catch (error) {
        console.error("Activity Analysis Error:", error);

        if (!isMounted.current) return;

        setError("Failed to load activity data.");
      } finally {
        if (isMounted.current) {
          setLoading(false);
        }
      }
    },
    [username, updateDashboardData, onLoaded],
  );

  useEffect(() => {
    const isMounted = {
      current: true,
    };

    fetchActivityData(isMounted);

    return () => {
      isMounted.current = false;
    };
  }, [fetchActivityData, refreshKey]);

  const roundedMax = useMemo(() => {
    const maxValue = Math.max(
      ...activityData.flatMap((item) => [
        item?.commits || 0,
        item?.pullRequests || 0,
        item?.repositoriesCreated || 0,
      ]),
      10,
    );

    return Math.ceil(maxValue / 10) * 10;
  }, [activityData]);  if (loading || error) {
    const isError = !!error;
    const skeletonClass = isError ? "skeleton-error" : "skeleton";
    return (
      <div className="activity-card" style={{ position: 'relative' }}>
        <div className="activity-title">Activity (Last 12 Months)</div>
        <div className={`skeleton-box ${skeletonClass}`} style={{ width: '100%', height: 'calc(100% - 30px)', marginTop: '10px' }}></div>
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

  return (
    <div className="activity-card">
      <div className="activity-title">Activity (Last 12 Months)</div>

      <div className="activity-chart">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={activityData}
            margin={{
              top: 5,
              right: 5,
              left: -40,
              bottom: -10,
            }}
          >
            <defs>
              <linearGradient id="commitGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#a855f7" stopOpacity={0.35} />

                <stop offset="100%" stopColor="#a855f7" stopOpacity={0} />
              </linearGradient>

              <linearGradient id="prGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.25} />

                <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>

              <linearGradient id="repoGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity={0.25} />

                <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>

            <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />

            <XAxis
              dataKey="label"
              tick={{
                fill: "#94a3b8",
                fontSize: 10,
              }}
              axisLine={false}
              tickLine={false}
            />

            <YAxis
              domain={[0, roundedMax]}
              ticks={[
                0,
                Math.round(roundedMax / 3),
                Math.round((roundedMax * 2) / 3),
                roundedMax,
              ]}
              tick={{
                fill: "#94a3b8",
                fontSize: 10,
              }}
              axisLine={false}
              tickLine={false}
            />

            <Tooltip
              content={<CustomTooltip />}
              cursor={{
                stroke: "rgba(255,255,255,0.15)",
              }}
              wrapperStyle={{
                zIndex: 9999,
              }}
            />

            <Area
              type="monotone"
              dataKey="commits"
              stroke="#a855f7"
              strokeWidth={3}
              fill="url(#commitGradient)"
              dot={{
                r: 4,
                fill: "#a855f7",
                stroke: "#c084fc",
                strokeWidth: 2,
              }}
              activeDot={{
                r: 6,
                fill: "#a855f7",
                stroke: "#fff",
                strokeWidth: 2,
              }}
            />

            <Area
              type="monotone"
              dataKey="pullRequests"
              stroke="#3b82f6"
              strokeWidth={2.5}
              fill="url(#prGradient)"
              dot={{
                r: 3,
                fill: "#3b82f6",
              }}
            />

            <Area
              type="monotone"
              dataKey="repositoriesCreated"
              stroke="#10b981"
              strokeWidth={2.5}
              fill="url(#repoGradient)"
              dot={{
                r: 3,
                fill: "#10b981",
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ActivityAnalysis;
