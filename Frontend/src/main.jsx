import { createRoot } from "react-dom/client";

import "./index.css";
import App from "./App.jsx";
import AuthVerify from "./components/Auth/AuthVerify.jsx";
import ResetPassword from "./components/Auth/ResetPassword.jsx";

import { DashboardProvider } from "./context/DashboardContext";

const path = window.location.pathname;

const hash = window.location.hash;

const renderApp = () => {
  if (
    path.startsWith('/auth/verify') || 
    hash.includes('message=Confirmation+link+accepted') || 
    hash.includes('type=email_change') ||
    hash.includes('error_code=otp_expired')
  ) {
    return <AuthVerify />;
  }
  
  if (path.startsWith('/auth/reset-password')) {
    return <ResetPassword />;
  }

  return (
    <DashboardProvider>
      <App />
    </DashboardProvider>
  );
};

createRoot(document.getElementById("root")).render(renderApp());