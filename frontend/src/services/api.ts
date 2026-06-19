import axios from "axios";
import type {
  AnalystPerformance,
  AnalyticsOverview,
  AuthResponse,
  AuthUser,
  BehaviorEvaluation,
  BehaviorSettings,
  CaseDetail,
  CaseSummary,
  CaseUpdate,
  ClientApiKey,
  FraudAlert,
  FraudHeatMapPoint,
  IntelligenceActivity,
  InviteToken,
  RiskDistributionPoint,
  TrendPoint,
  UserRiskProfile,
  UserRole
} from "../types";

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

export async function register(name: string, email: string, password: string, role: UserRole, inviteToken: string) {
  const response = await api.post<AuthResponse>("/auth/register", { name, email, password, role, invite_token: inviteToken });
  return response.data;
}

export async function createInvite(email: string, role: UserRole, expiresInHours: number) {
  const response = await api.post<InviteToken>("/auth/invites", { email, role, expires_in_hours: expiresInHours });
  return response.data;
}

export async function getInvites() {
  const response = await api.get<InviteToken[]>("/auth/invites");
  return response.data;
}

export async function createClientApiKey(name: string) {
  const response = await api.post<ClientApiKey>("/api-keys", { name });
  return response.data;
}

export async function getClientApiKeys() {
  const response = await api.get<ClientApiKey[]>("/api-keys");
  return response.data;
}

export async function revokeClientApiKey(keyId: number) {
  await api.delete(`/api-keys/${keyId}`);
}

export async function getBehaviorSettings() {
  const response = await api.get<BehaviorSettings>("/behavior/settings");
  return response.data;
}

export async function updateBehaviorSettings(settings: Partial<BehaviorSettings>) {
  const response = await api.patch<BehaviorSettings>("/behavior/settings", settings);
  return response.data;
}

export async function getBehaviorEvaluation() {
  const response = await api.get<BehaviorEvaluation>("/behavior/evaluation");
  return response.data;
}

export async function forgotPassword(email: string) {
  const response = await api.post<{ message: string; reset_token?: string | null; reset_url?: string | null }>("/auth/forgot-password", { email });
  return response.data;
}

export async function resetPassword(token: string, password: string) {
  const response = await api.post<{ message: string }>("/auth/reset-password", { token, password });
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

export async function updateDeviceTrust(userId: string, fingerprint: string, status: "TRUSTED" | "BLOCKED") {
  const response = await api.patch(
    `/customers/${encodeURIComponent(userId)}/devices/${encodeURIComponent(fingerprint)}`,
    { status }
  );
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

export async function getIntelligenceActivity(limit = 30) {
  const response = await api.get<IntelligenceActivity>("/intelligence/activity", { params: { limit } });
  return response.data;
}

export async function getAnalyticsOverview() {
  const response = await api.get<AnalyticsOverview>("/analytics/overview");
  return response.data;
}

export async function getAnalyticsTrends() {
  const response = await api.get<TrendPoint[]>("/analytics/trends");
  return response.data;
}

export async function getRiskDistribution() {
  const response = await api.get<RiskDistributionPoint[]>("/analytics/risk-distribution");
  return response.data;
}

export async function getAnalystPerformance() {
  const response = await api.get<AnalystPerformance[]>("/analytics/analyst-performance");
  return response.data;
}

export async function getFraudHeatMap() {
  const response = await api.get<FraudHeatMapPoint[]>("/analytics/heat-map");
  return response.data;
}

export async function downloadExport(path: string, filename: string) {
  const response = await api.get<Blob>(path, { responseType: "blob" });
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function getFraudSocketUrl() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${window.location.host}/ws/fraud`;
}
