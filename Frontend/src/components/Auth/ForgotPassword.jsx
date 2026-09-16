import React, { useState } from 'react';
import { Mail } from 'lucide-react';
import { FaGithub } from 'react-icons/fa';
import { supabase } from '../../services/supabaseClient';
import './Auth.css';

const ForgotPassword = ({ onSwitchToLogin, defaultEmail = '' }) => {
  const [email, setEmail] = useState(defaultEmail);
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const validate = () => {
    const newErrors = {};
    if (!email) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = "Please enter a valid email address";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (validate()) {
      setIsLoading(true);
      
      const authWebUrl = import.meta.env.VITE_AUTH_WEB_URL || 'http://localhost:5173';
      
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${authWebUrl}/auth/reset-password`,
      });
      
      setIsLoading(false);

      if (error) {
        setErrors({ submit: error.message });
      } else {
        setSuccess(true);
      }
    }
  };

  return (
    <div className="auth-card">
      <div className="auth-header">
        <div className="auth-logo">
          <FaGithub size={32} />
        </div>
        <h1 className="auth-title">Forgot Password?</h1>
        <p className="auth-subtitle">Enter the email address associated with your account and we'll send you a password reset link.</p>
      </div>

      {success ? (
        <div style={{ textAlign: 'center', margin: '20px 0' }}>
          <p style={{ color: 'var(--success)', marginBottom: '20px' }}>
            If an account exists for this email address, we've sent a password reset link.
          </p>
          <button type="button" className="auth-button" onClick={() => onSwitchToLogin(email)}>
            Back to Login
          </button>
        </div>
      ) : (
        <>
          {errors.submit && <div style={{ color: 'var(--danger)', fontSize: '14px', marginBottom: '16px', textAlign: 'center' }}>{errors.submit}</div>}

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <div className="form-group">
              <label className="form-label" htmlFor="email">Email</label>
              <div className="input-wrapper">
                <Mail className="input-icon" size={18} />
                <input
                  type="email"
                  id="email"
                  className={`auth-input ${errors.email ? 'error' : ''}`}
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              {errors.email && <span className="error-text">{errors.email}</span>}
            </div>

            <button type="submit" className="auth-button" disabled={isLoading}>
              {isLoading ? 'Sending...' : 'Send Reset Link'}
            </button>
          </form>

          <div className="auth-footer">
            <button type="button" className="auth-link" onClick={() => onSwitchToLogin(email)}>
              Back to Login
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ForgotPassword;
