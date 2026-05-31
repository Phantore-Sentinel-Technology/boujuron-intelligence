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
