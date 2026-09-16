import "./App.css";

import {
  useEffect,
  useState,
  useRef,
  useCallback,
} from "react";

import { getCurrentTabContext } from "./services/githubService";

import ProfileCard from "./components/ProfileCard/ProfileCard";
import ProfileAnalysis from "./components/ProfileAnalysis/ProfileAnalysis";
import RepositoryAnalysis from "./components/RepositoryAnalysis/RepositoryAnalysis";
import TechnologyStack from "./components/TechnologyStack/TechnologyStack";
import ActivityAnalysis from "./components/ActivityAnalysis/ActivityAnalysis";
import RepositoryQuality from "./components/RepositoryQuality/RepositoryQuality";
import PortfolioReadiness from "./components/PortfolioReadiness/PortfolioReadiness";
import MostStarredRepo from "./components/MostStarredRepo/MostStarredRepo";
import MostForkedRepo from "./components/MostForkedRepo/MostForkedRepo";
import ActivityStatus from "./components/ActivityStatus/ActivityStatus";
import ActionButtons from "./components/ActionButtons/ActionButtons";
import NavigationModal from "./components/NavigationModal/NavigationModal";
import Auth from "./components/Auth/Auth";
import FloatingAIButton from "./components/FloatingAIButton/FloatingAIButton";
import ProfilePage from "./components/ProfilePage/ProfilePage";

import { useDashboardContext } from "./context/DashboardContext";
import { COLORS } from './constants/colorConstant';
import { supabase } from './services/supabaseClient';

