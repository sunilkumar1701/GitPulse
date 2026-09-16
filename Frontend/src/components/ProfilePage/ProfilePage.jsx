import React, { useState, useEffect } from 'react';
import { ArrowLeft, Edit2, LogOut, Trash2, Check, X, RefreshCw } from 'lucide-react';
import { supabase } from '../../services/supabaseClient';
import apiClient from '../../services/apiClient';
import './ProfilePage.css';

const ProfilePage = ({ onBack, onLogout }) => {
  const [user, setUser] = useState(null);
  const [email, setEmail] = useState('');
  const [isEditingEmail, setIsEditingEmail] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [isEditingName, setIsEditingName] = useState(false);
  const [newName, setNewName] = useState('');
  const [isSavingName, setIsSavingName] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [isHoveringToast, setIsHoveringToast] = useState(false);
  const [isPendingEmailVerification, setIsPendingEmailVerification] = useState(false);

  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  useEffect(() => {
    fetchUser();

    // Listen for auth changes (e.g. when email is verified in another tab)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'USER_UPDATED' || event === 'SIGNED_IN') {
        if (session?.user) {
          setUser(session.user);
          setEmail(session.user.email);
          setNewEmail(session.user.email);
          setIsPendingEmailVerification(false);
        } else {
          fetchUser();
        }
      }
    });

    // Refresh when window regains focus
    const handleFocus = () => {
      fetchUser();
    };
    window.addEventListener('focus', handleFocus);

    return () => {
      subscription.unsubscribe();
      window.removeEventListener('focus', handleFocus);
    };
  }, []);

  // Toast auto-hide logic for success
  useEffect(() => {
    let timer;
    if (successMsg && !isHoveringToast) {
      timer = setTimeout(() => {
        setSuccessMsg(null);
      }, 1500);
    }
    return () => clearTimeout(timer);
  }, [successMsg, isHoveringToast]);

  // Toast auto-hide logic for error
  useEffect(() => {
    let timer;
    if (error && !isHoveringToast) {
      timer = setTimeout(() => {
        setError(null);
      }, 3000); // Errors stay a bit longer (3s)
    }
    return () => clearTimeout(timer);
  }, [error, isHoveringToast]);

  // Poll for email update when pending
  useEffect(() => {
    let interval;
    if (isPendingEmailVerification) {
      interval = setInterval(async () => {
        const { data: { user } } = await supabase.auth.getUser();
        if (user && user.email !== email) {
          setUser(user);
          setEmail(user.email);
          setNewEmail(user.email);
          setIsPendingEmailVerification(false);
          setSuccessMsg('Email updated successfully!');
        }
      }, 3000); // Check every 3 seconds
    }
    return () => clearInterval(interval);
  }, [isPendingEmailVerification, email]);

  const fetchUser = async () => {
    setIsLoading(true);
    const { data: { user }, error } = await supabase.auth.getUser();
    if (error) {
      setError('Failed to load profile');
    } else if (user) {
      setUser(user);
      setEmail(user.email);
      setNewEmail(user.email);
      const fetchedName = user.user_metadata?.full_name || user.user_metadata?.name || user.user_metadata?.display_name || '';
      setDisplayName(fetchedName);
      setNewName(fetchedName);
    }
    setIsLoading(false);
  };

  const getAvatarUrl = () => {
    if (user?.user_metadata?.avatar_url) {
      return user.user_metadata.avatar_url;
    }
    return `https://ui-avatars.com/api/?name=${encodeURIComponent(displayName || user?.email || 'User')}&background=random`;
  };

  const handleEditName = () => {
    setIsEditingName(true);
    setError(null);
    setSuccessMsg(null);
  };

  const handleCancelEditName = () => {
    setIsEditingName(false);
    setNewName(displayName);
    setError(null);
  };

  const handleSaveName = async () => {
    const trimmedName = newName.trim();
    if (!trimmedName) {
      setError('Display name cannot be empty.');
      return;
    }
    if (trimmedName === displayName) {
      setError('Display name is unchanged.');
      return;
    }

    setIsSavingName(true);
    setError(null);
    setSuccessMsg(null);

    const { data, error } = await supabase.auth.updateUser({ data: { full_name: trimmedName } });

    if (error) {
      setError(error.message);
    } else {
      setDisplayName(trimmedName);
      setSuccessMsg('Display name updated successfully.');
      setIsEditingName(false);
      
      // Update the user state to reflect the new metadata for avatar
      setUser(prev => ({
        ...prev,
        user_metadata: {
          ...prev.user_metadata,
          full_name: trimmedName
        }
      }));
    }
    setIsSavingName(false);
  };

  const handleEditEmail = () => {
    setIsEditingEmail(true);
    setError(null);
    setSuccessMsg(null);
  };

  const handleCancelEdit = () => {
    setIsEditingEmail(false);
    setNewEmail(email);
    setError(null);
  };

  const handleSaveEmail = async () => {
    const trimmedEmail = newEmail.trim();
    if (!trimmedEmail) {
      setError('Email cannot be empty.');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      setError('Invalid email format.');
      return;
    }
    if (trimmedEmail === email) {
      setError('Email is unchanged.');
      return;
    }

    setIsSaving(true);
    setError(null);
    setSuccessMsg(null);

    const { data, error } = await supabase.auth.updateUser(
      { email: trimmedEmail },
      { emailRedirectTo: `${window.location.origin}/auth/verify` }
    );

    if (error) {
      setError(error.message);
    } else {
      setSuccessMsg('Email change requested. Please check your email to confirm the new address.');
      setIsEditingEmail(false);
      setIsPendingEmailVerification(true);
    }
    setIsSaving(false);
  };

  const handleLogout = async () => {
    setIsSaving(true);
    await supabase.auth.signOut();
    onLogout();
  };

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    setError(null);
    try {
      await apiClient.delete('/user/account');
      // On success, backend deletes auth user, which invalidates token
      // Wait a moment then log out locally
      await supabase.auth.signOut();
      onLogout();
    } catch (err) {
      setError(err.message || 'Failed to delete account. Please try again later.');
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  if (isLoading) {
    return (
      <div className="profile-page-loading">
        <div className="spin-icon"><RefreshCw size={24} /></div>
        <p>Loading Profile...</p>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="profile-header">
        <button className="back-btn" onClick={onBack}>
          <ArrowLeft size={20} />
          <span>Back to Dashboard</span>
        </button>
        <h2 className="profile-title">Account Settings</h2>
      </div>

      <div className="profile-page-card">
        <div className="profile-page-avatar-container">
          <img src={getAvatarUrl()} alt="User Avatar" className="profile-page-avatar" />
        </div>

        <div className="profile-section">
          <label className="profile-label">Display Name</label>
          {isEditingName ? (
            <div className="profile-edit-group">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="profile-input"
                disabled={isSavingName}
                placeholder="Enter your name"
              />
              <div className="profile-edit-actions">
                <button 
                  className="profile-action-btn cancel-btn" 
                  onClick={handleCancelEditName}
                  disabled={isSavingName}
                >
                  <X size={16} /> Cancel
                </button>
                <button 
                  className="profile-action-btn save-btn" 
                  onClick={handleSaveName}
                  disabled={isSavingName}
                >
                  {isSavingName ? 'Saving...' : <><Check size={16} /> Save</>}
                </button>
              </div>
            </div>
          ) : (
            <div className="profile-display-group">
              <span className="profile-value">{displayName || 'No name set'}</span>
              <button className="profile-edit-btn" onClick={handleEditName}>
                <Edit2 size={14} /> Edit
              </button>
            </div>
          )}
        </div>

        <div className="profile-section">
          <label className="profile-label">Email</label>
          {isEditingEmail ? (
            <div className="profile-edit-group">
              <input
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                className="profile-input"
                disabled={isSaving}
              />
              <div className="profile-edit-actions">
                <button 
                  className="profile-action-btn cancel-btn" 
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                >
                  <X size={16} /> Cancel
                </button>
                <button 
                  className="profile-action-btn save-btn" 
                  onClick={handleSaveEmail}
                  disabled={isSaving}
                >
                  {isSaving ? 'Saving...' : <><Check size={16} /> Save</>}
                </button>
              </div>
            </div>
          ) : (
            <div className="profile-display-group">
              <span className="profile-value">{email}</span>
              <button className="profile-edit-btn" onClick={handleEditEmail}>
                <Edit2 size={14} /> Edit
              </button>
            </div>
          )}
        </div>

        <div className="profile-divider"></div>

        <div className="profile-danger-zone">
          <button className="profile-danger-btn logout-btn" onClick={() => setShowLogoutModal(true)}>
            <LogOut size={18} /> Logout
          </button>
          
          <button className="profile-danger-btn delete-btn" onClick={() => setShowDeleteModal(true)}>
            <Trash2 size={18} /> Delete Account
          </button>
        </div>
      </div>

      {showLogoutModal && (
        <div className="profile-modal-overlay">
          <div className="profile-modal">
            <h3>Logout</h3>
            <p>Are you sure you want to logout?</p>
            <div className="profile-modal-actions">
              <button className="modal-btn cancel-btn" onClick={() => setShowLogoutModal(false)}>No</button>
              <button className="modal-btn confirm-btn" onClick={handleLogout} disabled={isSaving}>
                {isSaving ? 'Logging out...' : 'Yes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showDeleteModal && (
        <div className="profile-modal-overlay">
          <div className="profile-modal danger-modal">
            <h3>Delete Account?</h3>
            <p>If you delete this account, all your data will be permanently lost.<br/>This action cannot be undone.</p>
            <div className="profile-modal-actions">
              <button className="modal-btn cancel-btn" onClick={() => setShowDeleteModal(false)} disabled={isDeleting}>No</button>
              <button className="modal-btn danger-confirm-btn" onClick={handleDeleteAccount} disabled={isDeleting}>
                {isDeleting ? 'Deleting...' : 'Yes, Delete Account'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Success Toast Notification */}
      {successMsg && (
        <div 
          className="profile-toast-success"
          onMouseEnter={() => setIsHoveringToast(true)}
          onMouseLeave={() => setIsHoveringToast(false)}
        >
          <Check size={16} />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Error Toast Notification */}
      {error && (
        <div 
          className="profile-toast-error"
          onMouseEnter={() => setIsHoveringToast(true)}
          onMouseLeave={() => setIsHoveringToast(false)}
        >
          <X size={16} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};

export default ProfilePage;
