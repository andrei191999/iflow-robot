export type Location = "telemunca" | "birou";

export interface DayConfig {
  enabled: boolean;
  checkIn?: string; // "HH:MM"
  checkOut?: string; // "HH:MM"
  location?: Location;
}

export interface WeekConfig {
  Mon: DayConfig;
  Tue: DayConfig;
  Wed: DayConfig;
  Thu: DayConfig;
  Fri: DayConfig;
  Sat: DayConfig;
  Sun: DayConfig;
}

export interface Jitter {
  minutesMinus: number;
  minutesPlus: number;
}

export interface Holidays {
  publicCalendars: string[]; // e.g. ["RO"]
  personalDates: string[]; // "YYYY-MM-DD"
  behavior: "skip" | "move_to_next_workday" | "run_anyway";
}

export interface HourWindow {
  day: string; // "Mon".."Sun" or "YYYY-MM-DD"
  start: string; // "HH:MM"
  end: string; // "HH:MM"
  action?: "exclude" | "include";
}

export interface ExceptionsCfg {
  include: string[]; // ISO dates or datetimes
  exclude: string[]; // ISO dates or datetimes
  hourWindows: HourWindow[];
}

export interface ScheduleSpec {
  tz: string; // e.g. "Europe/Bucharest"
  week: WeekConfig;
  jitter: Jitter;
  holidays: Holidays;
  exceptions: ExceptionsCfg;
}

export interface NextEvent {
  type: "checkIn" | "checkOut";
  at: string; // UTC ISO
  localDate: string; // "YYYY-MM-DD"
  location?: Location;
}

export interface ScheduleDoc {
  id?: string; // added client-side
  uid?: string;
  name: string;
  active: boolean;
  spec: ScheduleSpec;
  next_event?: NextEvent;
}

export interface PreviewEvent {
  type: "checkIn" | "checkOut";
  at: string; // UTC ISO
  localDate: string; // "YYYY-MM-DD"
  location?: Location;
}

export interface PreviewResponse {
  events: PreviewEvent[];
}
