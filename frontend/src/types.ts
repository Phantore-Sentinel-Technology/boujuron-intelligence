export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface FraudAlert {
  id?: number | null;
  case_id?: number | null;
  case_number?: string | null;
  case_status?: CaseStatus | null;
  analyst_feedback?: AnalystFeedback | null;
  closure_note?: string | null;
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

export interface Organization {
  id: number;
  name: string;
  slug: string;
  admin_invite_url?: string | null;
  created_at: string;
}

export interface InviteToken {
  id: number;
  token: string;
  invite_url: string;
  email: string;
  role: UserRole;
  expires_at: string;
  used_at?: string | null;
  created_by?: string | null;
  created_at: string;
}

export interface ClientApiKey {
  id: number;
  name: string;
  key_prefix: string;
  api_key?: string | null;
  active: boolean;
  request_count: number;
  last_used_at?: string | null;
  created_at: string;
}

export interface ApiUsage {
  total_requests: number;
  requests_this_month: number;
  blocked: number;
  challenged: number;
  allowed: number;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  period: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string;
}

export interface AlertDestination {
  id: number;
  name: string;
  channel: "SLACK" | "TEAMS" | "EMAIL" | "WEBHOOK";
  target: string;
  minimum_risk: RiskLevel;
  enabled: boolean;
  last_status?: string | null;
  last_sent_at?: string | null;
  created_at: string;
}

export interface ConsortiumSettings {
  enabled: boolean;
  share_devices: boolean;
  share_ips: boolean;
  share_emails: boolean;
  share_phones: boolean;
}

export interface EvidenceGraph {
  nodes: Array<{ id: string; type: string; label: string; risk: string; count: number }>;
  edges: Array<{ source: string; target: string; relationship: string; count: number }>;
  suspected_ring: boolean;
}

export interface BehaviorSettings {
  organization_id: number;
  organization_name: string;
  amount_spike_multiplier: number;
  minimum_amount_delta: number;
  new_device_points: number;
  new_location_points: number;
  unusual_hour_points: number;
  velocity_window_minutes: number;
  transaction_velocity_limit: number;
  login_velocity_limit: number;
  velocity_points: number;
  minimum_profile_events: number;
  adaptive_learning_enabled: boolean;
  trusted_learning_max_score: number;
}

export interface BehaviorEvaluation {
  labeled_decisions: number;
  confirmed_fraud: number;
  false_positives: number;
  needs_review: number;
  precision: number;
  false_positive_rate: number;
  profiles_learning: number;
  trusted_events_learned: number;
}

export type RuleField =
  | "amount"
  | "risk_score"
  | "risk_level"
  | "event_type"
  | "location"
  | "network"
  | "device_type"
  | "is_new_device"
  | "is_rooted"
  | "is_emulator"
  | "browser_tampering"
  | "sim_swap_detected"
  | "failed_login_count";

export interface RuleCondition {
  field: RuleField;
  operator: "EQ" | "NEQ" | "GT" | "GTE" | "LT" | "LTE" | "IN" | "CONTAINS";
  value: string | number | boolean | string[];
}

export interface DecisionRule {
  id: number;
  organization_id: number;
  name: string;
  conditions: RuleCondition[];
  action: "ALLOW" | "CHALLENGE" | "BLOCK";
  score_adjustment: number;
  priority: number;
  enabled: boolean;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RiskDecision {
  decision_id: number;
  transaction_id: string;
  user_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  action: "ALLOW" | "CHALLENGE" | "BLOCK" | "LOCK_ACCOUNT";
  recommendation: string;
  confidence: number;
  reasons: string[];
  signals: Array<{ category: string; label: string; points: number; evidence: string }>;
  behavioral_match: boolean;
  action_decision_id?: number | null;
  matched_rules: string[];
  device_intelligence?: {
    fingerprint: string;
    status: string;
    trust_score: number;
    is_new_device: boolean;
    integrity_flags: string[];
  } | null;
  account_takeover?: {
    detected: boolean;
    score: number;
    level: RiskLevel;
    recommendation: string;
    indicators: string[];
  } | null;
  created_at: string;
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
  device_inventory: DeviceProfile[];
  account_security?: AccountSecurity | null;
}

export interface DeviceProfile {
  fingerprint: string;
  label: string;
  status: "NEW" | "TRUSTED" | "SUSPICIOUS" | "BLOCKED";
  trust_score: number;
  first_seen_at: string;
  last_seen_at: string;
  event_count: number;
  last_ip?: string | null;
  last_location?: string | null;
  integrity_flags: string[];
}

export interface AccountSecurity {
  takeover_risk: number;
  takeover_level: RiskLevel;
  recommendation: string;
  recent_failed_logins: number;
  password_changed_at?: string | null;
  sim_changed_at?: string | null;
  last_successful_login_at?: string | null;
  last_login_location?: string | null;
  last_login_ip?: string | null;
  last_login_device?: string | null;
  indicators: string[];
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
