"use client";

import { FormEvent, useState } from "react";

export interface LoginCardProps {
  onSubmit: (username: string, password: string) => Promise<void> | void;
  onRegister?: (username: string, password: string) => Promise<void> | void;
  loading?: boolean;
  error?: string | null;
  info?: string | null;
}

export function LoginCard({
  onSubmit,
  onRegister,
  loading = false,
  error,
  info,
}: LoginCardProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");

  const isRegister = mode === "register";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!username || !password) {
      return;
    }
    if (isRegister && onRegister) {
      await onRegister(username, password);
    } else {
      await onSubmit(username, password);
    }
  }

  const passwordAutocomplete = isRegister ? "new-password" : "current-password";
  const primaryLabel = loading
    ? isRegister
      ? "Creating account..."
      : "Signing in..."
    : isRegister
    ? "Create account"
    : "Sign in";
  const toggleLabel = isRegister
    ? "Already have an account? Sign in"
    : "Need an account? Create one";

  function toggleMode() {
    setMode((prev) => (prev === "login" ? "register" : "login"));
  }

  return (
    <div className="w-full max-w-md rounded-xl border border-zinc-200 bg-white p-8 shadow-sm">
      <h1 className="mb-6 text-center text-2xl font-semibold text-zinc-900">
        Water Tank Dashboard
      </h1>
      <form className="space-y-5" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <label
            className="block text-sm font-medium text-zinc-700"
            htmlFor="username">
            Username
          </label>
          <input
            id="username"
            type="text"
            autoComplete="username"
            className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-zinc-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <label
            className="block text-sm font-medium text-zinc-700"
            htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete={passwordAutocomplete}
            className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-zinc-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        {error ? (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        ) : null}
        {info ? (
          <p className="text-sm text-green-600" role="status">
            {info}
          </p>
        ) : null}
        <button
          type="submit"
          className="flex w-full items-center justify-center rounded-lg bg-blue-600 px-3 py-2 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-400"
          disabled={loading}>
          {primaryLabel}
        </button>
      </form>
      <button
        type="button"
        onClick={toggleMode}
        className="mt-4 w-full text-sm font-medium text-blue-600 transition hover:text-blue-700">
        {toggleLabel}
      </button>
      <p className="mt-6 text-center text-xs text-zinc-500">
        Credentials are sent with HTTP Basic auth to your Raspberry Pi backend.
      </p>
    </div>
  );
}

export default LoginCard;