function App() {
  const { dashboardData } = useDashboardContext();

  const dashboardRef = useRef(null);
  const mountedRef = useRef(true);

  const TOTAL_MODULES = 10;

  const [detectedContext, setDetectedContext] = useState({ type: 'LOADING' });
  const [activeDashboardUser, setActiveDashboardUser] = useState(null);
  const [loadedModules, setLoadedModules] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [currentView, setCurrentView] = useState("dashboard");

  const handleModuleLoaded = useCallback(() => {
    setLoadedModules((prev) =>
      prev < TOTAL_MODULES ? prev + 1 : prev
    );
  }, []);

  const handleReanalyze = useCallback(() => {
    console.log("🔄 Reanalyzing dashboard");
    setLoadedModules(0);
    setRefreshKey((prev) => prev + 1);
  }, []);

  const isDashboardLoading = loadedModules < TOTAL_MODULES;

  const updateContext = useCallback(async () => {
    try {
      const context = await getCurrentTabContext();
      if (mountedRef.current) {
        setDetectedContext(context);
        
        // Auto-open dashboard if a GitHub user is detected (no modal)
        if (context.type === "GITHUB_USER") {
          setActiveDashboardUser(context.username);
        }
      }
    } catch (error) {
      console.error("Context Update Error:", error);
      if (mountedRef.current) {
        setDetectedContext({ type: 'NON_GITHUB' });
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    updateContext();

    if (typeof chrome !== "undefined" && chrome.tabs) {
      const handleTabUpdate = (tabId, changeInfo, tab) => {
        if (changeInfo.url || changeInfo.status === 'complete') {
          updateContext();
        }
      };

      const handleTabActivate = (activeInfo) => {
        updateContext();
      };

      chrome.tabs.onUpdated.addListener(handleTabUpdate);
      chrome.tabs.onActivated.addListener(handleTabActivate);

      return () => {
        mountedRef.current = false;
        chrome.tabs.onUpdated.removeListener(handleTabUpdate);
        chrome.tabs.onActivated.removeListener(handleTabActivate);
      };
    }

    return () => {
      mountedRef.current = false;
      chrome.tabs?.onUpdated?.removeListener(handleTabUpdate);
      chrome.tabs?.onActivated?.removeListener(handleTabActivate);
    };
  }, [updateContext]);

  useEffect(() => {
    // Check active session on mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      setIsAuthenticated(!!session);
      setIsAuthLoading(false);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setIsAuthenticated(!!session);
      setIsAuthLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleOpenDashboard = (username) => {
    setActiveDashboardUser(username);
    setLoadedModules(0);
    setRefreshKey((prev) => prev + 1);
  };

  const showModal = 
    !activeDashboardUser || 
    (detectedContext.type === "GITHUB_USER" && detectedContext.username !== activeDashboardUser) || 
    detectedContext.type === "NON_GITHUB" || 
    detectedContext.type === "GITHUB_SYSTEM";

  if (detectedContext.type === "LOADING") {
    return (
      <div
        className="dashboard"
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: "100vh",
          color: COLORS.text.primary,
        }}
      >
        Loading Context...
      </div>
    );
  }

  if (isAuthLoading) {
    return (
      <div
        className="dashboard"
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: "100vh",
          color: COLORS.text.primary,
        }}
      >
        Checking Authentication...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Auth onLoginSuccess={() => setIsAuthenticated(true)} />;
  }

  return (
    <>
      {isAuthenticated && <FloatingAIButton username={activeDashboardUser} />}

      {showModal && (
        <NavigationModal 
          context={detectedContext} 
          onOpenDashboard={handleOpenDashboard} 
        />
      )}

      {activeDashboardUser && currentView === "dashboard" && (
        <div 
          className="dashboard" 
          ref={dashboardRef} 
          style={{ display: showModal ? 'none' : 'flex' }}
        >
          <div className="full-row">
            <ProfileCard
              username={activeDashboardUser}
              refreshKey={refreshKey}
              onLoaded={handleModuleLoaded}
            />
          </div>

          <div className="full-row">
            <ProfileAnalysis
              username={activeDashboardUser}
              refreshKey={refreshKey}
              onLoaded={handleModuleLoaded}
            />
          </div>

          <div className="full-row">
            <RepositoryAnalysis
              username={activeDashboardUser}
              refreshKey={refreshKey}
              onLoaded={handleModuleLoaded}
            />
          </div>

          <div
            className="row"
            style={{
              gridTemplateColumns: "4fr 6fr",
            }}
          >
            <TechnologyStack
              username={activeDashboardUser}
              refreshKey={refreshKey}
              onLoaded={handleModuleLoaded}
            />

            <ActivityAnalysis
              username={activeDashboardUser}
              refreshKey={refreshKey}
              onLoaded={handleModuleLoaded}
            />
          </div>

          <div
            className="row"
            style={{
              gridTemplateColumns: "4fr 6fr",
            }}
          >
            <RepositoryQuality
              username={activeDashboardUser}
              refreshKey={refreshKey}
              onLoaded={handleModuleLoaded}
            />

            <PortfolioReadiness
              username={activeDashboardUser}
              refreshKey={refreshKey}
              onLoaded={handleModuleLoaded}
            />
          </div>

          <div
            className="row"
            style={{
              gridTemplateColumns: "3fr 3fr 4fr",
            }}
          >
            <MostStarredRepo
              username={activeDashboardUser}
              refreshKey={refreshKey}
              onLoaded={handleModuleLoaded}
            />

            <MostForkedRepo
              username={activeDashboardUser}
              refreshKey={refreshKey}
              onLoaded={handleModuleLoaded}
            />

            <ActivityStatus
              username={activeDashboardUser}
              refreshKey={refreshKey}
              onLoaded={handleModuleLoaded}
            />
          </div>

          <div className="full-row">
            <ActionButtons
              isLoading={isDashboardLoading}
              dashboardRef={dashboardRef}
              onReanalyze={handleReanalyze}
              username={activeDashboardUser}
              dashboardData={dashboardData}
              onProfileClick={() => setCurrentView("profile")}
            />
          </div>
        </div>
      )}

      {activeDashboardUser && currentView === "profile" && (
        <ProfilePage 
          onBack={() => setCurrentView("dashboard")} 
          onLogout={() => setCurrentView("dashboard")} 
        />
      )}
    </>
  );
}

export default App;