"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { BarChart3, Key, Shield, TrendingUp } from "lucide-react";

export default function DashboardPage() {
  const { data: subscription } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => api.getSubscription(),
  });

  const { data: analytics } = useQuery({
    queryKey: ["usage-analytics", 7],
    queryFn: () => api.getUsageAnalytics(7),
  });

  const { data: safetyData } = useQuery({
    queryKey: ["safety-analytics", 7],
    queryFn: () => api.getSafetyAnalytics(7),
  });

  const { data: apiKeys } = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => api.getAPIKeys(),
  });

  const stats = [
    {
      name: "Total Requests (7d)",
      value: analytics?.total_requests?.toLocaleString() || "0",
      icon: BarChart3,
      color: "text-blue-600",
      bgColor: "bg-blue-50",
    },
    {
      name: "Success Rate",
      value: `${analytics?.success_rate?.toFixed(1) || 0}%`,
      icon: TrendingUp,
      color: "text-green-600",
      bgColor: "bg-green-50",
    },
    {
      name: "Safety Incidents",
      value: safetyData?.total_incidents?.toString() || "0",
      icon: Shield,
      color: "text-orange-600",
      bgColor: "bg-orange-50",
    },
    {
      name: "Active API Keys",
      value: apiKeys?.filter(k => k.is_active).length.toString() || "0",
      icon: Key,
      color: "text-purple-600",
      bgColor: "bg-purple-50",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-gray-600 mt-2">
          Welcome back! Here&apos;s what&apos;s happening with your VLA inference platform.
        </p>
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

      {/* Subscription Info */}
      <Card>
        <CardHeader>
          <CardTitle>Subscription</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <p className="text-sm text-gray-600">Current Tier</p>
              <p className="text-lg font-semibold capitalize mt-1">
                {subscription?.tier || "Free"}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Monthly Usage</p>
              <p className="text-lg font-semibold mt-1">
                {subscription?.monthly_usage?.toLocaleString() || 0}
                {subscription?.monthly_quota && (
                  <span className="text-sm text-gray-500">
                    {" "}
                    / {subscription.monthly_quota.toLocaleString()}
                  </span>
                )}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Status</p>
              <p className="text-lg font-semibold mt-1">
                {subscription?.status ? (
                  <span className="capitalize">{subscription.status}</span>
                ) : (
                  "Active"
                )}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Quick Links</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <a
              href="/dashboard/api-keys"
              className="block p-3 rounded-lg border hover:bg-gray-50 transition-colors"
            >
              <p className="font-medium">Manage API Keys</p>
              <p className="text-sm text-gray-600">Create and revoke API keys</p>
            </a>
            <a
              href="/dashboard/playground"
              className="block p-3 rounded-lg border hover:bg-gray-50 transition-colors"
            >
              <p className="font-medium">Try Playground</p>
              <p className="text-sm text-gray-600">Test VLA inference with images</p>
            </a>
            <a
              href="/dashboard/analytics"
              className="block p-3 rounded-lg border hover:bg-gray-50 transition-colors"
            >
              <p className="font-medium">View Analytics</p>
              <p className="text-sm text-gray-600">Detailed usage and performance metrics</p>
            </a>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            {analytics && analytics.data_points.length > 0 ? (
              <div className="space-y-3">
                {analytics.data_points.slice(0, 5).map((point, i) => (
                  <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div>
                      <p className="text-sm font-medium">
                        {new Date(point.timestamp).toLocaleDateString()}
                      </p>
                      <p className="text-xs text-gray-600">
                        {point.count} requests
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-green-600">
                        {((point.success_count / point.count) * 100).toFixed(1)}%
                      </p>
                      <p className="text-xs text-gray-600">success</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-600">No recent activity</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
