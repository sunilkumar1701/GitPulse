import { useEffect, useMemo, useState } from "react";
import "./ProfileCard.css";
import { getProfile, getDeveloperScore } from "../../services/githubService";
import { useDashboardContext } from "../../context/DashboardContext";

const ProfileCard = ({ username, onLoaded, refreshKey }) => {
  const { updateDashboardData } = useDashboardContext();

  const [state, setState] = useState({
    profile: null,
    developerScore: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let mounted = true;

    const fetchProfile = async () => {
      try {
        console.log("🔄 Refetching ProfileCard");

        const [profileData, scoreData] = await Promise.all([
          getProfile(username),
          getDeveloperScore(username),
        ]);

        if (!mounted) return;

        setState({
          profile: profileData,
          developerScore: scoreData,
          loading: false,
          error: null,
        });

        updateDashboardData("developerScore", scoreData);
        updateDashboardData("profileCard", profileData);

        console.log("Developer Score:", scoreData);

        console.log("✅ ProfileCard Loaded");

        onLoaded?.();
      } catch (error) {
        console.error("ProfileCard Error:", error);

        if (!mounted) return;

        setState({
          profile: null,
          developerScore: null,
          loading: false,
          error: "Unable to load profile.",
        });
      }
    };

    fetchProfile();

    return () => {
      mounted = false;
    };
  }, [username, refreshKey, updateDashboardData, onLoaded]);

  const { profile, developerScore, loading, error } = state;

  const score = developerScore?.score || 0;

  const dashOffset = 220 - (220 * score) / 100;

  const websiteLabel = useMemo(() => {
    if (!profile?.blog) return "";

    try {
      const hostname = new URL(
        profile.blog.startsWith("http")
          ? profile.blog
          : `https://${profile.blog}`,
      ).hostname;

      return hostname.replace("www.", "");
    } catch {
      return profile.blog;
    }
  }, [profile?.blog]);

  if (loading || error) {
    const isError = !!error;
    const skeletonClass = isError ? "skeleton-error" : "skeleton";
    return (
      <div className="module-card profile-card" style={{ flexDirection: 'row', alignItems: 'center', position: 'relative' }}>
        <div className="profile-left">
          <div className={`${skeletonClass} skeleton-circle`} style={{ width: '80px', height: '80px', flexShrink: 0 }}></div>
          <div className="profile-details" style={{ width: '100%' }}>
            <div className={`${skeletonClass} skeleton-title`} style={{ width: '60%', margin: '0 0 4px 0' }}></div>
            <div className={`${skeletonClass} skeleton-text short`} style={{ margin: '0 0 12px 0' }}></div>
            <div className="profile-meta">
              <div className={`${skeletonClass} skeleton-text`} style={{ width: '40%' }}></div>
              <div className={`${skeletonClass} skeleton-text`} style={{ width: '50%' }}></div>
            </div>
          </div>
        </div>
        <div className="profile-right" style={{ justifyContent: 'center' }}>
          <div className={`${skeletonClass} skeleton-box`} style={{ width: '100px', height: '30px', marginBottom: '16px', borderRadius: '16px' }}></div>
          <div className={`${skeletonClass} skeleton-circle`} style={{ width: '120px', height: '60px', borderRadius: '60px 60px 0 0' }}></div>
        </div>
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
    <div className="module-card profile-card">
      {/* LEFT SIDE */}

      <div className="profile-left">
        <img
          src={profile.avatar_url}
          alt={profile.name}
          className="profile-avatar"
          loading="lazy"
          onError={(e) => {
            e.target.src =
              "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png";
          }}
        />

        <div className="profile-details">
          <h2>{profile.name || profile.login}</h2>

          <p className="username">@{profile.login}</p>

          <div className="profile-meta">
            {profile.location && (
              <div className="meta-item">
                <svg
                  className="meta-icon"
                  viewBox="0 0 16 16"
                  fill="currentColor"
                >
                  <path d="M8 0a5 5 0 0 0-5 5c0 3.75 5 11 5 11s5-7.25 5-11a5 5 0 0 0-5-5Zm0 7a2 2 0 1 1 0-4 2 2 0 0 1 0 4Z" />
                </svg>

                <span>{profile.location}</span>
              </div>
            )}

            {profile.blog && (
              <a
                href={
                  profile.blog.startsWith("http")
                    ? profile.blog
                    : `https://${profile.blog}`
                }
                target="_blank"
                rel="noopener noreferrer"
                className="meta-item website-link"
              >
                <svg
                  className="meta-icon"
                  viewBox="0 0 16 16"
                  fill="currentColor"
                >
                  <path d="M7.775 3.275a3.25 3.25 0 0 1 4.596 4.596l-1.944 1.944a3.25 3.25 0 0 1-4.596 0 .75.75 0 0 1 1.06-1.06 1.75 1.75 0 0 0 2.475 0L11.31 6.81a1.75 1.75 0 1 0-2.475-2.475L7.775 5.395a.75.75 0 1 1-1.06-1.06l1.06-1.06Z" />
                  <path d="M8.225 12.725a3.25 3.25 0 0 1-4.596-4.596l1.944-1.944a3.25 3.25 0 0 1 4.596 0 .75.75 0 0 1-1.06 1.06 1.75 1.75 0 0 0-2.475 0L4.69 9.19a1.75 1.75 0 1 0 2.475 2.475l1.06-1.06a.75.75 0 1 1 1.06 1.06l-1.06 1.06Z" />
                </svg>

                <span>{websiteLabel}</span>
              </a>
            )}
          </div>
        </div>
      </div>

      {/* RIGHT SIDE */}

      <div className="profile-right">
        <div className="score-info">
          <div className="score-label">
            <span className="crown">👑</span>

            <div>
              <p className="score-heading">Developer</p>

              <p className="score-heading">Score</p>
            </div>
          </div>

          <div className="expert-badge">
            {developerScore?.level || "Beginner"}
          </div>
        </div>

        <div className="gauge-wrapper">
          <svg className="score-gauge" viewBox="0 0 200 120">
            <defs>
              <linearGradient
                id="scoreGradient"
                x1="0%"
                y1="0%"
                x2="100%"
                y2="0%"
              >
                <stop offset="0%" stopColor="#9333EA" />

                <stop offset="100%" stopColor="#22C55E" />
              </linearGradient>
            </defs>

            <path d="M30 100 A70 70 0 0 1 170 100" className="gauge-track" />

            <path
              d="M30 100 A70 70 0 0 1 170 100"
              className="gauge-progress"
              style={{
                strokeDasharray: 220,
                strokeDashoffset: dashOffset,
              }}
            />
          </svg>

          <div className="score-center">
            <h2>{score}</h2>

            <span>/100</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfileCard;
