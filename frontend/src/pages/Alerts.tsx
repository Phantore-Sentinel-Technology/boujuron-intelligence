import type { FraudAlert } from "../types";
import { FraudTable } from "../components/FraudTable";

export function Alerts({ alerts, loading }: { alerts: FraudAlert[]; loading: boolean }) {
  return <FraudTable alerts={alerts} loading={loading} />;
}
