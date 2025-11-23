import { Card } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
import type { JitterConfig } from "../../types/simulation";

export default function JitterFields({
  value,
  onChange,
}: {
  value: JitterConfig;
  onChange: (j: JitterConfig) => void;
}) {
  // Ensure value has defaults if undefined (though parent should provide it)
  const safeValue = value || {
    execution: false,
    executionRange: 15,
    time: false,
    timeRange: 5,
  };

  return (
    <Card className="p-4">
      <h3 className="mb-3 text-base font-semibold">Jitter Configuration</h3>
      <div className="grid gap-6 md:grid-cols-2">
        {/* Execution Jitter */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label htmlFor="execution-jitter" className="font-medium">
              Execution Jitter
            </Label>
            <Switch
              id="execution-jitter"
              checked={safeValue.execution}
              onCheckedChange={(checked) =>
                onChange({ ...safeValue, execution: checked })
              }
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Randomize when the script runs (e.g. +/- 15 mins)
          </p>
          {safeValue.execution && (
            <div className="flex items-center gap-2">
              <Label className="whitespace-nowrap">Range (+/- min):</Label>
              <Input
                type="number"
                className="w-24"
                value={safeValue.executionRange}
                onChange={(e) =>
                  onChange({
                    ...safeValue,
                    executionRange: Number(e.target.value),
                  })
                }
              />
            </div>
          )}
        </div>

        {/* Time Jitter */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label htmlFor="time-jitter" className="font-medium">
              Time Jitter
            </Label>
            <Switch
              id="time-jitter"
              checked={safeValue.time}
              onCheckedChange={(checked) =>
                onChange({ ...safeValue, time: checked })
              }
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Randomize the time entered in the form (e.g. +/- 5 mins)
          </p>
          {safeValue.time && (
            <div className="flex items-center gap-2">
              <Label className="whitespace-nowrap">Range (+/- min):</Label>
              <Input
                type="number"
                className="w-24"
                value={safeValue.timeRange}
                onChange={(e) =>
                  onChange({
                    ...safeValue,
                    timeRange: Number(e.target.value),
                  })
                }
              />
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
