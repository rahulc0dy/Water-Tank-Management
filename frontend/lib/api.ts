export type BasicCreds = {
  username: string;
  password: string;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function encodeBase64(text: string): string {
  if (typeof window !== "undefined" && typeof window.btoa === "function") {
    return window.btoa(text);
  }
  return Buffer.from(text).toString("base64");
}

function basicAuthHeader(creds: BasicCreds): string {
  const token = encodeBase64(`${creds.username}:${creds.password}`);
  return `Basic ${token}`;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function handleJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail ?? detail;
    } catch (error) {
      // ignore
    }
    throw new ApiError(detail || "Request failed", response.status);
  }
  return response.json() as Promise<T>;
}

export async function login(
  creds: BasicCreds
): Promise<{ username: string; last_login: string | null }> {
  const response = await fetch(`${API_BASE}/users/login`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(creds),
  });
  return handleJson(response);
}

export async function register(
  creds: BasicCreds
): Promise<{ message: string; username: string }> {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(creds),
  });
  return handleJson(response);
}

export interface TelemetrySample {
  timestamp: string;
  water_level_percent: number;
  pump_state: number;
  leak_detected: boolean;
  raw_payload: string;
}

export async function fetchLatest(creds: BasicCreds): Promise<TelemetrySample> {
  const response = await fetch(`${API_BASE}/telemetry/latest`, {
    headers: {
      authorization: basicAuthHeader(creds),
    },
  });
  return handleJson(response);
}

export async function fetchHistory(
  creds: BasicCreds,
  limit = 50
): Promise<TelemetrySample[]> {
  const response = await fetch(`${API_BASE}/telemetry/history?limit=${limit}`, {
    headers: {
      authorization: basicAuthHeader(creds),
    },
  });
  return handleJson(response);
}

export interface DashboardUsageSlice {
  percent: number;
  liters?: number;
}

export interface DashboardMetrics {
  latest: {
    timestamp: string;
    water_level_percent: number;
    pump_state: number;
    leak_detected: boolean;
    water_level_liters?: number;
  } | null;
  sample_count: number;
  usage: {
    last_24h: DashboardUsageSlice;
    all_time: DashboardUsageSlice;
    per_hour: Array<{ hour: number } & DashboardUsageSlice>;
    per_day: Array<{ date: string } & DashboardUsageSlice>;
  };
  water_levels: Array<{
    timestamp: string;
    water_level_percent: number;
    water_level_liters?: number;
  }>;
  pump_state_summary: {
    on: number;
    off: number;
  };
  leak_events: number;
}

export async function fetchMetrics(
  creds: BasicCreds
): Promise<DashboardMetrics> {
  const response = await fetch(`${API_BASE}/dashboard/metrics`, {
    headers: {
      authorization: basicAuthHeader(creds),
    },
  });
  return handleJson(response);
}

export function persistCredentials(creds: BasicCreds): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("water-tank-creds", JSON.stringify(creds));
}

export function clearCredentials(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("water-tank-creds");
}

export function loadCredentials(): BasicCreds | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("water-tank-creds");
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as BasicCreds;
    if (!parsed.username || !parsed.password) return null;
    return parsed;
  } catch (error) {
    return null;
  }
}
