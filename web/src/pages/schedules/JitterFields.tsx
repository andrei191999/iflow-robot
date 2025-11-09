import { Card } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import type { Jitter } from "../../types/schedule";

export default function JitterFields({
  value,
  onChange,
}: {
  value: Jitter;
  onChange: (j: Jitter) => void;
}) {
  return (
    <Card className="p-4">
      <h3 className="mb-3 text-base font-semibold">Jitter</h3>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-1">
          <Label>− minutes</Label>
          <Input
            type="number"
            value={value.minutesMinus}
            onChange={(e) =>
              onChange({ ...value, minutesMinus: Number(e.target.value) })
            }
          />
        </div>
        <div className="space-y-1">
          <Label>+ minutes</Label>
          <Input
            type="number"
            value={value.minutesPlus}
            onChange={(e) =>
              onChange({ ...value, minutesPlus: Number(e.target.value) })
            }
          />
        </div>
      </div>
    </Card>
  );
}
