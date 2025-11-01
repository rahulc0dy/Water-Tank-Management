"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Dashboard from "../components/Dashboard";
import LoginCard from "../components/LoginCard";
import {
  ApiError,
  BasicCreds,
  DashboardMetrics,
  TelemetrySample,
  clearCredentials,
  fetchHistory,
  fetchMetrics,
  loadCredentials,
  login,
  persistCredentials,
} from "../lib/api";

const REFRESH_INTERVAL_MS = 10_000;

interface DashboardState {
  metrics: DashboardMetrics | null;
  history: TelemetrySample[];
}

const initialState: DashboardState = {
  metrics: null,
  history: [],
};

export default function Home() {
  const [creds, setCreds] = useState<BasicCreds | null>(null);
  const [state, setState] = useState<DashboardState>(initialState);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCreds(loadCredentials());
  }, []);

  const logout = useCallback(() => {
    clearCredentials();
    setCreds(null);
    setState(initialState);
    setError(null);
  }, []);

  const refresh = useCallback(
    async (currentCreds: BasicCreds | null, showSpinner = false) => {
      if (!currentCreds) return;
      setError(null);
      if (showSpinner) setLoading(true);
      try {
        const [metrics, history] = await Promise.all([
          fetchMetrics(currentCreds),
          fetchHistory(currentCreds, 50),
        ]);
        setState({ metrics, history });
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          logout();
          setError("Session expired. Please sign in again.");
          return;
        }
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Unable to refresh data");
        }
      } finally {
        if (showSpinner) setLoading(false);
      }
    },
    [logout]
  );

  useEffect(() => {
    if (!creds) return;
    refresh(creds, true);
    const timer = setInterval(() => {
      refresh(creds, false);
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [creds, refresh]);

  const handleLogin = useCallback(
    async (username: string, password: string) => {
      setLoading(true);
      setError(null);
      try {
        await login({ username, password });
        const nextCreds = { username, password };
        persistCredentials(nextCreds);
        setCreds(nextCreds);
        await refresh(nextCreds, false);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Login failed");
        }
      } finally {
        setLoading(false);
      }
    },
    [refresh]
  );

  const memoisedError = useMemo(() => error, [error]);

  if (!creds) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-100 px-4">
        <LoginCard
          onSubmit={handleLogin}
          loading={loading}
          error={memoisedError}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-100">
      {memoisedError ? (
        <div className="bg-amber-100 px-6 py-3 text-sm text-amber-800 shadow">
          {memoisedError}
        </div>
      ) : null}
      <Dashboard
        metrics={state.metrics}
        history={state.history}
        username={creds.username}
        onLogout={logout}
        onRefresh={() => refresh(creds, true)}
        loading={loading}
      />
    </div>
  );
}
