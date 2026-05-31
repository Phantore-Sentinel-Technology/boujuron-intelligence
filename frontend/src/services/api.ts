import axios from "axios";
import type { FraudAlert } from "../types";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || ""
});

export async function getFraudAlerts(limit = 100) {
  const response = await api.get<FraudAlert[]>("/fraud-alerts", {
    params: { limit }
  });
  return response.data;
}

export function getFraudSocketUrl() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${window.location.host}/ws/fraud`;
}
