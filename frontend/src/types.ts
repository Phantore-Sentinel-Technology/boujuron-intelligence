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
  behavior_anomalies: BehaviorAnomaly[];
  risk_timeline: RiskTimelinePoint[];
  recent_events: UserProfileEvent[];
  previous_investigations: FraudAlert[];
  score_breakdown: ScoreBreakdownItem[];
}

export interface RiskTimelinePoint {
  timestamp: string;
  score: number;
  level: RiskLevel;
  reason: string;
}

export interface BehaviorAnomaly {
  label: string;
  severity: RiskLevel | "INFO";
  detail: string;
}

export type CaseStatus = "NEW" | "ASSIGNED" | "INVESTIGATING" | "ESCALATED" | "RESOLVED" | "ARCHIVED";
export type CasePriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type AnalystFeedback = "TRUE_FRAUD" | "FALSE_POSITIVE" | "NEEDS_REVIEW";
export type CaseDecision = "ALLOW" | "VERIFY" | "BLOCK" | "FREEZE" | "ESCALATE";

export interface CaseSummary {
  id: number;
  case_number: string;
  user_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  status: CaseStatus;
  priority: CasePriority;
  assigned_to?: string | null;
  analyst_feedback?: AnalystFeedback | null;
  created_at: string;
  updated_at: string;
}

export interface CaseNote {
  id: number;
  author: string;
  note: string;
  created_at: string;
}

export interface CaseTimelineItem {
  id: number;
  event_type: string;
  description: string;
  actor: string;
  created_at: string;
}

export interface CaseDetail extends CaseSummary {
  reason: string;
  recommended_action?: string | null;
  decision?: CaseDecision | null;
  potential_loss?: number | null;
  actual_loss?: number | null;
  fraud_signals: string[];
  score_breakdown: ScoreBreakdownItem[];
  notes: CaseNote[];
  timeline: CaseTimelineItem[];
}

export interface CaseUpdate {
  assigned_to?: string | null;
  status?: CaseStatus;
  priority?: CasePriority;
  analyst_feedback?: AnalystFeedback | null;
  decision?: CaseDecision | null;
  potential_loss?: number | null;
  actual_loss?: number | null;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  severity: RiskLevel | "INFO";
  case_id?: number | null;
  user_id?: string | null;
  created_at: string;
  read: boolean;
}

export interface InvestigationFeedItem {
  id: string;
  event_type: string;
  description: string;
  actor: string;
  case_id?: number | null;
  case_number?: string | null;
  user_id?: string | null;
  risk_level?: RiskLevel | null;
  created_at: string;
}

export interface IntelligenceActivity {
  notifications: NotificationItem[];
  feed: InvestigationFeedItem[];
}

export interface AnalyticsOverview {
  total_events: number;
  fraud_alerts: number;
  confirmed_fraud_cases: number;
  fraud_prevention_rate: number;
  false_positive_rate: number;
  average_investigation_minutes: number;
  cases_resolved: number;
}

export interface TrendPoint {
  label: string;
  value: number;
}

export interface RiskDistributionPoint {
  level: RiskLevel;
  count: number;
}

export interface AnalystPerformance {
  analyst: string;
  assigned_cases: number;
  resolved_cases: number;
  confirmed_fraud: number;
  false_positives: number;
}

export interface FraudHeatMapPoint {
  location: string;
  alerts: number;
  average_risk: number;
  highest_risk: RiskLevel;
}
