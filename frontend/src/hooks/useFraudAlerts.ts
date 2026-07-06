import { useEffect, useMemo, useState } from "react";
import { getFraudAlerts, getFraudSocketUrl } from "../services/api";
import type { AlertStats, FraudAlert, RiskLevel } from "../types";

const order: Record<RiskLevel, number> = {
  CRITICAL: 4,
  HIGH: 3,
  MEDIUM: 2,
  LOW: 1
};

export function useFraudAlerts() {
  const [alerts, setAlerts] = useState<FraudAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [connection, setConnection] = useState<"live" | "polling" | "offline">("polling");

  function reloadAlerts() {
    setLoading(true);
    return getFraudAlerts()
      .then((data) => {
        setAlerts(data.filter((alert) => alert.risk_level !== "LOW"));
        setConnection((current) => (current === "live" ? current : "polling"));
      })
      .catch(() => setConnection("offline"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    reloadAlerts().catch(() => undefined);

    const timer = window.setInterval(() => {
      getFraudAlerts()
        .then((data) => {
          setAlerts(data.filter((alert) => alert.risk_level !== "LOW"));
          setConnection((current) => (current === "live" ? current : "polling"));
        })
        .catch(() => setConnection("offline"));
    }, 5000);

    return () => {
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    let socket: WebSocket | null = null;

    try {
      socket = new WebSocket(getFraudSocketUrl());
      socket.onopen = () => setConnection("live");
      socket.onmessage = (event) => {
        const alert = JSON.parse(event.data) as FraudAlert;
        if (alert.risk_level === "LOW") return;
        setAlerts((current) => [alert, ...current].slice(0, 100));
      };
      socket.onerror = () => setConnection("polling");
      socket.onclose = () => setConnection("polling");
    } catch {
      setConnection("polling");
    }

    return () => socket?.close();
  }, []);

  const stats = useMemo<AlertStats>(() => {
    const total = alerts.length;
    const scoreTotal = alerts.reduce((sum, alert) => sum + Number(alert.risk_score || 0), 0);

    return {
      total,
      low: alerts.filter((alert) => alert.risk_level === "LOW").length,
      medium: alerts.filter((alert) => alert.risk_level === "MEDIUM").length,
      high: alerts.filter((alert) => alert.risk_level === "HIGH").length,
      critical: alerts.filter((alert) => alert.risk_level === "CRITICAL").length,
      avgScore: total ? Math.round(scoreTotal / total) : 0
    };
  }, [alerts]);

  const topAlerts = useMemo(
    () => [...alerts].sort((a, b) => order[b.risk_level] - order[a.risk_level] || Number(b.risk_score) - Number(a.risk_score)),
    [alerts]
  );

  return { alerts, topAlerts, stats, loading, connection, reloadAlerts };
}
