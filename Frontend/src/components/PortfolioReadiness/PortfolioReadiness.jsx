import "./PortfolioReadiness.css";

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

import { useEffect, useState, useCallback, useMemo } from "react";

import { useDashboardContext } from "../../context/DashboardContext";
import { getPortfolioReadinessAnalysis } from "../../services/githubService";

const PortfolioReadiness = ({ username, onLoaded, refreshKey }) => {
  const { updateDashboardData } = useDashboardContext();

  const [data, setData] = useState(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState(null);

  const fetchPortfolioReadiness = useCallback(
    async (isMounted) => {
      try {
        setLoading(true);
        setError(null);

        console.log("🔄 Refetching PortfolioReadiness");

        const response = await getPortfolioReadinessAnalysis(username);

        if (!isMounted.current) return;

        const formattedData = {
          score: response?.score ?? 0,

          completed: response?.completed ?? 0,

          total: response?.total ?? 0,

          checks: response?.checks ?? [],
        };

        setData(formattedData);

        updateDashboardData("portfolioReadiness", formattedData);

        console.log("✅ PortfolioReadiness Loaded");

        onLoaded?.();
      } catch (err) {
        console.error("Portfolio Readiness Error:", err);

        if (!isMounted.current) return;

        setError("Failed to load portfolio readiness.");
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

    fetchPortfolioReadiness(isMounted);

    return () => {
      isMounted.current = false;
    };
  }, [username, refreshKey, fetchPortfolioReadiness]);

  const score = data?.score ?? 0;

  const checks = data?.checks ?? [];

  const chartData = useMemo(
    () => [
      {
        name: "completed",
        value: score,
      },
      {
        name: "remaining",
        value: 100 - score,
      },
    ],
    [score],
  );

  const label = useMemo(() => {
    if (score >= 90) return "Excellent";

    if (score >= 70) return "Good";

    if (score >= 50) return "Average";

    return "Poor";
  }, [score]);

  if (loading || error) {
    const isError = !!error;
    const skeletonClass = isError ? "skeleton-error" : "skeleton";
    return (
      <div className="pr-card" style={{ position: 'relative' }}>
        <h3 className="pr-title">Portfolio Readiness</h3>
        <div className="pr-content">
          <div className={`pr-chart-wrapper ${skeletonClass} skeleton-circle`} style={{ width: '80px', height: '80px', flexShrink: 0, border: 'none' }}></div>
          <div className="pr-checks" style={{ width: '100%', gap: '12px', display: 'flex', flexDirection: 'column', paddingLeft: '16px' }}>
            <div className={`${skeletonClass} skeleton-text`} style={{ width: '100%', margin: 0 }}></div>
            <div className={`${skeletonClass} skeleton-text`} style={{ width: '80%', margin: 0 }}></div>
            <div className={`${skeletonClass} skeleton-text`} style={{ width: '90%', margin: 0 }}></div>
            <div className={`${skeletonClass} skeleton-text`} style={{ width: '70%', margin: 0 }}></div>
          </div>
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

  if (!data) {
    return null;
  }

  return (
    <div className="pr-card">
      <h3 className="pr-title">Portfolio Readiness</h3>

      <div className="pr-content">
        <div className="pr-chart-wrapper">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                cx="50%"
                cy="50%"
                innerRadius={28}
                outerRadius={38}
                startAngle={90}
                endAngle={-270}
                stroke="none"
              >
                <Cell fill="#22c55e" />

                <Cell fill="rgba(255,255,255,0.08)" />
              </Pie>
            </PieChart>
          </ResponsiveContainer>

          <div className="pr-center-text">
            <div className="pr-score">{score}%</div>

            <div className="pr-label">{label}</div>
          </div>
        </div>

        <div className="pr-checks">
          {checks.map((item) => (
            <div key={item.name} className="pr-row">
              <div className="pr-left">
                <span
                  className={item.status ? "pr-dot success" : "pr-dot failed"}
                ></span>

                <span className="pr-text">{item.name}</span>
              </div>

              <span
                className={
                  item.status ? "pr-status success" : "pr-status failed"
                }
              >
                {item.status ? "✓" : "✕"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default PortfolioReadiness;
