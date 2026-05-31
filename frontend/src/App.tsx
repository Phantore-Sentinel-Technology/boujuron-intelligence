import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { Analytics } from "./pages/Analytics";
import { Alerts } from "./pages/Alerts";
import { Users } from "./pages/Users";
import { Settings } from "./pages/Settings";
import { useFraudAlerts } from "./hooks/useFraudAlerts";

export default function App() {
  const fraud = useFraudAlerts();

  return (
    <AppShell connection={fraud.connection}>
      <Routes>
        <Route path="/" element={<Dashboard {...fraud} />} />
        <Route path="/analytics" element={<Analytics alerts={fraud.alerts} stats={fraud.stats} />} />
        <Route path="/alerts" element={<Alerts alerts={fraud.topAlerts} loading={fraud.loading} />} />
        <Route path="/users" element={<Users alerts={fraud.alerts} />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
