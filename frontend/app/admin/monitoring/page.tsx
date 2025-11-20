"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { Activity, Cpu, Database, Zap, Server, HardDrive } from "lucide-react";

export default function MonitoringPage() {
  const { data: health } = useQuery({
    queryKey: ["system-health"],
    queryFn: () => api.getSystemHealth(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: gpuMetrics, isLoading: gpuLoading } = useQuery({
    queryKey: ["gpu-metrics"],
    queryFn: () => api.getGPUMetrics(),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  const systemStats = [
    {
      name: "API Status",
      value: health?.status || "Unknown",
      status: health?.status === "healthy" ? "good" : "bad",
      icon: Activity,
      color: health?.status === "healthy" ? "text-green-600" : "text-red-600",
      bgColor: health?.status === "healthy" ? "bg-green-50" : "bg-red-50",
    },
    {
      name: "Database",
      value: health?.database_status || "Unknown",
      status: health?.database_status === "connected" ? "good" : "bad",
      icon: Database,
      color: health?.database_status === "connected" ? "text-green-600" : "text-red-600",
      bgColor: health?.database_status === "connected" ? "bg-green-50" : "bg-red-50",
    },
    {
      name: "Redis Cache",
      value: health?.redis_status || "Unknown",
      status: health?.redis_status === "connected" ? "good" : "bad",
      icon: Zap,
      color: health?.redis_status === "connected" ? "text-green-600" : "text-red-600",
      bgColor: health?.redis_status === "connected" ? "bg-green-50" : "bg-red-50",
    },
    {
      name: "Queue Status",
      value: health?.queue_status || "Unknown",
      status: health?.queue_status === "operational" ? "good" : "bad",
      icon: Server,
      color: health?.queue_status === "operational" ? "text-green-600" : "text-red-600",
      bgColor: health?.queue_status === "operational" ? "bg-green-50" : "bg-red-50",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">System Monitoring</h1>
        <p className="text-gray-600 mt-2">
          Real-time platform health and performance metrics
        </p>
      </div>

      {/* System Health Status */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {systemStats.map((stat) => (
          <Card key={stat.name}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                  <p className="text-lg font-bold mt-2 capitalize">{stat.value}</p>
                </div>
                <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                  <stat.icon className={`w-6 h-6 ${stat.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* API Metrics */}
      <Card>
        <CardHeader>
          <CardTitle>API Performance</CardTitle>
          <CardDescription>Request metrics and response times</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">Requests/min</p>
              <p className="text-2xl font-bold mt-1">{health?.requests_per_minute || 0}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">Avg Response Time</p>
              <p className="text-2xl font-bold mt-1">{health?.avg_response_time?.toFixed(0) || 0}ms</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">Error Rate</p>
              <p className="text-2xl font-bold mt-1">{health?.error_rate?.toFixed(2) || 0}%</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">Active Connections</p>
              <p className="text-2xl font-bold mt-1">{health?.active_connections || 0}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* GPU Metrics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="w-5 h-5" />
            GPU Metrics
          </CardTitle>
          <CardDescription>VLA model inference hardware status</CardDescription>
        </CardHeader>
        <CardContent>
          {gpuLoading ? (
            <p className="text-center py-8 text-gray-600">Loading GPU metrics...</p>
          ) : gpuMetrics && gpuMetrics.gpus ? (
            <div className="space-y-6">
              {gpuMetrics.gpus.map((gpu: any, i: number) => (
                <div key={i} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold">GPU {i} - {gpu.name || "Unknown"}</h3>
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full ${
                        gpu.temperature < 80
                          ? "bg-green-100 text-green-800"
                          : gpu.temperature < 90
                          ? "bg-yellow-100 text-yellow-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {gpu.temperature}°C
                    </span>
                  </div>

                  <div className="grid gap-4 md:grid-cols-3">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-600">Utilization</span>
                        <span className="text-sm font-semibold">{gpu.utilization}%</span>
                      </div>
                      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            gpu.utilization > 90
                              ? "bg-red-500"
                              : gpu.utilization > 70
                              ? "bg-yellow-500"
                              : "bg-green-500"
                          }`}
                          style={{ width: `${gpu.utilization}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-600">Memory</span>
                        <span className="text-sm font-semibold">
                          {gpu.memory_used}GB / {gpu.memory_total}GB
                        </span>
                      </div>
                      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            (gpu.memory_used / gpu.memory_total) * 100 > 90
                              ? "bg-red-500"
                              : (gpu.memory_used / gpu.memory_total) * 100 > 70
                              ? "bg-yellow-500"
                              : "bg-blue-500"
                          }`}
                          style={{ width: `${(gpu.memory_used / gpu.memory_total) * 100}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-600">Power</span>
                        <span className="text-sm font-semibold">
                          {gpu.power_draw}W / {gpu.power_limit}W
                        </span>
                      </div>
                      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-purple-500"
                          style={{ width: `${(gpu.power_draw / gpu.power_limit) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center py-8 text-gray-600">No GPU metrics available</p>
          )}
        </CardContent>
      </Card>

      {/* Queue & Workers */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Inference Queue</CardTitle>
            <CardDescription>Request queue and processing status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm text-gray-600">Pending Requests</span>
                <span className="text-lg font-bold">{health?.queue_depth || 0}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm text-gray-600">Processing</span>
                <span className="text-lg font-bold">{health?.processing_count || 0}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm text-gray-600">Avg Wait Time</span>
                <span className="text-lg font-bold">{health?.avg_wait_time?.toFixed(1) || 0}s</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm text-gray-600">Throughput</span>
                <span className="text-lg font-bold">{health?.throughput || 0} req/min</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="w-5 h-5" />
              Resource Usage
            </CardTitle>
            <CardDescription>System resource consumption</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">CPU Usage</span>
                  <span className="text-sm font-semibold">{health?.cpu_usage || 0}%</span>
                </div>
                <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      (health?.cpu_usage || 0) > 80
                        ? "bg-red-500"
                        : (health?.cpu_usage || 0) > 60
                        ? "bg-yellow-500"
                        : "bg-green-500"
                    }`}
                    style={{ width: `${health?.cpu_usage || 0}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">Memory Usage</span>
                  <span className="text-sm font-semibold">{health?.memory_usage || 0}%</span>
                </div>
                <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      (health?.memory_usage || 0) > 80
                        ? "bg-red-500"
                        : (health?.memory_usage || 0) > 60
                        ? "bg-yellow-500"
                        : "bg-blue-500"
                    }`}
                    style={{ width: `${health?.memory_usage || 0}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">Disk Usage</span>
                  <span className="text-sm font-semibold">{health?.disk_usage || 0}%</span>
                </div>
                <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      (health?.disk_usage || 0) > 80
                        ? "bg-red-500"
                        : (health?.disk_usage || 0) > 60
                        ? "bg-yellow-500"
                        : "bg-purple-500"
                    }`}
                    style={{ width: `${health?.disk_usage || 0}%` }}
                  />
                </div>
              </div>

              <div className="pt-3 border-t">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Uptime</span>
                  <span className="text-sm font-semibold">{health?.uptime || "Unknown"}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Errors */}
      {health?.recent_errors && health.recent_errors.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Errors</CardTitle>
            <CardDescription>Latest error logs and exceptions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {health.recent_errors.map((error: any, i: number) => (
                <div key={i} className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-red-900">{error.message}</p>
                      <p className="text-xs text-red-700 mt-1">
                        {new Date(error.timestamp).toLocaleString()} • {error.endpoint || "Unknown"}
                      </p>
                    </div>
                    <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded">
                      {error.status_code}
                    </span>
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
