import { useState } from "react";
import { Card, CardContent } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import LogViewer from "./LogViewer";
import ScreenshotGallery from "./ScreenshotGallery";
import { api } from "@/lib/api";
import type {
  SimulationOptions,
  SimulationResult,
  SimulationStatus,
} from "../types/simulation";
import {
  CheckCircle2Icon,
  XCircleIcon,
  PlayCircleIcon,
  LoaderIcon,
} from "lucide-react";

interface SimulationRunnerProps {
  options: SimulationOptions;
  onComplete?: (result: SimulationResult) => void;
  onError?: (error: string) => void;
  autoRun?: boolean;
}

export default function SimulationRunner({
  options,
  onComplete,
  onError,
  autoRun = false,
}: SimulationRunnerProps) {
  const [status, setStatus] = useState<SimulationStatus>("idle");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    setStatus("running");
    setError(null);
    setResult(null);

    try {
      const response = await api.runSimulation(options);

      if (response.success && response.result) {
        setResult(response.result);
        setStatus(response.result.status);
        onComplete?.(response.result);
      } else {
        const errorMsg = response.error || "Simulation failed";
        setError(errorMsg);
        setStatus("failed");
        onError?.(errorMsg);
      }
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Failed to run simulation";
      setError(errorMsg);
      setStatus("failed");
      onError?.(errorMsg);
    }
  };

  // Auto-run on mount if enabled
  useState(() => {
    if (autoRun) {
      runSimulation();
    }
  });

  const getStatusBadge = () => {
    switch (status) {
      case "running":
        return (
          <Badge variant="outline" className="gap-1">
            <LoaderIcon className="w-3 h-3 animate-spin" />
            Running
          </Badge>
        );
      case "success":
        return (
          <Badge variant="secondary" className="gap-1">
            <CheckCircle2Icon className="w-3 h-3" />
            Success
          </Badge>
        );
      case "failed":
        return (
          <Badge variant="destructive" className="gap-1">
            <XCircleIcon className="w-3 h-3" />
            Failed
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="gap-1">
            Idle
          </Badge>
        );
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <div className="space-y-4">
      {/* Status Summary */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <h3 className="font-medium">Simulation Status</h3>
              {getStatusBadge()}
            </div>
            {status !== "running" && (
              <Button onClick={runSimulation} size="sm">
                <PlayCircleIcon className="w-4 h-4" />
                {status === "idle" ? "Run Simulation" : "Run Again"}
              </Button>
            )}
          </div>

          {result && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-md">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Duration</p>
                <p className="text-lg font-semibold">
                  {formatDuration(result.duration)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Steps</p>
                <p className="text-lg font-semibold">{result.stepCount}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Logs</p>
                <p className="text-lg font-semibold">{result.logs.length}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">
                  Screenshots
                </p>
                <p className="text-lg font-semibold">
                  {result.screenshots.length}
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {status === "running" && (
            <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
              <LoaderIcon className="w-4 h-4 animate-spin" />
              <span>
                Executing simulation in {options.mode} mode at {options.speed}{" "}
                speed...
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Logs */}
      {result && result.logs.length > 0 && (
        <LogViewer logs={result.logs} autoScroll={true} maxHeight="500px" />
      )}

      {/* Screenshots */}
      {result && result.screenshots.length > 0 && (
        <ScreenshotGallery
          screenshots={result.screenshots}
          mode={options.mode === "visual" ? "slideshow" : "grid"}
        />
      )}
    </div>
  );
}
