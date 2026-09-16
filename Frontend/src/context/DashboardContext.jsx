import {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
} from "react";

const DashboardContext = createContext(null);

const initialDashboardData = {
  profileCard: null,
  profileAnalysis: null,
  repositoryAnalysis: null,
  technologyStack: null,
  activityAnalysis: null,
  portfolioReadiness: null,
  repositoryQuality: null,
  mostStarredRepo: null,
  mostForkedRepo: null,
  activityStatus: null,
  developerScore: null,
};

export const DashboardProvider = ({ children }) => {
  const [dashboardData, setDashboardData] = useState(initialDashboardData);

  const updateDashboardData = useCallback((key, value) => {
    setDashboardData((prev) => {
      // Prevent unnecessary updates
      if (prev[key] === value) {
        return prev;
      }

      return {
        ...prev,
        [key]: value,
      };
    });
  }, []);

  const resetDashboardData = useCallback(() => {
    setDashboardData(initialDashboardData);
  }, []);

  const value = useMemo(
    () => ({
      dashboardData,
      updateDashboardData,
      resetDashboardData,
    }),
    [dashboardData, updateDashboardData, resetDashboardData],
  );

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  );
};

export const useDashboardContext = () => {
  const context = useContext(DashboardContext);

  if (!context) {
    throw new Error(
      "useDashboardContext must be used inside DashboardProvider",
    );
  }

  return context;
};
