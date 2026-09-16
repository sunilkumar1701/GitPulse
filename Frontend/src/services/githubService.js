import apiClient from "./apiClient";

const GITHUB_API = "/github";

const fetchData = async (endpoint) => {
  try {
    const response = await apiClient.get(
      `${GITHUB_API}${endpoint}`,
    );

    return response.data.data;
  } catch (error) {
    throw {
      status: error.status,

      message:
        error.message ||
        "Failed to fetch GitHub data.",
    };
  }
};

const GITHUB_SYSTEM_ROUTES = new Set([
  'explore', 'topics', 'features', 'marketplace', 'settings',
  'pulls', 'issues', 'notifications', 'new', 'organizations',
  'repositories', 'search', 'sponsors', 'pricing', 'about',
  'blog', 'contact', 'enterprise', 'nonprofit', 'dashboard',
  'login', 'join', 'codespaces', 'trending'
]);

export const extractGithubContextFromUrl = (urlStr) => {
  if (!urlStr) return { type: 'NON_GITHUB' };
  
  try {
    const url = new URL(urlStr);
    const hostname = url.hostname.toLowerCase();
    
    if (hostname !== 'github.com' && hostname !== 'www.github.com') {
      return { type: 'NON_GITHUB' };
    }
    
    const pathSegments = url.pathname.split('/').filter(Boolean);
    
    if (pathSegments.length === 0) {
      return { type: 'GITHUB_SYSTEM' };
    }
    
    const potentialUsername = pathSegments[0];
    
    if (GITHUB_SYSTEM_ROUTES.has(potentialUsername.toLowerCase())) {
      return { type: 'GITHUB_SYSTEM' };
    }
    
    return { 
      type: 'GITHUB_USER', 
      username: potentialUsername 
    };
  } catch (error) {
    console.error("URL Parsing Error:", error);
    return { type: 'NON_GITHUB' };
  }
};

export const getCurrentTabContext = () => {
  return new Promise((resolve) => {
    try {
      if (typeof chrome === "undefined" || !chrome.tabs) {
        resolve({ type: 'NON_GITHUB' });
        return;
      }

      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (chrome.runtime.lastError) {
          console.error("Chrome Runtime Error:", chrome.runtime.lastError.message);
          resolve({ type: 'NON_GITHUB' });
          return;
        }

        const url = tabs?.[0]?.url;
        resolve(extractGithubContextFromUrl(url));
      });
    } catch (error) {
      console.error("Context Detection Error:", error);
      resolve({ type: 'NON_GITHUB' });
    }
  });
};

// Deprecated
export const getGithubUsername = async () => {
  const context = await getCurrentTabContext();
  return context.type === 'GITHUB_USER' ? context.username : null;
};

export const getProfile = (username) =>
  fetchData(`/profile/${username}`);

export const getProfileAnalysis = (
  username,
) => fetchData(`/analysis/${username}`);

export const getRepositoryAnalysis = (
  username,
) =>
  fetchData(
    `/repository-analysis/${username}`,
  );

export const getTechnologyStackAnalysis = (
  username,
) =>
  fetchData(
    `/technology-stack/${username}`,
  );

export const getActivityAnalysis = (
  username,
) =>
  fetchData(
    `/activity-analysis/${username}`,
  );

export const getRepositoryQualityAnalysis = (
  username,
) =>
  fetchData(
    `/repository-quality/${username}`,
  );

export const getPortfolioReadinessAnalysis =
  (username) =>
    fetchData(
      `/portfolio-readiness/${username}`,
    );

export const getMostStarredRepository = (
  username,
) =>
  fetchData(
    `/most-starred-repository/${username}`,
  );

export const getMostForkedRepository = (
  username,
) =>
  fetchData(
    `/most-forked-repository/${username}`,
  );

export const getActivityStatus = (
  username,
) =>
  fetchData(
    `/activity-status/${username}`,
  );

export const getDeveloperScore = (
  username,
) =>
  fetchData(
    `/developer-score/${username}`,
  );