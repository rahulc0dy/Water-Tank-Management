"use client";

import { FormEvent, useState } from "react";

export type UserType = "user" | "admin";

const USER_TYPE_STORAGE_KEY = "water_tank_user_type";

export function saveUserType(userType: UserType): void {
  localStorage.setItem(USER_TYPE_STORAGE_KEY, userType);
}

export function loadUserType(): UserType {
  if (typeof window === "undefined") return "user";
  const stored = localStorage.getItem(USER_TYPE_STORAGE_KEY);
  if (stored === "admin" || stored === "user") return stored;
  return "user";
}

export interface LoginCardProps {
  onSubmit: (
    username: string,
    password: string,
    userType: UserType
  ) => Promise<void> | void;
  onRegister?: (
    username: string,
    password: string,
    userType: UserType
  ) => Promise<void> | void;
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
  const [userType, setUserType] = useState<UserType>("user");

  const isRegister = mode === "register";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!username || !password) {
      return;
    }
    saveUserType(userType);
    if (isRegister && onRegister) {
      await onRegister(username, password, userType);
    } else {
      await onSubmit(username, password, userType);
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
        <div className="space-y-2">
          <label className="block text-sm font-medium text-zinc-700">
            User Type
          </label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="userType"
                value="user"
                checked={userType === "user"}
                onChange={() => setUserType("user")}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-zinc-700">User</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="userType"
                value="admin"
                checked={userType === "admin"}
                onChange={() => setUserType("admin")}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-zinc-700">Admin</span>
            </label>
          </div>
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
