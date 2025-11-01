"use client";

import { useMemo } from "react";
import type { DashboardMetrics, TelemetrySample } from "../lib/api";

export interface DashboardProps {
  metrics: DashboardMetrics | null;
  history: TelemetrySample[];
  username: string;
  onLogout: () => void;
  onRefresh: () => void;
  loading?: boolean;
}

function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-zinc-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-zinc-900">{value}</p>
      {hint ? <p className="mt-1 text-xs text-zinc-400">{hint}</p> : null}
    </div>
  );
}

function formatTimestamp(timestamp?: string | null): string {
  if (!timestamp) return "--";
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return timestamp;
  return date.toLocaleString();
}

function formatUsage({
  percent,
  liters,
}: {
  percent: number;
  liters?: number;
}): string {
  const percentText = `${percent.toFixed(2)}%`;
  if (liters === undefined) return percentText;
  return `${percentText} (${liters.toFixed(2)} L)`;
}

function Sparkline({
  points,
  height = 80,
}: {
  points: Array<{ value: number }>;
  height?: number;
}) {
  const path = useMemo(() => {
    if (!points.length) return "";
    const max = Math.max(...points.map((entry) => entry.value));
    const min = Math.min(...points.map((entry) => entry.value));
    const span = max - min || 1;
    const width = Math.max(points.length - 1, 1);
    return points
      .map((entry, index) => {
        const x = (index / width) * 100;
        const y = 100 - ((entry.value - min) / span) * 100;
        return `${x},${y}`;
      })
      .join(" ");
  }, [points]);

  if (!path) {
    return (
      <div className="flex h-[80px] w-full items-center justify-center text-sm text-zinc-400">
        Insufficient data
      </div>
    );
  }

  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      className="h-[80px] w-full">
      <polyline
        fill="none"
        stroke="rgb(37, 99, 235)"
        strokeWidth="2"
        points={path}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Dashboard({
  metrics,
  history,
  username,
  onLogout,
  onRefresh,
  loading = false,
}: DashboardProps) {
  const latest = metrics?.latest ?? null;
  const waterTrend = useMemo(
    () =>
      (metrics?.water_levels ?? []).map((entry) => ({
        value: entry.water_level_percent,
        timestamp: entry.timestamp,
      })),
    [metrics?.water_levels]
  );

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-zinc-900">
            Water Tank Dashboard
          </h1>
          <p className="text-sm text-zinc-500">Signed in as {username}</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={onRefresh}
            className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition hover:bg-blue-100"
            disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
          <button
            onClick={onLogout}
            className="rounded-lg border border-zinc-200 px-4 py-2 text-sm font-medium text-zinc-600 transition hover:bg-zinc-100">
            Sign out
          </button>
        </div>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Water level"
          value={latest ? `${latest.water_level_percent.toFixed(1)}%` : "--"}
          hint={
            latest?.water_level_liters
              ? `${latest.water_level_liters.toFixed(1)} L`
              : undefined
          }
        />
        <StatCard
          label="Pump state"
          value={latest ? (latest.pump_state ? "ON" : "OFF") : "--"}
          hint={
            latest
              ? `Last update: ${formatTimestamp(latest.timestamp)}`
              : undefined
          }
        />
        <StatCard
          label="Usage (24h)"
          value={metrics ? formatUsage(metrics.usage.last_24h) : "--"}
        />
        <StatCard
          label="Usage (all time)"
          value={metrics ? formatUsage(metrics.usage.all_time) : "--"}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-[2fr,1fr]">
        <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-zinc-900">
              Water level trend
            </h2>
            <span className="text-xs text-zinc-400">
              Last {waterTrend.length} samples
            </span>
          </div>
          <Sparkline points={waterTrend} />
        </div>
        <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-zinc-900">
            Pump & leak summary
          </h2>
          <dl className="mt-4 space-y-2 text-sm text-zinc-600">
            <div className="flex justify-between">
              <dt>Pump ON samples</dt>
              <dd className="font-medium text-zinc-900">
                {metrics?.pump_state_summary.on ?? 0}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt>Pump OFF samples</dt>
              <dd className="font-medium text-zinc-900">
                {metrics?.pump_state_summary.off ?? 0}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt>Leak events</dt>
              <dd className="font-medium text-zinc-900">
                {metrics?.leak_events ?? 0}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt>Total samples</dt>
              <dd className="font-medium text-zinc-900">
                {metrics?.sample_count ?? 0}
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-zinc-900">
            Usage per hour
          </h2>
          <ul className="mt-4 grid grid-cols-2 gap-2 text-sm text-zinc-600">
            {metrics?.usage?.per_hour?.length ? (
              metrics.usage.per_hour.map((entry) => (
                <li
                  key={entry.hour}
                  className="flex items-center justify-between rounded-lg bg-zinc-50 px-3 py-2">
                  <span>{entry.hour.toString().padStart(2, "0")}:00</span>
                  <span className="font-medium text-zinc-900">
                    {formatUsage(entry)}
                  </span>
                </li>
              ))
            ) : (
              <li>No data</li>
            )}
          </ul>
        </div>
        <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-zinc-900">Usage per day</h2>
          <ul className="mt-4 space-y-2 text-sm text-zinc-600">
            {metrics?.usage?.per_day?.length ? (
              metrics.usage.per_day.map((entry) => (
                <li
                  key={entry.date}
                  className="flex items-center justify-between rounded-lg bg-zinc-50 px-3 py-2">
                  <span>{entry.date}</span>
                  <span className="font-medium text-zinc-900">
                    {formatUsage(entry)}
                  </span>
                </li>
              ))
            ) : (
              <li>No data</li>
            )}
          </ul>
        </div>
      </section>

      <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-zinc-900">
            Recent telemetry
          </h2>
          <span className="text-xs text-zinc-400">
            Showing latest {history.length} samples
          </span>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full divide-y divide-zinc-200 text-sm">
            <thead className="bg-zinc-50 text-left text-xs font-semibold uppercase text-zinc-500">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Water level</th>
                <th className="px-4 py-3">Pump</th>
                <th className="px-4 py-3">Leak</th>
                <th className="px-4 py-3">Raw payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {history.length ? (
                history.map((sample) => (
                  <tr key={sample.timestamp} className="hover:bg-zinc-50">
                    <td className="px-4 py-2 text-zinc-600">
                      {formatTimestamp(sample.timestamp)}
                    </td>
                    <td className="px-4 py-2 font-medium text-zinc-900">
                      {sample.water_level_percent.toFixed(1)}%
                    </td>
                    <td className="px-4 py-2 text-zinc-600">
                      {sample.pump_state ? "ON" : "OFF"}
                    </td>
                    <td className="px-4 py-2 text-zinc-600">
                      {sample.leak_detected ? "Yes" : "No"}
                    </td>
                    <td className="px-4 py-2 text-zinc-600">
                      {sample.raw_payload || "-"}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    className="px-4 py-6 text-center text-zinc-500"
                    colSpan={5}>
                    No telemetry samples yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
