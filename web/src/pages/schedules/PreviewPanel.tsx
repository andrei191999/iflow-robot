import { Card } from "../../components/ui/card";
import type { PreviewResponse } from "../../types/schedule";

export default function PreviewPanel({
  preview,
}: {
  preview: PreviewResponse | null;
}) {
  if (!preview) return null;
  return (
    <Card className="p-4">
      <h3 className="mb-3 text-base font-semibold">Preview</h3>
      <ul className="space-y-1 text-sm">
        {preview.events.map((e, i) => (
          <li key={i} className="flex items-center justify-between">
            <span>{new Date(e.at).toLocaleString()}</span>
            <span className="text-muted-foreground">
              {e.type} • {e.localDate}
              {e.location ? ` • ${e.location}` : ""}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
