import { getIdToken } from "./auth";
import type { UserSettings, TestCredentialsResponse } from "../types/settings";
import type {
  SimulationOptions,
  SimulationResponse,
  PublicSimulationOptions,
  PublicSimulationResponse,
  AdvancedSimulationOptions,
  AdvancedSimulationResponse
} from "../types/simulation";

const API_BASE = import.meta.env.VITE_API_BASE_URL as string;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getIdToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  // Handle 401 - token expired, try refreshing once
  if (res.status === 401) {
    const newToken = await getIdToken(true); // Force refresh
    if (newToken) {
      const retryHeaders: HeadersInit = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${newToken}`,
        ...options.headers,
      };
      const retryRes = await fetch(`${API_BASE}${path}`, { ...options, headers: retryHeaders });
      if (!retryRes.ok) {
        const text = await retryRes.text();
        throw new Error(`${retryRes.status} ${retryRes.statusText}: ${text}`);
      }
      return retryRes.json();
    }
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json();
}

export const api = {
  // Auth debug (optional, if ENABLE_DEBUG_LOGIN=1 is set on backend)
  me: () => request("/auth/me"),

  // Schedules
  listSchedules: () => request("/api/schedules"),
  createSchedule: (body: unknown) =>
    request("/api/schedules", { method: "POST", body: JSON.stringify(body) }),
  updateSchedule: (id: string, body: unknown) =>
    request(`/api/schedules/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteSchedule: (id: string) =>
    request(`/api/schedules/${id}`, { method: "DELETE" }),
  previewSchedule: (spec: unknown, count = 10) =>
    request("/api/schedules/preview", {
      method: "POST",
      body: JSON.stringify({ spec, count }),
    }),

  // Runs
  listRuns: (scheduleId: string) =>
    request(`/api/runs?scheduleId=${encodeURIComponent(scheduleId)}`),

  // Settings
  getSettings: () => request<UserSettings>("/api/settings"),
  updateSettings: (settings: UserSettings) =>
    request<UserSettings>("/api/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    }),
  testCredentials: () =>
    request<TestCredentialsResponse>("/api/settings/test-credentials", {
      method: "POST",
    }),
  deleteCredentials: () =>
    request<void>("/api/settings/credentials", {
      method: "DELETE",
    }),

  // Simulation
  runSimulation: (options: SimulationOptions) =>
    request<SimulationResponse>("/api/simulation/run", {
      method: "POST",
      body: JSON.stringify(options),
    }),

  // Public demo simulation (no auth required)
  runPublicSimulation: (options: PublicSimulationOptions) =>
    request<PublicSimulationResponse>("/api/simulation/run-public", {
      method: "POST",
      body: JSON.stringify(options),
    }),

  // Advanced simulation (auth required in production, dev endpoint in local)
  runAdvancedSimulation: (options: AdvancedSimulationOptions) => {
    // Use dev endpoint if running on localhost
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const endpoint = isLocal ? "/api/simulation/run-advanced-dev" : "/api/simulation/run-advanced";

    return request<AdvancedSimulationResponse>(endpoint, {
      method: "POST",
      body: JSON.stringify(options),
    });
  },
};
