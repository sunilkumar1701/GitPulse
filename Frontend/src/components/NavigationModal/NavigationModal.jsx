import "./NavigationModal.css";
import { UserX, Globe } from "lucide-react";
import { FaGithub } from "react-icons/fa";

const NavigationModal = ({ context, onOpenDashboard }) => {
  if (!context || context.type === "LOADING") return null;

  const handleGoToGithub = () => {
    if (typeof chrome !== "undefined" && chrome.tabs) {
      chrome.tabs.update({ url: "https://github.com" });
    } else {
      window.open("https://github.com", "_blank");
    }
  };

  return (
    <div className="navigation-modal-overlay">
      <div className="navigation-modal-card">
        {context.type === "GITHUB_USER" && (
          <>
            <div className="navigation-modal-icon">
              <FaGithub size={28} />
            </div>
            <h3 className="navigation-modal-title">GitHub Profile Detected</h3>
            <p className="navigation-modal-desc">
              We detected the GitHub profile:
              <br />
              <span className="navigation-modal-username">{context.username}</span>
            </p>
            <button 
              className="navigation-modal-btn" 
              onClick={() => onOpenDashboard(context.username)}
            >
              Open Dashboard
            </button>
          </>
        )}

        {context.type === "NON_GITHUB" && (
          <>
            <div className="navigation-modal-icon">
              <Globe size={28} />
            </div>
            <h3 className="navigation-modal-title">GitHub Page Required</h3>
            <p className="navigation-modal-desc">
              This extension works only on GitHub pages. Please navigate to a GitHub profile page to use the GitHub Talent Analyzer.
            </p>
            <button 
              className="navigation-modal-btn" 
              onClick={handleGoToGithub}
            >
              Go to GitHub
            </button>
          </>
        )}

        {context.type === "GITHUB_SYSTEM" && (
          <>
            <div className="navigation-modal-icon">
              <UserX size={28} />
            </div>
            <h3 className="navigation-modal-title">GitHub Profile Required</h3>
            <p className="navigation-modal-desc">
              Please open a GitHub user profile to use the GitHub Talent Analyzer.
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default NavigationModal;
