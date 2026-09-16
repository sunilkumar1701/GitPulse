import React, { useState } from 'react';
import { Mail, Lock, Eye, EyeOff, User, Check, X } from 'lucide-react';
import { FaGithub } from 'react-icons/fa';
import { supabase } from '../../services/supabaseClient';
import './Auth.css';

const Signup = ({ onSwitchToLogin, onLoginSuccess }) => {
  const [showPassword, setShowPassword] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);

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

  const validate = () => {
    const newErrors = {};

    if (!name.trim()) {
      newErrors.name = "Name is required";
    }

    if (!email) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = "Please enter a valid email address";
    }

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
      
      const authWebUrl = import.meta.env.VITE_AUTH_WEB_URL || 'http://localhost:5173';
      
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: name
          },
          emailRedirectTo: `${authWebUrl}/auth/verify`
        }
      });
      setIsLoading(false);

      if (error) {
        setErrors({ submit: error.message });
      } else if (data.session) {
        onLoginSuccess();
      } else {
        // Session is null, meaning email confirmation is required
        onSwitchToLogin(email, "Your account has been created. Please check your email and verify your address before logging in.");
      }
    }
  };

  return (
    <div className="auth-card">
      <div className="auth-header">
        <div className="auth-logo">
          <FaGithub size={32} />
        </div>
        <h1 className="auth-title">Create Account</h1>
        <p className="auth-subtitle">Join us to analyze GitHub profiles</p>
      </div>

      {errors.submit && <div style={{ color: 'var(--danger)', fontSize: '14px', marginBottom: '16px', textAlign: 'center' }}>{errors.submit}</div>}

      <form className="auth-form" onSubmit={handleSubmit} noValidate>
        <div className="form-group">
          <label className="form-label" htmlFor="name">Name</label>
          <div className="input-wrapper">
            <User className="input-icon" size={18} />
            <input
              type="text"
              id="name"
              className={`auth-input ${errors.name ? 'error' : ''}`}
              placeholder="Enter your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          {errors.name && <span className="error-text">{errors.name}</span>}
        </div>

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
              placeholder="Create a password"
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
            {reqList.map(req => {
              // "Only show the remaining requirements that are still needed"
              // We'll show satisfied ones with a check, but if user prefers strictly hiding them, 
              // we can hide them. But to satisfy "Show each with ✓ when satisfied", we'll keep them 
              // and style them differently.
              return (
                <li key={req.id} className={`req-item ${req.met ? 'met' : 'unmet'}`}>
                  {req.met ? <Check size={14} className="req-icon" /> : <X size={14} className="req-icon" />}
                  <span>{req.text}</span>
                </li>
              );
            })}
          </ul>
          
          {errors.password && <span className="error-text">{errors.password}</span>}
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="confirmPassword">Confirm Password</label>
          <div className="input-wrapper">
            <Lock className="input-icon" size={18} />
            <input
              type={showPassword ? "text" : "password"}
              id="confirmPassword"
              className={`auth-input ${errors.confirmPassword ? 'error' : ''}`}
              placeholder="Confirm your password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>
          {errors.confirmPassword && <span className="error-text">{errors.confirmPassword}</span>}
        </div>

        <button type="submit" className="auth-button" disabled={isLoading}>
          {isLoading ? 'Signing Up...' : 'Sign Up'}
        </button>

        <p className="terms-text">
          By signing up, you agree to our Terms of Service and Privacy Policy.
        </p>
      </form>

      <div className="auth-footer">
        Already have an account?{' '}
        <button type="button" className="auth-link" onClick={() => onSwitchToLogin()}>
          Login
        </button>
      </div>
    </div>
  );
};

export default Signup;
