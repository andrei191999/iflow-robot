import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../../lib/api";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
import type {
  ScheduleDoc,
  ScheduleSpec,
  WeekConfig,
  PreviewResponse,
} from "../../types/schedule";
import WeekGrid from "./WeekGrid";
import JitterFields from "./JitterFields";
import HolidaysFields from "./HolidaysFields";
import PreviewPanel from "./PreviewPanel";

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
  jitter: { minutesMinus: 0, minutesPlus: 0 },
  holidays: { publicCalendars: ["RO"], personalDates: [], behavior: "skip" },
  exceptions: { include: [], exclude: [], hourWindows: [] },
};

export default function ScheduleForm() {
  const { id } = useParams();
  const isNew = id === "new";
  const nav = useNavigate();

  const [doc, setDoc] = useState<ScheduleDoc>({
    name: "",
    active: true,
    spec: defaultSpec,
  });
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);

  useEffect(() => {
    if (isNew) return;
    (async () => {
      try {
        const list = await api.listSchedules();
        const found = (list as ScheduleDoc[]).find((s) => s.id === id);
        if (!found) throw new Error("Schedule not found");
        setDoc(found);
      } catch (e) {
        const errorMessage = e instanceof Error ? e.message : "Failed to load schedule";
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    })();
  }, [id, isNew]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      if (isNew) {
        const created = (await api.createSchedule(doc)) as ScheduleDoc;
        nav(`/schedules/${created.id}`);
      } else {
        await api.updateSchedule(doc.id!, doc);
      }
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Failed to save schedule";
      setError(errorMessage);
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!doc.id) return;
    if (!confirm("Delete this schedule?")) return;
    try {
      await api.deleteSchedule(doc.id);
      nav("/schedules");
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Failed to delete schedule";
      setError(errorMessage);
    }
  }

  async function doPreview() {
    setError(null);
    try {
      const resp = await api.previewSchedule(doc.spec, 10);
      setPreview(resp as PreviewResponse);
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Failed to preview schedule";
      setError(errorMessage);
    }
  }

  if (loading) return <div className="p-6">Loading…</div>;

  return (
    <div className="space-y-4">
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <Card className="p-4 space-y-4">
        {/* Header row */}
        <div className="grid gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <Label>Name</Label>
            <Input
              value={doc.name}
              onChange={(e) => setDoc({ ...doc, name: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <Label>Time zone</Label>
            <Input
              value={doc.spec.tz}
              onChange={(e) =>
                setDoc({ ...doc, spec: { ...doc.spec, tz: e.target.value } })
              }
              placeholder="Europe/Bucharest"
            />
          </div>

          <div className="flex items-end gap-3">
            <div className="space-y-2">
              <Label>Active</Label>
              <div className="h-10 flex items-center">
                <Switch
                  checked={doc.active}
                  onCheckedChange={(v) => setDoc({ ...doc, active: v })}
                />
              </div>
            </div>
            <div className="ml-auto flex gap-2">
              <Button variant="secondary" onClick={doPreview}>
                Preview 10
              </Button>
              <Button onClick={save} disabled={saving}>
                {saving ? "Saving…" : "Save"}
              </Button>
              {!isNew && (
                <Button variant="destructive" onClick={remove}>
                  Delete
                </Button>
              )}
            </div>
          </div>
        </div>

        <JitterFields
          value={doc.spec.jitter}
          onChange={(j) => setDoc({ ...doc, spec: { ...doc.spec, jitter: j } })}
        />

        <HolidaysFields
          value={doc.spec.holidays}
          onChange={(h) =>
            setDoc({ ...doc, spec: { ...doc.spec, holidays: h } })
          }
        />

        <WeekGrid
          week={doc.spec.week}
          onChange={(week) => setDoc({ ...doc, spec: { ...doc.spec, week } })}
        />
      </Card>

      <PreviewPanel preview={preview} />
    </div>
  );
}
