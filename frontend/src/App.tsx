import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { Activity } from "./pages/Activity";
import { History } from "./pages/History";
import { Analytics } from "./pages/Analytics";
import { Executive } from "./pages/Executive";
import { Alerts } from "./pages/Alerts";
import { Cases } from "./pages/Cases";
import { CaseDetail } from "./pages/CaseDetail";
import { Users } from "./pages/Users";
import { Settings } from "./pages/Settings";
import { CustomerProfile } from "./pages/CustomerProfile";
import { ForgotPassword } from "./pages/ForgotPassword";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { ResetPassword } from "./pages/ResetPassword";
import { useFraudAlerts } from "./hooks/useFraudAlerts";
import { useAuth } from "./context/AuthContext";

export default function App() {
  const { booting, user } = useAuth();
  const location = useLocation();

  if (booting) return <div className="empty-state">Starting Boujuron console...</div>;

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="*" element={<Navigate to="/login" replace state={{ from: location }} />} />
      </Routes>
    );
  }

  return <AuthenticatedApp />;
}

function AuthenticatedApp() {
  const fraud = useFraudAlerts();

  return (
    <AppShell connection={fraud.connection}>
      <Routes>
        <Route path="/" element={<Dashboard {...fraud} />} />
        <Route path="/activity" element={<Activity />} />
        <Route path="/history" element={<History />} />
        <Route path="/executive" element={<Executive />} />
        <Route path="/analytics" element={<Analytics alerts={fraud.alerts} stats={fraud.stats} />} />
        <Route path="/alerts" element={<Alerts alerts={fraud.topAlerts} loading={fraud.loading} />} />
        <Route path="/cases" element={<Cases />} />
        <Route path="/cases/:caseId" element={<CaseDetail />} />
        <Route path="/users" element={<Users alerts={fraud.alerts} />} />
        <Route path="/customers/:userId" element={<CustomerProfile />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="/register" element={<Navigate to="/" replace />} />
        <Route path="/forgot-password" element={<Navigate to="/" replace />} />
        <Route path="/reset-password" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
