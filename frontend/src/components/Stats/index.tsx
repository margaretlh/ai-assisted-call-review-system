import { useEffect, useState } from "react";
import { api } from "../../api";
import type { Stats as StatsType } from "../../types";
import styles from "./Stats.module.css";

export default function Stats() {
  const [stats, setStats] = useState<StatsType | null>(null);

  useEffect(() => {
    // Errors are silently ignored here — stats are non-critical and
    // console.error could log sensitive API response data.
    api.getStats().then(setStats).catch(() => undefined);
  }, []);

  if (!stats) return <div className={styles.bar}>Loading stats…</div>;

  return (
    <div className={styles.bar}>
      <Stat label="Total Calls" value={stats.total} />
      <Stat label="Pending Review" value={stats.pending_review} highlight />
      <Stat label="Reviewed Today" value={stats.reviewed_today} />
      <Stat label="Not Analyzed" value={stats.not_analyzed} />
    </div>
  );
}

function Stat({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <div className={`${styles.stat} ${highlight && value > 0 ? styles.statHighlight : ""}`}>
      <span className={styles.statValue}>{value}</span>
      <span className={styles.statLabel}>{label}</span>
    </div>
  );
}
