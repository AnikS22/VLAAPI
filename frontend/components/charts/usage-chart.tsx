"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { UsageDataPoint } from "@/lib/api-client";

interface UsageChartProps {
  data: UsageDataPoint[];
}

export function UsageChart({ data }: UsageChartProps) {
  const chartData = data.map((point) => ({
    date: new Date(point.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    requests: point.count,
    successful: point.success_count,
    failed: point.error_count,
    latency: point.avg_latency_ms || 0,
  }));

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold mb-2">Request Volume</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
            <XAxis dataKey="date" className="text-xs" />
            <YAxis className="text-xs" />
            <Tooltip
              contentStyle={{
                backgroundColor: "white",
                border: "1px solid #e5e7eb",
                borderRadius: "0.5rem",
              }}
            />
            <Legend />
            <Line type="monotone" dataKey="requests" stroke="#3b82f6" strokeWidth={2} name="Total Requests" />
            <Line type="monotone" dataKey="successful" stroke="#22c55e" strokeWidth={2} name="Successful" />
            <Line type="monotone" dataKey="failed" stroke="#ef4444" strokeWidth={2} name="Failed" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-2">Average Latency (ms)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
            <XAxis dataKey="date" className="text-xs" />
            <YAxis className="text-xs" />
            <Tooltip
              contentStyle={{
                backgroundColor: "white",
                border: "1px solid #e5e7eb",
                borderRadius: "0.5rem",
              }}
            />
            <Line type="monotone" dataKey="latency" stroke="#8b5cf6" strokeWidth={2} name="Latency" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
