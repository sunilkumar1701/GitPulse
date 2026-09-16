import "./TechnologyStack.css";
import { useState, useEffect } from "react";
import { getTechnologyStackAnalysis } from "../../services/githubService";
import { useDashboardContext } from "../../context/DashboardContext";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { COLORS } from '../../constants/colorConstant';

const CHART_COLORS = [COLORS.warning.yellow, COLORS.info.main, COLORS.warning.lightOrange, COLORS.primary.light, COLORS.success.main];

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;

    return (
      <div
        style={{
          background: COLORS.background.darkElement,
          border: "1px solid rgba(139,92,246,0.35)",
          borderRadius: "10px",
          padding: "10px 12px",
          color: COLORS.text.primary,
          boxShadow: "0 0 20px rgba(139,92,246,0.25)",
          minWidth: "120px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            marginBottom: "6px",
          }}
        >
          <span
            style={{
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              background: data.color,
            }}
          />

          <span
            style={{
              fontWeight: 600,
            }}
          >
            {data.name}
          </span>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "center",
            color: COLORS.text.muted,
            fontSize: "12px",
          }}
        >
          Usage: {data.value}%
        </div>
      </div>
    );
  }

  return null;
};

const TechnologyStack = ({ username, onLoaded, refreshKey }) => {
  const { updateDashboardData } = useDashboardContext();
  const [activeIndex, setActiveIndex] = useState(null);

  const [mounted, setMounted] = useState(false);

  const [technologyData, setTechnologyData] = useState([]);

  const [totalLanguages, setTotalLanguages] = useState(0);

  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchTechnologyStack = async () => {
      try {
        console.log("🔄 Refetching TechnologyStack");
        const data = await getTechnologyStackAnalysis(username);

        if (data && data.top_languages) {
        // Map colors to data
        const formattedData = data.top_languages.map((lang, index) => ({
          ...lang,
          color: CHART_COLORS[index % CHART_COLORS.length],
        }));

        setTechnologyData(formattedData);

        setTotalLanguages(data.total_languages);
        updateDashboardData("technologyStack", {
          topLanguages: formattedData,
          totalLanguages: data.total_languages,
        });
        console.log("✅ TechnologyStack Loaded");
        onLoaded?.();
        }
      } catch (err) {
        console.error("Technology Stack Error:", err);
        setError("Failed to load technology data.");
      }
    };

    setMounted(true);

    fetchTechnologyStack();
  }, [username, refreshKey]);

  const isCompact = window.innerWidth < 1300;

  const onPieEnter = (_, index) => {
    setActiveIndex(index);
  };

  const onPieLeave = () => {
    setActiveIndex(null);
  };

  return (
    <div className="technology-card" style={{ position: 'relative' }}>
      <h3 className="technology-title" title="Top Languages">
        Top Languages
      </h3>

      <div className="technology-wrapper">
        <div className="chart-section">
          {technologyData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Tooltip
                  content={<CustomTooltip />}
                  position={{
                    x: 0,
                    y: -45,
                  }}
                  wrapperStyle={{
                    zIndex: 9999,
                  }}
                />

                <Pie
                  data={technologyData}
                  dataKey="value"
                  cx="50%"
                  cy="50%"
                  innerRadius={isCompact ? 18 : 36}
                  outerRadius={isCompact ? 30 : 58}
                  paddingAngle={2}
                  activeIndex={activeIndex}
                  onMouseEnter={onPieEnter}
                  onMouseLeave={onPieLeave}
                >
                  {technologyData.map((entry, index) => (
                  <Cell
                    key={entry.name}
                    fill={entry.color}
                    stroke={COLORS.text.primary}
                    strokeWidth={activeIndex === index ? 2 : 1}
                  />
                ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className={`skeleton-circle ${error ? "skeleton-error" : "skeleton"}`} style={{ width: '100%', height: '100%', border: 'none' }}></div>
          )}

          <div className="chart-center">{totalLanguages}</div>
        </div>

        <div className="language-list">
          {technologyData.length > 0 ? (
            technologyData.map((language) => (
              <div key={language.name} className="language-item">
                <div className="language-left">
                  <span
                    className="language-dot"
                    style={{
                      background: language.color,
                    }}
                  />
                  <span>{language.name}</span>
                </div>
                <span className="language-value">{language.value}%</span>
              </div>
            ))
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
               <div className={`skeleton-text ${error ? "skeleton-error" : "skeleton"}`} style={{ width: '100%', margin: 0 }}></div>
               <div className={`skeleton-text ${error ? "skeleton-error" : "skeleton"}`} style={{ width: '80%', margin: 0 }}></div>
               <div className={`skeleton-text ${error ? "skeleton-error" : "skeleton"}`} style={{ width: '90%', margin: 0 }}></div>
               <div className={`skeleton-text ${error ? "skeleton-error" : "skeleton"}`} style={{ width: '70%', margin: 0 }}></div>
               <div className={`skeleton-text ${error ? "skeleton-error" : "skeleton"}`} style={{ width: '60%', margin: 0 }}></div>
            </div>
          )}
        </div>
      </div>
      {error && (
        <div style={{ position: 'absolute', inset: 0, top: '40px', display: 'flex', alignItems: 'center', justifyItems: 'center', justifyContent: 'center', padding: '16px', zIndex: 10 }}>
          <span style={{ color: 'var(--danger-main)', fontWeight: 600, textAlign: 'center', background: 'var(--bg-card)', padding: '4px 12px', borderRadius: '8px' }}>
            {error}
          </span>
        </div>
      )}
    </div>
  );
};

export default TechnologyStack;
