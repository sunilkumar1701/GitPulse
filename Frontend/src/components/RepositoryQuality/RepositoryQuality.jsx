import "./RepositoryQuality.css";

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

import { useEffect, useState, useCallback, useMemo } from "react";

import { useDashboardContext } from "../../context/DashboardContext";
import { getRepositoryQualityAnalysis } from "../../services/githubService";
import { COLORS } from '../../constants/colorConstant';

const RepositoryQuality = ({ username, onLoaded, refreshKey }) => {
  const { updateDashboardData } = useDashboardContext();

  const [qualityData, setQualityData] = useState(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState(null);

  const fetchRepositoryQuality = useCallback(
    async (isMounted) => {
      try {
        setLoading(true);
        setError(null);

        console.log("🔄 Refetching RepositoryQuality");

        const data = await getRepositoryQualityAnalysis(username);

        if (!isMounted.current) return;

        const score = data?.score ?? 0;

        const label =
          score >= 90
            ? "Excellent"
            : score >= 70
              ? "Good"
              : score >= 50
                ? "Average"
                : "Poor";

        const metrics = [
          {
            name: "README",
            value: data?.metrics?.readme ?? 0,
            count: data?.counts?.readme ?? 0,
            description:
              "Checks whether the repository contains a README file with basic project information.",
          },
          {
            name: "Description",
            value: data?.metrics?.description ?? 0,
            count: data?.counts?.description ?? 0,
            description:
              "Checks whether the repository has a meaningful description in the GitHub About section.",
          },
          {
            name: "Documentation",
            value: data?.metrics?.documentation ?? 0,
            count: data?.counts?.documentation ?? 0,
            description:
              "Checks whether the README contains more than 100 words and provides meaningful project documentation.",
          },
          {
            name: "Topics",
            value: data?.metrics?.topics ?? 0,
            count: data?.counts?.topics ?? 0,
            description:
              "Checks whether the repository uses GitHub Topics for categorization and discoverability.",
          },
        ];

        const formattedData = {
          score,
          totalRepos: data?.total_repos ?? 0,
          label,
          metrics,
        };

        setQualityData(formattedData);

        updateDashboardData("repositoryQuality", {
          score,
          totalRepos: data?.total_repos ?? 0,
          label,
          metrics: metrics.map(({ name, value, count }) => ({
            name,
            score: value,
            count,
          })),
        });

        console.log("✅ RepositoryQuality Loaded");

        onLoaded?.();
      } catch (err) {
        console.error("Repository Quality Error:", err);

        if (!isMounted.current) return;

        setError("Failed to load repository quality.");
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

    fetchRepositoryQuality(isMounted);

    return () => {
      isMounted.current = false;
    };
  }, [fetchRepositoryQuality, refreshKey]);

  const scoreColor = useMemo(() => {
    if (!qualityData) return COLORS.danger.main;

    if (qualityData.score >= 90) return "#22c55e";

    if (qualityData.score >= 70) return "#3b82f6";

    if (qualityData.score >= 50) return "#f59e0b";

    return COLORS.danger.main;
  }, [qualityData]);

  const chartData = useMemo(() => {
    if (!qualityData) return [];

    return [
      {
        name: "completed",
        value: qualityData.score,
      },
      {
        name: "remaining",
        value: 100 - qualityData.score,
      },
    ];
  }, [qualityData]);  if (loading || error) {
    const isError = !!error;
    const skeletonClass = isError ? "skeleton-error" : "skeleton";
    return (
      <div className="rq-card" style={{ position: 'relative' }}>
        <h3 className="rq-title">Repository Quality</h3>
        <div className="rq-content">
          <div className={`rq-chart-wrapper skeleton-circle ${skeletonClass}`} style={{ width: '80px', height: '80px', flexShrink: 0, border: 'none' }}></div>
          <div className="rq-metrics" style={{ width: '100%', gap: '12px', display: 'flex', flexDirection: 'column', paddingLeft: '16px' }}>
            <div className={`skeleton-text ${skeletonClass}`} style={{ width: '100%', margin: 0 }}></div>
            <div className={`skeleton-text ${skeletonClass}`} style={{ width: '80%', margin: 0 }}></div>
            <div className={`skeleton-text ${skeletonClass}`} style={{ width: '90%', margin: 0 }}></div>
            <div className={`skeleton-text ${skeletonClass}`} style={{ width: '70%', margin: 0 }}></div>
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

  if (!qualityData) {
    return null;
  }

  return (
    <div className="rq-card">
      <h3 className="rq-title">Repository Quality</h3>

      <div className="rq-content">
        <div className="rq-chart-wrapper">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                cx="50%"
                cy="50%"
                innerRadius={24}
                outerRadius={34}
                startAngle={90}
                endAngle={-270}
                stroke="none"
              >
                <Cell fill={scoreColor} />

                <Cell fill="rgba(255,255,255,0.08)" />
              </Pie>
            </PieChart>
          </ResponsiveContainer>

          <div className="rq-center-text">
            <div
              className="rq-score"
              style={{
                color: scoreColor,
              }}
            >
              {qualityData.score}%
            </div>

            <div
              className="rq-label"
              style={{
                color: scoreColor,
              }}
            >
              {qualityData.label}
            </div>
          </div>
        </div>

        <div className="rq-metrics">
          {qualityData.metrics.map((item) => (
            <div key={item.name} className="rq-row">
              <div className="rq-metric-wrapper">
                <span className="rq-metric-name">{item.name}</span>

                <div className="rq-tooltip-container">
                  ⓘ
                  <div className="rq-tooltip">
                    <strong>{item.name}</strong>
                    <br />
                    <br />
                    {item.description}
                    <br />
                    <br />
                    Found in{" "}
                    <strong>
                      {item.count}/{qualityData.totalRepos}
                    </strong>{" "}
                    repositories.
                  </div>
                </div>
              </div>

              <span className="rq-metric-value">{item.value}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default RepositoryQuality;
