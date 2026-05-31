export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface FraudAlert {
  user_id: string;
  reason: string;
  timestamp: string;
  risk_score: string;
  risk_level: RiskLevel;
  recommended_action?: string | null;
  confidence?: number | null;
  signals_triggered?: number | null;
  behavioral_match?: boolean | null;
}

export interface AlertStats {
  total: number;
  low: number;
  medium: number;
  high: number;
  critical: number;
  avgScore: number;
}

export type UserRole = "Admin" | "Fraud Analyst" | "Investigator" | "Read-Only Auditor";

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  role: UserRole;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
}

export interface ScoreBreakdownItem {
  label: string;
  points: number;
  evidence: string;
}

export interface UserProfileEvent {
  event_type: string;
  device_type: string;
  ip: string;
  location?: string | null;
  network?: string | null;
  amount?: number | null;
  timestamp: string;
}

export interface UserRiskProfile {
  user_id: string;
  current_risk: number;
  risk_level: RiskLevel;
  risk_trend: "up" | "down" | "stable";
  known_devices: string[];
  new_devices: string[];
  known_locations: string[];
  current_location?: string | null;
  ip_history: string[];
  behavioral_profile: Record<string, string>;
  recent_events: UserProfileEvent[];
  previous_investigations: FraudAlert[];
  score_breakdown: ScoreBreakdownItem[];
}
