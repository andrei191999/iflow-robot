import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import Spinner from "../components/Spinner";
import type { ScheduleDoc } from "../types/schedule";

export default function SchedulesList() {
  const nav = useNavigate();
  const [items, setItems] = useState<ScheduleDoc[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const data = (await api.listSchedules()) as ScheduleDoc[];
      setItems(data);
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Failed to load schedules";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (loading)
    return (
      <div className="p-6">
        <Spinner />
      </div>
    );
  if (error) return <div className="p-6 text-red-600">{error}</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Schedules</h1>
        <Button onClick={() => nav("/schedules/new")}>New schedule</Button>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {items?.map((s) => {
          const enabledDays = Object.entries(s.spec.week)
            .filter(([, config]) => config.enabled)
            .map(([day]) => day);

          const jitterMinus = s.spec.jitter?.minutesMinus || 0;
          const jitterPlus = s.spec.jitter?.minutesPlus || 0;
          const hasJitter = jitterMinus > 0 || jitterPlus > 0;

          return (
            <Card key={s.id}>
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <div className="font-medium">{s.name}</div>
                    {!s.active && (
                      <Badge variant="secondary" className="text-xs">
                        Inactive
                      </Badge>
                    )}
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    {s.spec.tz} • {enabledDays.join(", ")}
                  </div>
                  {hasJitter && (
                    <div className="text-xs text-gray-400 mt-1">
                      Jitter: -{jitterMinus}m to +{jitterPlus}m
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Link className="text-sm text-brand-600" to={`/runs/${s.id}`}>
                    Runs
                  </Link>
                  <Link
                    className="text-sm text-brand-600"
                    to={`/schedules/${s.id}`}
                  >
                    Edit
                  </Link>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
