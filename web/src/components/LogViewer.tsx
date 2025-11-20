import { useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import type { SimulationLogEntry } from "../types/simulation";
import { cn } from "@/lib/utils";

interface LogViewerProps {
  logs: SimulationLogEntry[];
  autoScroll?: boolean;
  maxHeight?: string;
}

export default function LogViewer({
  logs,
  autoScroll = true,
  maxHeight = "400px",
}: LogViewerProps) {
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, autoScroll]);

  const getLevelStyles = (level: SimulationLogEntry["level"]) => {
    switch (level) {
      case "error":
        return "border-red-500 bg-red-50 text-red-900";
      case "warn":
        return "border-yellow-500 bg-yellow-50 text-yellow-900";
      case "success":
        return "border-green-500 bg-green-50 text-green-900";
      default:
        return "border-gray-300 bg-gray-50 text-gray-900";
    }
  };

  const getLevelBadgeVariant = (
    level: SimulationLogEntry["level"]
  ): "default" | "destructive" | "secondary" | "outline" => {
    switch (level) {
      case "error":
        return "destructive";
      case "warn":
        return "outline";
      case "success":
        return "secondary";
      default:
        return "default";
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Execution Log</CardTitle>
      </CardHeader>
      <CardContent>
        <div
          className="space-y-2 overflow-y-auto pr-2"
          style={{ maxHeight }}
        >
          {logs.length === 0 ? (
            <div className="text-sm text-muted-foreground text-center py-8">
              No logs yet. Start a simulation to see execution details.
            </div>
          ) : (
            logs.map((log, idx) => (
              <div
                key={idx}
                className={cn(
                  "p-3 rounded-md border-l-4 text-sm",
                  getLevelStyles(log.level)
                )}
              >
                <div className="flex items-start gap-2">
                  <Badge
                    variant={getLevelBadgeVariant(log.level)}
                    className="shrink-0 mt-0.5"
                  >
                    {log.level.toUpperCase()}
                  </Badge>
                  <span className="text-xs text-gray-500 shrink-0 mt-0.5">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <p className="flex-1 leading-relaxed">{log.message}</p>
                </div>
              </div>
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </CardContent>
    </Card>
  );
}
