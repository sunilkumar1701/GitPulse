import React, { useState } from 'react';
import { Mail, Lock, Eye, EyeOff } from 'lucide-react';
import { FaGithub } from 'react-icons/fa';
import { supabase } from '../../services/supabaseClient';
import './Auth.css';

const Login = ({ onSwitchToSignup, onSwitchToForgotPassword, onLoginSuccess, defaultEmail = '', message = '' }) => {
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState(defaultEmail);
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);

  const validate = () => {
    const newErrors = {};
    if (!email) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = "Please enter a valid email address";
    }

    if (!password) {
      newErrors.password = "Password is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (validate()) {
      setIsLoading(true);
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password
      });
      setIsLoading(false);

      if (error) {
        setErrors({ submit: error.message });
      } else if (data.session) {
        onLoginSuccess();
      }
    }
  };

  return (
    <div className="auth-card">
      <div className="auth-header">
        <div className="auth-logo">
          <FaGithub size={32} />
        </div>
        <h1 className="auth-title">Welcome Back</h1>
        <p className="auth-subtitle">Login to analyze GitHub profiles</p>
      </div>

      {message && <div style={{ color: 'var(--success)', fontSize: '14px', marginBottom: '16px', textAlign: 'center' }}>{message}</div>}
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

        <div className="form-group">
          <label className="form-label" htmlFor="password">Password</label>
          <div className="input-wrapper">
            <Lock className="input-icon" size={18} />
            <input
              type={showPassword ? "text" : "password"}
              id="password"
              className={`auth-input ${errors.password ? 'error' : ''}`}
              placeholder="Enter your password"
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
          {errors.password && <span className="error-text">{errors.password}</span>}
        </div>

        <div className="auth-options">
          <button type="button" className="auth-link" onClick={() => onSwitchToForgotPassword(email)}>
            Forgot password?
          </button>
        </div>

        <button type="submit" className="auth-button" disabled={isLoading}>
          {isLoading ? 'Logging in...' : 'Login'}
        </button>
      </form>

      <div className="auth-footer">
        Don't have an account?{' '}
        <button type="button" className="auth-link" onClick={onSwitchToSignup}>
          Sign Up
        </button>
      </div>
    </div>
  );
};

export default Login;
