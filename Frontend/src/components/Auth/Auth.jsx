import React, { useState } from 'react';
import Login from './Login';
import Signup from './Signup';
import ForgotPassword from './ForgotPassword';
import './Auth.css';

const Auth = ({ onLoginSuccess }) => {
  const [view, setView] = useState('login'); // 'login', 'signup', 'forgot-password'
  const [prefilledEmail, setPrefilledEmail] = useState('');
  const [message, setMessage] = useState('');

  const handleSwitchToLogin = (email = '', msg = '') => {
    setPrefilledEmail(email);
    setMessage(msg);
    setView('login');
  };

  const handleSwitchToSignup = () => {
    setMessage('');
    setView('signup');
  };

  const handleSwitchToForgotPassword = (email = '') => {
    setPrefilledEmail(email);
    setMessage('');
    setView('forgot-password');
  };

  return (
    <div className="auth-container">
      {view === 'login' && (
        <Login 
          onSwitchToSignup={handleSwitchToSignup} 
          onSwitchToForgotPassword={handleSwitchToForgotPassword}
          onLoginSuccess={onLoginSuccess}
          defaultEmail={prefilledEmail}
          message={message}
        />
      )}
      {view === 'signup' && (
        <Signup 
          onSwitchToLogin={handleSwitchToLogin} 
          onLoginSuccess={onLoginSuccess}
        />
      )}
      {view === 'forgot-password' && (
        <ForgotPassword 
          onSwitchToLogin={handleSwitchToLogin} 
          defaultEmail={prefilledEmail}
        />
      )}
    </div>
  );
};

export default Auth;
