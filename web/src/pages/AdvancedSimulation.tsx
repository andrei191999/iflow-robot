import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { api } from "../lib/api";
import type {
  SimulationDuration,
  SimulationMode,
  AdvancedSimulationOptions,
  AdvancedSimulationResponse,
  JitterConfig,
} from "../types/simulation";
import type { ScheduleSpec, WeekConfig } from "../types/schedule";
import { PlayCircleIcon, FlaskConicalIcon, CheckCircle2Icon, XCircleIcon, MinusCircleIcon } from "lucide-react";
import WeekGrid from "./schedules/WeekGrid";
import JitterFields from "./schedules/JitterFields";
import HolidaysFields from "./schedules/HolidaysFields";
import ScreenshotGallery from "../components/ScreenshotGallery";

const DAY_DEFAULTS = {
  enabled: true,
  checkIn: "09:00",
  checkOut: "17:00",
  location: "telemunca",
} as const;

const defaultWeek: WeekConfig = {
  Mon: { ...DAY_DEFAULTS },
  Tue: { ...DAY_DEFAULTS },
  Wed: { ...DAY_DEFAULTS },
  Thu: { ...DAY_DEFAULTS },
  Fri: { ...DAY_DEFAULTS },
  Sat: { enabled: false },
  Sun: { enabled: false },
};

const defaultSpec: ScheduleSpec = {
  tz: "Europe/Bucharest",
  week: defaultWeek,
  jitter: { minutesMinus: 0, minutesPlus: 0 }, // Legacy jitter, ignored in advanced sim
  holidays: { publicCalendars: ["RO"], personalDates: [], behavior: "skip" },
  exceptions: { include: [], exclude: [], hourWindows: [] },
};

const defaultJitterConfig: JitterConfig = {
  execution: false,
  executionRange: 15,
  time: false,
  timeRange: 5,
};

