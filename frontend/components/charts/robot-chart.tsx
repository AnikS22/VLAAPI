"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { RobotProfile } from "@/lib/api-client";

interface RobotChartProps {
  profiles: RobotProfile[];
}

const COLORS = ["#3b82f6", "#22c55e", "#eab308", "#8b5cf6", "#ef4444", "#06b6d4", "#f97316"];

export function RobotChart({ profiles }: RobotChartProps) {
  const chartData = profiles.map((profile) => ({
    name: profile.robot_type.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
    value: profile.total_inferences,
    successRate: profile.success_rate,
    avgLatency: profile.avg_latency_ms,
  }));

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">Inference Distribution by Robot Type</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: "white",
              border: "1px solid #e5e7eb",
              borderRadius: "0.5rem",
            }}
            formatter={(value: number, name: string, props: any) => {
              if (name === "value") {
                return [
                  <div key="tooltip" className="space-y-1">
                    <div>{value.toLocaleString()} inferences</div>
                    <div className="text-xs text-gray-600">
                      Success: {props.payload.successRate.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-600">
                      Avg Latency: {props.payload.avgLatency.toFixed(0)}ms
                    </div>
                  </div>,
                  props.payload.name,
                ];
              }
              return [value, name];
            }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
