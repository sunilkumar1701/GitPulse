import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle } from 'lucide-react';
import { supabase } from '../../services/supabaseClient';
import './Auth.css';

const AuthVerify = () => {
  const [status, setStatus] = useState('loading'); // 'loading', 'success', 'error', 'pending'
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    const handleEmailVerification = async () => {
      // When Supabase redirects back, it might have an error in the URL hash or query params
      const hashParams = new URLSearchParams(window.location.hash.substring(1));
      const queryParams = new URLSearchParams(window.location.search);

      const error = hashParams.get('error_description') || queryParams.get('error_description') || hashParams.get('error') || queryParams.get('error');
      const message = hashParams.get('message') || queryParams.get('message');

      if (error) {
        setStatus('error');
        setErrorMessage(decodeURIComponent(error).replace(/\+/g, ' '));
        return;
      }

      if (message) {
        setStatus('pending');
        setErrorMessage(decodeURIComponent(message).replace(/\+/g, ' '));
        return;
      }

      // Supabase's email verification link establishes a session
      const { data: { session } } = await supabase.auth.getSession();

      if (session) {
        setStatus('success');
      } else {
        // If there's no session and no explicit error, wait a little bit just in case
        setTimeout(async () => {
          const { data: { session: delayedSession } } = await supabase.auth.getSession();
          if (delayedSession) {
            setStatus('success');
          } else {
            setStatus('error');
            setErrorMessage('Email verification failed. The link may be invalid or expired.');
          }
        }, 1000);
      }
    };

    handleEmailVerification();
  }, []);

  return (
    <div className="auth-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
      <div className="auth-card" style={{ textAlign: 'center', padding: '40px', maxWidth: '500px' }}>
        {status === 'loading' && (
          <div>
            <h2 style={{ color: 'var(--text-primary)' }}>Verifying...</h2>
            <p style={{ color: 'var(--text-secondary)', marginTop: '10px' }}>Please wait while we verify your email address.</p>
          </div>
        )}

        {status === 'success' && (
          <div>
            <CheckCircle size={64} color="var(--success)" style={{ margin: '0 auto 20px auto' }} />
            <h1 className="auth-title">Email Verified Successfully!</h1>
            <p className="auth-subtitle" style={{ marginTop: '10px', marginBottom: '30px' }}>
              Your email address has been verified. You can now sign in to the GitHub Developer Analyzer.
            </p>
            <p style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>
              Open the extension on GitHub to continue.
            </p>
          </div>
        )}

        {status === 'pending' && (
          <div>
            <CheckCircle size={64} color="var(--primary-main)" style={{ margin: '0 auto 20px auto' }} />
            <h1 className="auth-title">Almost There!</h1>
            <p className="auth-subtitle" style={{ marginTop: '10px', marginBottom: '20px', color: 'var(--text-primary)' }}>
              {errorMessage}
            </p>
            <div style={{ backgroundColor: 'rgba(59, 130, 246, 0.1)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.3)', marginBottom: '20px' }}>
              <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: '1.5' }}>
                <strong>Note:</strong> Because "Secure email change" is enabled in your Supabase settings, you must click the links sent to <strong>both</strong> your old and new email addresses.
              </p>
            </div>
          </div>
        )}

        {status === 'error' && (
          <div>
            <XCircle size={64} color="var(--danger)" style={{ margin: '0 auto 20px auto' }} />
            <h1 className="auth-title">Verification Error</h1>
            <p className="auth-subtitle" style={{ marginTop: '10px', color: 'var(--danger)' }}>
              {errorMessage}
            </p>
            {errorMessage.includes('expired') && (
              <p style={{ marginTop: '20px', color: 'var(--text-secondary)', fontSize: '14px', lineHeight: '1.5' }}>
                If you just requested this change, make sure you click the link in the <strong>newest</strong> email. Alternatively, you can disable "Secure email change" in your Supabase Authentication settings to make this a 1-click process.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AuthVerify;
