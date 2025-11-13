"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api-client";
import { UsageChart } from "@/components/charts/usage-chart";
import { SafetyChart } from "@/components/charts/safety-chart";
import { RobotChart } from "@/components/charts/robot-chart";
import { AlertTriangle, BarChart3, Shield, TrendingUp } from "lucide-react";

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<number>(7);

  const { data: usageData, isLoading: usageLoading } = useQuery({
    queryKey: ["usage-analytics", timeRange],
    queryFn: () => api.getUsageAnalytics(timeRange),
  });

  const { data: safetyData, isLoading: safetyLoading } = useQuery({
    queryKey: ["safety-analytics", timeRange],
    queryFn: () => api.getSafetyAnalytics(timeRange),
  });

  const { data: robotProfiles, isLoading: robotsLoading } = useQuery({
    queryKey: ["robot-profiles", timeRange],
    queryFn: () => api.getRobotProfiles(timeRange),
  });

  const { data: topInstructions } = useQuery({
    queryKey: ["top-instructions", timeRange],
    queryFn: () => api.getTopInstructions(timeRange, 10),
  });

  const stats = [
    {
      name: "Total Requests",
      value: usageData?.total_requests?.toLocaleString() || "0",
      icon: BarChart3,
      color: "text-blue-600",
      bgColor: "bg-blue-50",
    },
    {
      name: "Success Rate",
      value: `${usageData?.success_rate?.toFixed(1) || 0}%`,
      icon: TrendingUp,
      color: "text-green-600",
      bgColor: "bg-green-50",
    },
    {
      name: "Avg Latency",
      value: `${usageData?.avg_latency_ms?.toFixed(0) || 0}ms`,
      icon: BarChart3,
      color: "text-purple-600",
      bgColor: "bg-purple-50",
    },
    {
      name: "Safety Incidents",
      value: safetyData?.total_incidents?.toString() || "0",
      icon: Shield,
      color: safetyData && safetyData.critical_incidents > 0 ? "text-red-600" : "text-orange-600",
      bgColor: safetyData && safetyData.critical_incidents > 0 ? "bg-red-50" : "bg-orange-50",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analytics</h1>
          <p className="text-gray-600 mt-2">
            Detailed insights into your VLA inference usage and performance
          </p>
        </div>

        <Select value={timeRange.toString()} onValueChange={(v) => setTimeRange(Number(v))}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Select time range" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="90">Last 90 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.name}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                  <p className="text-2xl font-bold mt-2">{stat.value}</p>
                </div>
                <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                  <stat.icon className={`w-6 h-6 ${stat.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Usage Charts */}
      <Card>
        <CardHeader>
          <CardTitle>Usage Trends</CardTitle>
          <CardDescription>Request volume and latency over time</CardDescription>
        </CardHeader>
        <CardContent>
          {usageLoading ? (
            <p className="text-center py-8 text-gray-600">Loading usage data...</p>
          ) : usageData && usageData.data_points.length > 0 ? (
            <UsageChart data={usageData.data_points} />
          ) : (
            <p className="text-center py-8 text-gray-600">No usage data available</p>
          )}
        </CardContent>
      </Card>

      {/* Safety & Robot Charts */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Safety Analysis</CardTitle>
            <CardDescription>Safety incidents breakdown by type</CardDescription>
          </CardHeader>
          <CardContent>
            {safetyLoading ? (
              <p className="text-center py-8 text-gray-600">Loading safety data...</p>
            ) : safetyData && Object.keys(safetyData.incidents_by_type).length > 0 ? (
              <SafetyChart incidents_by_type={safetyData.incidents_by_type} />
            ) : (
              <div className="text-center py-8">
                <Shield className="w-12 h-12 text-green-500 mx-auto mb-2" />
                <p className="text-gray-600">No safety incidents in this period</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Robot Performance</CardTitle>
            <CardDescription>Inference distribution across robot types</CardDescription>
          </CardHeader>
          <CardContent>
            {robotsLoading ? (
              <p className="text-center py-8 text-gray-600">Loading robot data...</p>
            ) : robotProfiles && robotProfiles.length > 0 ? (
              <RobotChart profiles={robotProfiles} />
            ) : (
              <p className="text-center py-8 text-gray-600">No robot data available</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Top Instructions Table */}
      <Card>
        <CardHeader>
          <CardTitle>Top Instructions</CardTitle>
          <CardDescription>Most frequently used instructions in this period</CardDescription>
        </CardHeader>
        <CardContent>
          {topInstructions && topInstructions.instructions && topInstructions.instructions.length > 0 ? (
            <div className="space-y-3">
              {topInstructions.instructions.map((item: any, i: number) => (
                <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div className="flex-1">
                    <p className="text-sm font-medium truncate">{item.instruction}</p>
                    <p className="text-xs text-gray-500">
                      Success rate: {item.success_rate.toFixed(1)}%
                    </p>
                  </div>
                  <div className="text-right ml-4">
                    <p className="text-sm font-semibold">{item.count.toLocaleString()}</p>
                    <p className="text-xs text-gray-500">uses</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center py-8 text-gray-600">No instruction data available</p>
          )}
        </CardContent>
      </Card>

      {/* Recent Safety Incidents */}
      {safetyData && safetyData.recent_incidents && safetyData.recent_incidents.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Safety Incidents</CardTitle>
            <CardDescription>Latest safety violations detected</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {safetyData.recent_incidents.slice(0, 5).map((incident) => (
                <div key={incident.incident_id} className="flex items-start gap-3 p-3 border rounded-lg">
                  <AlertTriangle
                    className={`w-5 h-5 mt-0.5 ${
                      incident.severity === "critical"
                        ? "text-red-600"
                        : incident.severity === "high"
                        ? "text-orange-600"
                        : "text-yellow-600"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm font-medium">
                        {incident.violation_type.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                      </p>
                      <span
                        className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                          incident.severity === "critical"
                            ? "bg-red-100 text-red-800"
                            : incident.severity === "high"
                            ? "bg-orange-100 text-orange-800"
                            : "bg-yellow-100 text-yellow-800"
                        }`}
                      >
                        {incident.severity}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600">
                      {incident.robot_type} • {incident.environment_type} •{" "}
                      {new Date(incident.timestamp).toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Action: {incident.action_taken}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
