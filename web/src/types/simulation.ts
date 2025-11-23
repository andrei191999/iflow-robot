export type SimulationMode = "visual" | "screenshot" | "backend";
export type SimulationSpeed = "slow" | "normal" | "fast";
export type SimulationScenario = "checkIn" | "checkOut";
export type SimulationStatus = "idle" | "running" | "success" | "failed";
export type SimulationDuration = "1-week" | "1-month" | "3-months";

export interface SimulationOptions {
  mode: SimulationMode;
  speed: SimulationSpeed;
  scenario: SimulationScenario;
  location: "telemunca" | "birou";
  scheduleId?: string; // Optional: for testing specific schedule
}

// Public demo simulation options (both check-in and check-out)
export interface PublicSimulationOptions {
  mode: "visual"; // Always visual for public demo
  speed: SimulationSpeed;
  location: "telemunca" | "birou";
  checkInTime: string; // HH:mm format
  checkOutTime: string; // HH:mm format
}

// Advanced simulation options (authenticated users)
// Advanced simulation options (authenticated users)
export interface JitterConfig {
  execution: boolean;
  executionRange: number;
  time: boolean;
  timeRange: number;
}

export interface AdvancedSimulationOptions {
  duration: SimulationDuration;
  spec: unknown; // ScheduleSpec - keeping as unknown to avoid circular deps
  speed?: SimulationSpeed;
  mode?: SimulationMode;
  jitter?: JitterConfig;
}

export interface SimulationLogEntry {
  timestamp: string;
  level: "info" | "warn" | "error" | "success";
  message: string;
}

export interface SimulationScreenshot {
  step: string;
  url: string;
  timestamp: string;
}

export interface SimulationResult {
  status: SimulationStatus;
  duration: number; // milliseconds
  stepCount: number;
  logs: SimulationLogEntry[];
  screenshots: SimulationScreenshot[];
  error?: string;
}

export interface SimulationResponse {
  success: boolean;
  result?: SimulationResult;
  error?: string;
}

// Public demo simulation response (combines check-in and check-out)
export interface PublicSimulationResponse {
  success: boolean;
  checkIn?: SimulationResult;
  checkOut?: SimulationResult;
  error?: string;
}

// Advanced simulation response (multiple events over time period)
export interface AdvancedSimulationResponse {
  success: boolean;
  summary: {
    totalEvents: number;
    successCount: number;
    failureCount: number;
    holidaysSkipped: number;
    dateRange: {
      start: string;
      end: string;
    };
  };
  events: Array<{
    type: "checkIn" | "checkOut";
    scheduledAt: string;
    localDate: string;
    location: string;
    status: "success" | "failure" | "skipped";
    result?: SimulationResult;
  }>;
  error?: string;
}
