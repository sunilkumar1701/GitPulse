import React, { useEffect, useState } from 'react';
import { Lock, Eye, EyeOff, Check, X } from 'lucide-react';
import { supabase } from '../../services/supabaseClient';
import './Auth.css';

const ResetPassword = () => {
  const [showPassword, setShowPassword] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState('loading'); // 'loading', 'valid', 'success', 'error'
  const [errorMessage, setErrorMessage] = useState('');

  const passwordReqs = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    special: /[^A-Za-z0-9]/.test(password)
  };

  const reqList = [
    { id: 'length', text: 'Minimum 8 characters', met: passwordReqs.length },
    { id: 'uppercase', text: 'At least 1 uppercase letter', met: passwordReqs.uppercase },
    { id: 'special', text: 'At least 1 special character', met: passwordReqs.special }
  ];

  useEffect(() => {
    // Check for errors in URL
    const hashParams = new URLSearchParams(window.location.hash.substring(1));
    const queryParams = new URLSearchParams(window.location.search);

    const error = hashParams.get('error_description') || queryParams.get('error_description') || hashParams.get('error') || queryParams.get('error');

    if (error) {
      setStatus('error');
      setErrorMessage(decodeURIComponent(error).replace(/\+/g, ' '));
      return;
    }

    // Check if we have an active recovery session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setStatus('valid');
      } else {
        // Wait a bit to see if the session resolves via event listener
        setTimeout(async () => {
          const { data: { session: delayedSession } } = await supabase.auth.getSession();
          if (delayedSession) {
            setStatus('valid');
          } else {
            setStatus('error');
            setErrorMessage('This password reset link is invalid or has expired. Please request a new password reset link.');
          }
        }, 1000);
      }
    });

    // Listen for the recovery event just in case
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY') {
        setStatus('valid');
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const validate = () => {
    const newErrors = {};

    if (!passwordReqs.length || !passwordReqs.uppercase || !passwordReqs.special) {
      newErrors.password = "Please meet all password requirements";
    }

    if (!confirmPassword) {
      newErrors.confirmPassword = "Please confirm your password";
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (validate()) {
      setIsLoading(true);
      const { error } = await supabase.auth.updateUser({
        password: password
      });
      setIsLoading(false);

      if (error) {
        setErrors({ submit: error.message });
      } else {
        // Sign out the user after updating password so they have to login with the new one
        await supabase.auth.signOut();
        setStatus('success');
      }
    }
  };

  if (status === 'loading') {
    return (
      <div className="auth-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
        <div className="auth-card" style={{ textAlign: 'center', padding: '40px' }}>
          <h2 style={{ color: 'var(--text-primary)' }}>Loading...</h2>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="auth-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
        <div className="auth-card" style={{ textAlign: 'center', padding: '40px' }}>
          <h1 className="auth-title">Reset Link Invalid or Expired</h1>
          <p className="auth-subtitle" style={{ marginTop: '10px', color: 'var(--danger)', marginBottom: '30px' }}>
            {errorMessage}
          </p>
          <button 
            className="auth-button" 
            onClick={() => {
              // Direct user to open extension or a known web url, but we can't open extension directly easily.
              // We'll instruct them to open the extension.
              window.close();
            }}
          >
            Close Window
          </button>
          <p style={{ marginTop: '20px', color: 'var(--text-secondary)' }}>
            Please open the extension and click "Forgot Password" to request a new link.
          </p>
        </div>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="auth-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
        <div className="auth-card" style={{ textAlign: 'center', padding: '40px' }}>
          <Check size={64} color="var(--success)" style={{ margin: '0 auto 20px auto' }} />
          <h1 className="auth-title">Password Updated Successfully!</h1>
          <p className="auth-subtitle" style={{ marginTop: '10px', marginBottom: '30px' }}>
            Your password has been updated successfully. You can now sign in with your new password.
          </p>
          <p style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>
            Open the extension on GitHub to login.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
      <div className="auth-card">
        <div className="auth-header">
          <h1 className="auth-title">Reset Your Password</h1>
          <p className="auth-subtitle">Enter your new password below.</p>
        </div>

        {errors.submit && <div style={{ color: 'var(--danger)', fontSize: '14px', marginBottom: '16px', textAlign: 'center' }}>{errors.submit}</div>}

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label className="form-label" htmlFor="password">New Password</label>
            <div className="input-wrapper">
              <Lock className="input-icon" size={18} />
              <input
                type={showPassword ? "text" : "password"}
                id="password"
                className={`auth-input ${errors.password ? 'error' : ''}`}
                placeholder="Create a new password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            
            <ul className="password-requirements">
              {reqList.map(req => (
                <li key={req.id} className={`req-item ${req.met ? 'met' : 'unmet'}`}>
                  {req.met ? <Check size={14} className="req-icon" /> : <X size={14} className="req-icon" />}
                  <span>{req.text}</span>
                </li>
              ))}
            </ul>
            
            {errors.password && <span className="error-text">{errors.password}</span>}
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="confirmPassword">Confirm New Password</label>
            <div className="input-wrapper">
              <Lock className="input-icon" size={18} />
              <input
                type={showPassword ? "text" : "password"}
                id="confirmPassword"
                className={`auth-input ${errors.confirmPassword ? 'error' : ''}`}
                placeholder="Confirm your new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </div>
            {errors.confirmPassword && <span className="error-text">{errors.confirmPassword}</span>}
          </div>

          <button type="submit" className="auth-button" disabled={isLoading}>
            {isLoading ? 'Updating...' : 'Update Password'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ResetPassword;
