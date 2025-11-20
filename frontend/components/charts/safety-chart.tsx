"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface SafetyChartProps {
  incidents_by_type: Record<string, number>;
}

export function SafetyChart({ incidents_by_type }: SafetyChartProps) {
  const chartData = Object.entries(incidents_by_type).map(([type, count]) => ({
    type: type.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
    count,
  }));

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">Safety Incidents by Type</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
          <XAxis dataKey="type" className="text-xs" angle={-45} textAnchor="end" height={100} />
          <YAxis className="text-xs" />
          <Tooltip
            contentStyle={{
              backgroundColor: "white",
              border: "1px solid #e5e7eb",
              borderRadius: "0.5rem",
            }}
          />
          <Legend />
          <Bar
            dataKey="count"
            name="Incidents"
            fill="#3b82f6"
            radius={[8, 8, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
