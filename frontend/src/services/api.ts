import axios from "axios";
import type { AuthResponse, AuthUser, CaseDetail, CaseSummary, CaseUpdate, FraudAlert, UserRiskProfile, UserRole } from "../types";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || ""
});

export const authStorageKey = "boujuron.auth.token";

export function setAuthToken(token: string | null) {
  if (token) {
    localStorage.setItem(authStorageKey, token);
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
    return;
  }
  localStorage.removeItem(authStorageKey);
  delete api.defaults.headers.common.Authorization;
}

export function hydrateAuthToken() {
  const token = localStorage.getItem(authStorageKey);
  if (token) setAuthToken(token);
  return token;
}

export async function login(email: string, password: string) {
  const response = await api.post<AuthResponse>("/auth/login", { email, password });
  setAuthToken(response.data.access_token);
  return response.data;
}

export async function register(name: string, email: string, password: string, role: UserRole) {
  const response = await api.post<AuthResponse>("/auth/register", { name, email, password, role });
  return response.data;
}

export async function getCurrentUser() {
  const response = await api.get<AuthUser>("/auth/me");
  return response.data;
}

export async function getFraudAlerts(limit = 100) {
  const response = await api.get<FraudAlert[]>("/fraud-alerts", {
    params: { limit }
  });
  return response.data;
}

export async function getUserRiskProfile(userId: string) {
  const response = await api.get<UserRiskProfile>(`/customers/${encodeURIComponent(userId)}/profile`);
  return response.data;
}

export async function getCases(filters: Record<string, string> = {}) {
  const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
  const response = await api.get<CaseSummary[]>("/cases", { params });
  return response.data;
}

export async function getCase(caseId: string | number) {
  const response = await api.get<CaseDetail>(`/cases/${caseId}`);
  return response.data;
}

export async function updateCase(caseId: string | number, update: CaseUpdate) {
  const response = await api.patch<CaseDetail>(`/cases/${caseId}`, update);
  return response.data;
}

export async function addCaseNote(caseId: string | number, note: string) {
  const response = await api.post<CaseDetail>(`/cases/${caseId}/notes`, { note });
  return response.data;
}

export function getFraudSocketUrl() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${window.location.host}/ws/fraud`;
}
