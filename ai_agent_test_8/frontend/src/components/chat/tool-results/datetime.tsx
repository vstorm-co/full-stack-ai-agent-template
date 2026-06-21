"use client";
import { Calendar, Clock } from "lucide-react";

export function DateTimeResult({ result }: { result: string }) {
  // Parse "Current date: YYYY-MM-DD, Current time: HH:MM:SS"
  const dateMatch = result.match(/Current date:\s*(\d{4}-\d{2}-\d{2})/);
  const timeMatch = result.match(/Current time:\s*(\d{2}:\d{2}:\d{2})/);

  return (
    <div className="flex items-center gap-4 py-2">
      {dateMatch && (
        <div className="flex items-center gap-2">
          <Calendar className="text-primary h-5 w-5" />
          <div>
            <p className="text-muted-foreground text-xs">Date</p>
            <p className="text-sm font-semibold">{dateMatch[1]}</p>
          </div>
        </div>
      )}
      {timeMatch && (
        <div className="flex items-center gap-2">
          <Clock className="text-primary h-5 w-5" />
          <div>
            <p className="text-muted-foreground text-xs">Time</p>
            <p className="text-sm font-semibold">{timeMatch[1]}</p>
          </div>
        </div>
      )}
      {!dateMatch && !timeMatch && <p className="text-sm">{result}</p>}
    </div>
  );
}
