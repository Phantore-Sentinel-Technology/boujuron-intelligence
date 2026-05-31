import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  hint: string;
  icon: LucideIcon;
  tone?: "default" | "good" | "warn" | "danger";
}

export function StatCard({ label, value, hint, icon: Icon, tone = "default" }: StatCardProps) {
  return (
    <section className={`stat-card ${tone}`}>
      <div className="stat-icon">
        <Icon size={18} />
      </div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        <span>{hint}</span>
      </div>
    </section>
  );
}
