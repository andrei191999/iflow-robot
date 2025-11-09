import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { Run } from "../types/run";
import { Card } from "../components/ui/card";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Badge } from "../components/ui/badge";

export default function Runs() {
  const { scheduleId } = useParams();
  const [items, setItems] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.listRuns(scheduleId!);
        setItems(data as Run[]);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [scheduleId]);

  if (loading) return <div className="p-6">Loading…</div>;
  if (error) return <div className="p-6 text-red-600">{error}</div>;

  function statusBadge(s: Run["status"]) {
    const map: Record<Run["status"], string> = {
      success: "bg-green-100 text-green-700",
      failure: "bg-red-100 text-red-700",
      skipped: "bg-gray-100 text-gray-700",
    };
    return (
      <span
        className={`inline-flex rounded-full px-2 py-0.5 text-xs ${map[s]}`}
      >
        {s}
      </span>
    );
  }

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Runs</h1>
      <Card className="p-4">
        <Table>
          <TableCaption>Last executions for this schedule.</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>Scheduled</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Message</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((r) => (
              <TableRow key={r.id}>
                <TableCell>
                  {new Date(r.scheduledAt).toLocaleString()}
                </TableCell>
                <TableCell>{r.eventType}</TableCell>
                <TableCell>{statusBadge(r.status)}</TableCell>
                <TableCell>{r.location ?? "-"}</TableCell>
                <TableCell
                  className="max-w-[420px] truncate"
                  title={r.message ?? ""}
                >
                  {r.message ?? "-"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
