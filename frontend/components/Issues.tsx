"use client";

import React, { useState, useEffect } from "react";

const LOCAL_STORAGE_KEY = "water_tank_issues";

export interface Issue {
  id: string;
  title: string;
  description: string;
  category: "leak" | "pump" | "sensor" | "other";
  timestamp: string;
  username: string;
  resolved: boolean;
}

function getIssues(): Issue[] {
  if (typeof window === "undefined") return [];
  const stored = localStorage.getItem(LOCAL_STORAGE_KEY);
  if (!stored) return [];
  try {
    return JSON.parse(stored) as Issue[];
  } catch {
    return [];
  }
}

function saveIssues(issues: Issue[]): void {
  localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(issues));
}

export interface ReportIssueBoxProps {
  username: string;
  onIssueReported?: () => void;
}

export const ReportIssueBox: React.FC<ReportIssueBoxProps> = ({
  username,
  onIssueReported,
}) => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<Issue["category"]>("other");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setSubmitting(true);

    const newIssue: Issue = {
      id: crypto.randomUUID(),
      title: title.trim(),
      description: description.trim(),
      category,
      timestamp: new Date().toISOString(),
      username,
      resolved: false,
    };

    const issues = getIssues();
    issues.unshift(newIssue);
    saveIssues(issues);

    setTitle("");
    setDescription("");
    setCategory("other");
    setSubmitting(false);
    setSuccess(true);

    setTimeout(() => setSuccess(false), 3000);
    onIssueReported?.();
  };

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-zinc-900 mb-4">Report Issue</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="issue-title"
            className="block text-sm font-medium text-zinc-700 mb-1">
            Title *
          </label>
          <input
            id="issue-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Brief description of the issue"
            className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 text-zinc-700 focus:ring-blue-500"
            required
          />
        </div>

        <div>
          <label
            htmlFor="issue-category"
            className="block text-sm font-medium text-zinc-700 mb-1">
            Category
          </label>
          <select
            id="issue-category"
            value={category}
            onChange={(e) => setCategory(e.target.value as Issue["category"])}
            className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500">
            <option value="leak">Leak Detected</option>
            <option value="pump">Pump Issue</option>
            <option value="sensor">Sensor Malfunction</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="issue-description"
            className="block text-sm font-medium text-zinc-700 mb-1">
            Description
          </label>
          <textarea
            id="issue-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Detailed description of the issue..."
            rows={4}
            className="w-full rounded-lg border border-zinc-300 text-zinc-700 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
          />
        </div>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={submitting || !title.trim()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed">
            {submitting ? "Submitting..." : "Submit Issue"}
          </button>
          {success && (
            <span className="text-sm text-green-600">
              Issue reported successfully!
            </span>
          )}
        </div>
      </form>
    </div>
  );
};

export interface ViewIssuesProps {
  refreshTrigger?: number;
}

export const ViewIssues: React.FC<ViewIssuesProps> = ({ refreshTrigger }) => {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [filter, setFilter] = useState<"all" | "resolved" | "unresolved">(
    "all"
  );

  useEffect(() => {
    // Initial load
    setIssues(getIssues());

    // Poll every second, only update if data changed
    const interval = setInterval(() => {
      const stored = getIssues();
      setIssues((prev) => {
        const prevJson = JSON.stringify(prev);
        const newJson = JSON.stringify(stored);
        if (prevJson !== newJson) {
          return stored;
        }
        return prev;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [refreshTrigger]);

  const toggleResolved = (id: string) => {
    const updated = issues.map((issue) =>
      issue.id === id ? { ...issue, resolved: !issue.resolved } : issue
    );
    setIssues(updated);
    saveIssues(updated);
  };

  const deleteIssue = (id: string) => {
    const updated = issues.filter((issue) => issue.id !== id);
    setIssues(updated);
    saveIssues(updated);
  };

  const filteredIssues = issues.filter((issue) => {
    if (filter === "resolved") return issue.resolved;
    if (filter === "unresolved") return !issue.resolved;
    return true;
  });

  const categoryColors: Record<Issue["category"], string> = {
    leak: "bg-red-100 text-red-700",
    pump: "bg-yellow-100 text-yellow-700",
    sensor: "bg-purple-100 text-purple-700",
    other: "bg-zinc-100 text-zinc-700",
  };

  const categoryLabels: Record<Issue["category"], string> = {
    leak: "Leak",
    pump: "Pump",
    sensor: "Sensor",
    other: "Other",
  };

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-zinc-900">Reported Issues</h2>
        <select
          value={filter}
          onChange={(e) =>
            setFilter(e.target.value as "all" | "resolved" | "unresolved")
          }
          className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none">
          <option value="all">All ({issues.length})</option>
          <option value="unresolved">
            Unresolved ({issues.filter((i) => !i.resolved).length})
          </option>
          <option value="resolved">
            Resolved ({issues.filter((i) => i.resolved).length})
          </option>
        </select>
      </div>

      {filteredIssues.length === 0 ? (
        <p className="text-sm text-zinc-500 text-center py-8">
          {filter === "all"
            ? "No issues reported yet."
            : `No ${filter} issues.`}
        </p>
      ) : (
        <div className="space-y-3 max-h-[500px] overflow-y-auto">
          {filteredIssues.map((issue) => (
            <div
              key={issue.id}
              className={`rounded-lg border p-4 transition-colors ${
                issue.resolved
                  ? "bg-zinc-50 border-zinc-200"
                  : "bg-white border-zinc-300"
              }`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3
                      className={`font-medium ${
                        issue.resolved
                          ? "text-zinc-500 line-through"
                          : "text-zinc-900"
                      }`}>
                      {issue.title}
                    </h3>
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        categoryColors[issue.category]
                      }`}>
                      {categoryLabels[issue.category]}
                    </span>
                  </div>
                  {issue.description && (
                    <p className="text-sm text-zinc-600 mt-1">
                      {issue.description}
                    </p>
                  )}
                  <p className="text-xs text-zinc-400 mt-2">
                    Reported by{" "}
                    <span className="font-medium">{issue.username}</span> on{" "}
                    {new Date(issue.timestamp).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleResolved(issue.id)}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                      issue.resolved
                        ? "bg-zinc-200 text-zinc-700 hover:bg-zinc-300"
                        : "bg-green-100 text-green-700 hover:bg-green-200"
                    }`}>
                    {issue.resolved ? "Reopen" : "Resolve"}
                  </button>
                  <button
                    onClick={() => deleteIssue(issue.id)}
                    className="rounded-lg bg-red-100 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-200 transition-colors">
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
