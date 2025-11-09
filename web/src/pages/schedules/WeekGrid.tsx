import { Card } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
import type { WeekConfig, Location } from "../../types/schedule";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] as const;

export default function WeekGrid({
  week,
  onChange,
}: {
  week: WeekConfig;
  onChange: (w: WeekConfig) => void;
}) {
  function update(
    day: (typeof DAYS)[number],
    field: "enabled" | "checkIn" | "checkOut" | "location",
    value: boolean | string | Location
  ) {
    onChange({ ...week, [day]: { ...week[day], [field]: value } });
  }

  return (
    <Card className="p-4">
      <h3 className="mb-3 text-base font-semibold">Week</h3>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-7">
        {DAYS.map((day) => {
          const d = week[day];
          return (
            <div key={day} className="rounded-lg border p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="font-medium">{day}</span>
                <Switch
                  checked={!!d.enabled}
                  onCheckedChange={(v) => update(day, "enabled", v)}
                />
              </div>
              <div className="space-y-2">
                <div className="space-y-1">
                  <Label>Check-in</Label>
                  <Input
                    type="time"
                    value={d.checkIn ?? ""}
                    onChange={(e) => update(day, "checkIn", e.target.value)}
                    disabled={!d.enabled}
                  />
                </div>
                <div className="space-y-1">
                  <Label>Check-out</Label>
                  <Input
                    type="time"
                    value={d.checkOut ?? ""}
                    onChange={(e) => update(day, "checkOut", e.target.value)}
                    disabled={!d.enabled}
                  />
                </div>
                <div className="space-y-1">
                  <Label>Location</Label>
                  <Select
                    value={(d.location ?? "telemunca") as Location}
                    onValueChange={(val) =>
                      update(day, "location", val as Location)
                    }
                    disabled={!d.enabled}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="telemunca">telemunca</SelectItem>
                      <SelectItem value="birou">birou</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
