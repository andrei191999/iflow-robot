export interface Run {
  id: string;
  uid: string;
  scheduleId: string;
  eventType: "checkIn" | "checkOut";
  scheduledAt: string; // ISO
  status: "success" | "failure" | "skipped";
  message?: string;
  location?: "telemunca" | "birou";
}