export default function AdvancedSimulation() {
  const location = useLocation();
  const [duration, setDuration] = useState<SimulationDuration>("1-week");
  const [mode, setMode] = useState<SimulationMode>("backend");
  const [spec, setSpec] = useState<ScheduleSpec>(defaultSpec);
  const [jitterConfig, setJitterConfig] = useState<JitterConfig>(defaultJitterConfig);
  const [isRunning, setIsRunning] = useState(false);
  const [response, setResponse] = useState<AdvancedSimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedEvents, setExpandedEvents] = useState<Set<number>>(new Set());

  // Initialize from location state if passed from ScheduleForm
  useEffect(() => {
    if (location.state) {
      const { spec: passedSpec, duration: passedDuration } = location.state as {
        spec?: ScheduleSpec;
        duration?: SimulationDuration;
      };
      if (passedSpec) setSpec(passedSpec);
      if (passedDuration) setDuration(passedDuration);
    }
  }, [location.state]);

  const handleRun = async () => {
    setIsRunning(true);
    setError(null);
    setResponse(null);

    try {
      // Always use backend API - it handles visual mode, holidays, jitter, exceptions properly
      const options: AdvancedSimulationOptions = {
        duration,
        spec,
        mode,
        jitter: jitterConfig,
      };
      const result = await api.runAdvancedSimulation(options);
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setIsRunning(false);
    }
  };

  const toggleEventExpanded = (index: number) => {
    const newSet = new Set(expandedEvents);
    if (newSet.has(index)) {
      newSet.delete(index);
    } else {
      newSet.add(index);
    }
    setExpandedEvents(newSet);
  };

  const exportAsJSON = () => {
    if (!response) return;
    const dataStr = JSON.stringify(response, null, 2);
    const dataBlob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `simulation-${new Date().toISOString().replace(/:/g, '-')}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportAsCSV = () => {
    if (!response) return;
    const headers = ["Type", "Scheduled At", "Local Date", "Location", "Status"];
    const rows = response.events.map((event) => [
      event.type,
      event.scheduledAt,
      event.localDate,
      event.location,
      event.status,
    ]);
    const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
    const dataBlob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `simulation-${new Date().toISOString().replace(/:/g, '-')}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return <CheckCircle2Icon className="w-4 h-4 text-green-600" />;
      case "failure":
        return <XCircleIcon className="w-4 h-4 text-red-600" />;
      case "skipped":
        return <MinusCircleIcon className="w-4 h-4 text-gray-400" />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <FlaskConicalIcon className="w-8 h-8 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Advanced Simulation</h1>
          <p className="text-sm text-muted-foreground">
            Simulate your schedule over extended time periods
          </p>
        </div>
      </div>

      {/* Duration Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Duration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Select
              value={mode}
              onValueChange={(v) => setMode(v as SimulationMode)}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="backend">Backend (Fast)</SelectItem>
                <SelectItem value="screenshot">Screenshot</SelectItem>
                <SelectItem value="visual">Visual (3 Days)</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={duration}
              onValueChange={(v) => setDuration(v as SimulationDuration)}
            >
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1-week">1 Week</SelectItem>
                <SelectItem value="1-month">1 Month</SelectItem>
                <SelectItem value="3-months">3 Months</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={handleRun} disabled={isRunning} size="lg">
              <PlayCircleIcon className="w-5 h-5" />
              {isRunning ? "Running Simulation..." : "Simulate"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Schedule Configuration */}
      <Card className="p-4 space-y-4">
        <h2 className="text-lg font-semibold">Schedule Configuration</h2>

        <JitterFields
          value={jitterConfig}
          onChange={setJitterConfig}
        />

        <HolidaysFields
          value={spec.holidays}
          onChange={(h) => setSpec({ ...spec, holidays: h })}
        />

        <WeekGrid
          week={spec.week}
          onChange={(week) => setSpec({ ...spec, week })}
        />
      </Card>

      {/* Error */}
      {error && (
        <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Results */}
      {response && response.success && (
        <div className="space-y-4">
          {/* Summary Card */}
          <Card>
            <CardHeader>
              <CardTitle>Simulation Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div>
                  <div className="text-2xl font-bold">{response.summary.totalEvents}</div>
                  <div className="text-xs text-muted-foreground">Total Events</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-600">
                    {response.summary.successCount}
                  </div>
                  <div className="text-xs text-muted-foreground">Successful</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-red-600">
                    {response.summary.failureCount}
                  </div>
                  <div className="text-xs text-muted-foreground">Failed</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-gray-400">
                    {response.summary.holidaysSkipped}
                  </div>
                  <div className="text-xs text-muted-foreground">Holidays Skipped</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-600">
                    {response.summary.successCount > 0
                      ? Math.round((response.summary.successCount / response.summary.totalEvents) * 100)
                      : 0}%
                  </div>
                  <div className="text-xs text-muted-foreground">Success Rate</div>
                </div>
              </div>
              <div className="mt-4 text-sm text-muted-foreground">
                Period: {new Date(response.summary.dateRange.start).toLocaleDateString()} -{" "}
                {new Date(response.summary.dateRange.end).toLocaleDateString()}
              </div>
              <div className="mt-4 flex gap-2">
                <Button variant="outline" size="sm" onClick={exportAsJSON}>
                  Export JSON
                </Button>
                <Button variant="outline" size="sm" onClick={exportAsCSV}>
                  Export CSV
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Timeline View */}
          <Card>
            <CardHeader>
              <CardTitle>Event Timeline ({response.events.length} events)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {response.events.slice(0, 50).map((event, idx) => (
                  <div
                    key={idx}
                    className="border rounded-lg p-3 hover:bg-gray-50 cursor-pointer"
                    onClick={() => toggleEventExpanded(idx)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {getStatusIcon(event.status)}
                        <div>
                          <div className="font-medium">
                            {event.type === "checkIn" ? "Check-In" : "Check-Out"} at {event.time} from {event.location} - {event.localDate}
                          </div>
                          {event.reason && (
                            <div className="text-xs text-muted-foreground mt-1 whitespace-pre-wrap">
                              {event.reason}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="text-sm">
                        <span
                          className={
                            event.status === "success"
                              ? "text-green-600"
                              : event.status === "failure"
                              ? "text-red-600"
                              : "text-gray-400"
                          }
                        >
                          {event.status}
                        </span>
                      </div>
                    </div>

                    {/* Expanded Details */}
                    {expandedEvents.has(idx) && (
                      <div
                        className="mt-3 pt-3 border-t space-y-3 cursor-default"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {event.result && (
                          <div className="text-sm">
                            Duration: {(event.result.duration / 1000).toFixed(2)}s | Steps:{" "}
                            {event.result.stepCount}
                          </div>
                        )}

                        {/* Screenshots direct from event */}
                        {event.screenshots && event.screenshots.length > 0 && (
                          <div>
                            <div className="text-sm font-medium mb-2">Screenshots:</div>
                            <ScreenshotGallery
                              screenshots={event.screenshots.map((url, sIdx) => ({
                                url,
                                step: `Screenshot ${sIdx + 1}`,
                                timestamp: event.localDate
                              }))}
                            />
                          </div>
                        )}

                        {/* Fallback to result screenshots if any (legacy) */}
                        {!event.screenshots && event.result?.screenshots && event.result.screenshots.length > 0 && (
                          <div>
                            <div className="text-sm font-medium mb-2">Screenshots:</div>
                            <ScreenshotGallery screenshots={event.result.screenshots.slice(0, 3)} />
                          </div>
                        )}

                        {/* Error info */}
                        {event.result?.error && (
                          <div className="rounded-md bg-red-50 p-2 text-sm text-red-700">
                            {event.result.error}
                          </div>
                        )}

                        {/* Show raw info if no specific result but we have screenshots/logs */}
                        {!event.result && !event.screenshots && (
                             <div className="text-xs text-muted-foreground">No detailed logs available for this event.</div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
                {response.events.length > 50 && (
                  <div className="text-sm text-muted-foreground text-center py-2">
                    Showing first 50 of {response.events.length} events. Export to see all.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Sample Screenshots */}
          {response.sample_screenshots && response.sample_screenshots.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Sample Screenshots</CardTitle>
              </CardHeader>
              <CardContent>
                <ScreenshotGallery
                  screenshots={response.sample_screenshots.map((url, idx) => ({
                    url,
                    step: `Screenshot ${idx + 1}`,
                    timestamp: new Date().toISOString()
                  }))}
                />
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Help Card */}
      {!response && !error && !isRunning && (
        <Card className="border-dashed">
          <CardContent className="p-6 text-center text-muted-foreground">
            <FlaskConicalIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">
              Configure your schedule and select a duration to simulate how it would
              perform over time.
            </p>
            <p className="text-xs mt-2">
              This will compute all scheduled events and show you a detailed timeline
              with success rates and holidays.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
