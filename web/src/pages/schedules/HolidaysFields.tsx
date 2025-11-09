import { Card } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import type { Holidays } from "../../types/schedule";

export default function HolidaysFields({
  value,
  onChange,
}: {
  value: Holidays;
  onChange: (h: Holidays) => void;
}) {
  return (
    <Card className="p-4">
      <h3 className="mb-3 text-base font-semibold">Holidays</h3>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-1">
          <Label>Public calendars (comma separated)</Label>
          <Input
            placeholder="RO, ES"
            value={value.publicCalendars.join(", ")}
            onChange={(e) =>
              onChange({
                ...value,
                publicCalendars: e.target.value
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean),
              })
            }
          />
        </div>
        <div className="space-y-1">
          <Label>Behavior</Label>
          <Select
            value={value.behavior}
            onValueChange={(v) =>
              onChange({ ...value, behavior: v as Holidays["behavior"] })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="skip">Skip</SelectItem>
              <SelectItem value="move_to_next_workday">
                Move to next workday
              </SelectItem>
              <SelectItem value="run_anyway">Run anyway</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="mt-4 space-y-1">
        <Label>Personal dates (YYYY-MM-DD, comma separated)</Label>
        <Input
          placeholder="2025-12-24, 2025-12-31"
          value={value.personalDates.join(", ")}
          onChange={(e) =>
            onChange({
              ...value,
              personalDates: e.target.value
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean),
            })
          }
        />
      </div>
    </Card>
  );
}
