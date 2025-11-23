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
    speed: "normal",
  });
  const [isRunning, setIsRunning] = useState(false);
  const [response, setResponse] = useState<PublicSimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setIsRunning(true);
    setError(null);
    setResponse(null);

    try {
      const result = await api.runPublicSimulation(options);
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setIsRunning(false);
    }
  };

  const renderResult = (result: SimulationResult, title: string) => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {result.status === "success" ? (
            <span className="text-green-600">{title} - Success</span>
          ) : (
            <span className="text-red-600">{title} - Failed</span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="text-sm text-muted-foreground">
          Duration: {(result.duration / 1000).toFixed(2)}s | Steps: {result.stepCount}
        </div>
        {result.logs && result.logs.length > 0 && (
          <LogViewer logs={result.logs} />
        )}
        {result.screenshots && result.screenshots.length > 0 && (
          <ScreenshotGallery screenshots={result.screenshots} />
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

      {/* Demo Banner */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="p-4 flex items-start gap-3">
          <InfoIcon className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-900">
            <p className="font-medium">Demo mode - using test account</p>
            <p className="text-blue-700 mt-1">
              This simulation runs both check-in and check-out automatically. Sign in to access
              advanced simulation features with your own schedule configuration.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Configuration Panel */}
      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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

            {/* Speed */}
            <div className="space-y-2">
              <Label>Speed</Label>
              <Select
                value={options.speed}
                onValueChange={(v) =>
                  setOptions({ ...options, speed: v as "slow" | "normal" | "fast" })
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="slow">Slow (2s delays)</SelectItem>
                  <SelectItem value="normal">Normal (0.5s)</SelectItem>
                  <SelectItem value="fast">Fast (no delays)</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Playback speed
              </p>
            </div>
          </div>

          <div className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-md">
            💡 This demo runs in <strong>visual mode</strong> - you'll see the browser automation in real-time with a red dot showing where it's clicking
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
      {response && response.success && (
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
