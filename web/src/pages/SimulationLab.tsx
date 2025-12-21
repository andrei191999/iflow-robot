import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Label } from "../components/ui/label";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { api } from "../lib/api";
import type {
  PublicSimulationOptions,
  PublicSimulationResponse,
  SimulationResult,
} from "../types/simulation";
import type { Location } from "../types/schedule";
import { PlayCircleIcon, FlaskConicalIcon, InfoIcon } from "lucide-react";
import LogViewer from "../components/LogViewer";
import ScreenshotGallery from "../components/ScreenshotGallery";

export default function SimulationLab() {
  const [options, setOptions] = useState<PublicSimulationOptions>({
    mode: "visual",
    location: "telemunca",
    checkInTime: "09:00",
    checkOutTime: "17:00",
    speed: "fast",
  });
  const [isRunning, setIsRunning] = useState(false);
  const [response, setResponse] = useState<PublicSimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRun = () => {
    setIsRunning(true);
    setError(null);
    setResponse(null);

    try {
      // Construct URLs for the Visual Simulation (Client-Side)
      const baseApi = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

      const today = new Date();
      const dateStr = `${today.getDate().toString().padStart(2, '0')}/${(today.getMonth() + 1).toString().padStart(2, '0')}/${today.getFullYear()}`;

      // 2. The Check-Out Simulation URL (Step 2)
      // Points to /dashboard to reuse session (skip login)
      const checkOutParams = new URLSearchParams({
        auto_run: "true",
        event_type: "checkOut",
        checkin: options.checkInTime, // Needed as reference
        checkout: options.checkOutTime,
        location: options.location,
        speed: options.speed,
        date: dateStr
      });
      const checkOutUrl = `${baseApi}/mock-iflow/dashboard?${checkOutParams.toString()}`;

      // 1. The Check-In Simulation URL (Step 1)
      // Points to /login to start session
      const checkInParams = new URLSearchParams({
        auto_run: "true",
        username: "demo@example.com",
        password: "demo123",
        event_type: "checkIn",
        checkin: options.checkInTime,
        location: options.location,
        speed: options.speed,
        date: dateStr,
        next_url: checkOutUrl // Chain to Check-Out dashboard
      });
      const checkInUrl = `${baseApi}/mock-iflow/login?${checkInParams.toString()}`;

      // Launch the simulation
      window.open(checkInUrl, "_blank", "width=1280,height=800");

      setResponse({
          success: true,
          summary: "Visual simulation launched in a new tab.\n\nPlease follow the 'Step 1: Check-in' and 'Step 2: Check-out' actions in the new window.",
          duration_ms: 0
      } as any);

    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to launch simulation");
    } finally {
      setIsRunning(false);
    }
  };

  const renderResult = (result: SimulationResult, title: string) => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {result.status === "success" || result.success ? (
            <span className="text-green-600">{title} - Success</span>
          ) : (
            <span className="text-red-600">{title} - Failed</span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {result.summary && (
             <div className="text-sm font-medium whitespace-pre-wrap">{result.summary}</div>
        )}
        <div className="text-sm text-muted-foreground">
          Duration: {(result.duration / 1000).toFixed(2)}s | Steps: {result.stepCount}
        </div>
        {result.logs && result.logs.length > 0 && (
          <LogViewer logs={result.logs} />
        )}
        {result.error && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
            {result.error}
          </div>
        )}
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <FlaskConicalIcon className="w-8 h-8 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Public Demo</h1>
          <p className="text-sm text-muted-foreground">
            Try iFlow automation with a demo account
          </p>
        </div>
      </div>

      {/* Configuration Panel */}
      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

            {/* Check-in Time */}
            <div className="space-y-2">
              <Label>Check-in Time</Label>
              <Input
                type="time"
                value={options.checkInTime}
                onChange={(e) =>
                  setOptions({ ...options, checkInTime: e.target.value })
                }
              />
              <p className="text-xs text-muted-foreground">
                Time to perform check-in
              </p>
            </div>

            {/* Check-out Time */}
            <div className="space-y-2">
              <Label>Check-out Time</Label>
              <Input
                type="time"
                value={options.checkOutTime}
                onChange={(e) =>
                  setOptions({ ...options, checkOutTime: e.target.value })
                }
              />
              <p className="text-xs text-muted-foreground">
                Time to perform check-out
              </p>
            </div>

            {/* Location */}
            <div className="space-y-2">
              <Label>Location</Label>
              <Select
                value={options.location}
                onValueChange={(v) =>
                  setOptions({ ...options, location: v as Location })
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="telemunca">Telemunca</SelectItem>
                  <SelectItem value="birou">Birou</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Work location
              </p>
            </div>
          </div>

          <div className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-md">
            💡 This demo runs in <strong>visual mode</strong> - you'll see the browser automation in real-time with fast execution speed.
          </div>

          {/* Run Button */}
          <div className="flex justify-end pt-2">
            <Button onClick={handleRun} size="lg" disabled={isRunning}>
              <PlayCircleIcon className="w-5 h-5" />
              {isRunning ? "Running..." : "Run Simulation"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Results */}
      {response && (
        <div className="space-y-4">
          {response.checkIn && renderResult(response.checkIn, "Check-In")}
          {response.checkOut && renderResult(response.checkOut, "Check-Out")}
        </div>
      )}

      {/* Help Card */}
      {!response && !error && !isRunning && (
        <Card className="border-dashed">
          <CardContent className="p-6 text-center text-muted-foreground">
            <FlaskConicalIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">
              Configure check-in and check-out times above and click "Run Simulation"
              to see the automation in action.
            </p>
            <p className="text-xs mt-2">
              Both check-in and check-out will be executed sequentially.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
