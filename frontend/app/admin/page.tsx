"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { Users, TrendingUp, Shield, DollarSign, Activity, AlertTriangle } from "lucide-react";

export default function AdminOverviewPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: () => api.getAdminStats(),
  });

  const overviewCards = [
    {
      name: "Total Customers",
      value: stats?.total_customers?.toLocaleString() || "0",
      icon: Users,
      color: "text-blue-600",
      bgColor: "bg-blue-50",
      description: `${stats?.active_customers || 0} active`,
    },
    {
      name: "Total Requests (30d)",
      value: stats?.total_requests?.toLocaleString() || "0",
      icon: Activity,
      color: "text-green-600",
      bgColor: "bg-green-50",
      description: `${stats?.success_rate?.toFixed(1) || 0}% success rate`,
    },
    {
      name: "MRR",
      value: `$${stats?.monthly_revenue?.toLocaleString() || 0}`,
      icon: DollarSign,
      color: "text-purple-600",
      bgColor: "bg-purple-50",
      description: `${stats?.paying_customers || 0} paying customers`,
    },
    {
      name: "Safety Incidents",
      value: stats?.total_incidents?.toLocaleString() || "0",
      icon: Shield,
      color: stats?.critical_incidents > 0 ? "text-red-600" : "text-orange-600",
      bgColor: stats?.critical_incidents > 0 ? "bg-red-50" : "bg-orange-50",
      description: `${stats?.critical_incidents || 0} critical`,
    },
  ];

  const tierDistribution = [
    { name: "Free", count: stats?.tier_distribution?.free || 0, color: "bg-gray-500" },
    { name: "Pro", count: stats?.tier_distribution?.pro || 0, color: "bg-blue-500" },
    { name: "Enterprise", count: stats?.tier_distribution?.enterprise || 0, color: "bg-purple-500" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Admin Overview</h1>
        <p className="text-gray-600 mt-2">
          System-wide statistics and platform health
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {overviewCards.map((card) => (
          <Card key={card.name}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{card.name}</p>
                  <p className="text-2xl font-bold mt-2">{card.value}</p>
                  <p className="text-xs text-gray-500 mt-1">{card.description}</p>
                </div>
                <div className={`p-3 rounded-lg ${card.bgColor}`}>
                  <card.icon className={`w-6 h-6 ${card.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tier Distribution & Recent Activity */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Tier Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Customer Tier Distribution</CardTitle>
            <CardDescription>Breakdown of customers by subscription tier</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {tierDistribution.map((tier) => (
                <div key={tier.name}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">{tier.name}</span>
                    <span className="text-sm text-gray-600">{tier.count} customers</span>
                  </div>
                  <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${tier.color}`}
                      style={{
                        width: `${
                          ((tier.count / (stats?.total_customers || 1)) * 100).toFixed(0)
                        }%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* System Health */}
        <Card>
          <CardHeader>
            <CardTitle>System Health</CardTitle>
            <CardDescription>Current platform status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Activity className="w-5 h-5 text-green-600" />
                  <div>
                    <p className="text-sm font-medium">API Status</p>
                    <p className="text-xs text-gray-600">All systems operational</p>
                  </div>
                </div>
                <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
                  Healthy
                </span>
              </div>

              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <TrendingUp className="w-5 h-5 text-gray-600" />
                  <div>
                    <p className="text-sm font-medium">Avg Response Time</p>
                    <p className="text-xs text-gray-600">Last 24 hours</p>
                  </div>
                </div>
                <span className="text-sm font-semibold">
                  {stats?.avg_latency_ms?.toFixed(0) || 0}ms
                </span>
              </div>

              {stats?.critical_incidents > 0 && (
                <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-600" />
                    <div>
                      <p className="text-sm font-medium">Critical Alerts</p>
                      <p className="text-xs text-gray-600">Requires attention</p>
                    </div>
                  </div>
                  <span className="px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded-full">
                    {stats.critical_incidents}
                  </span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Customers */}
      <Card>
        <CardHeader>
          <CardTitle>Top Customers by Usage</CardTitle>
          <CardDescription>Highest API usage in the last 30 days</CardDescription>
        </CardHeader>
        <CardContent>
          {stats?.top_customers && stats.top_customers.length > 0 ? (
            <div className="space-y-3">
              {stats.top_customers.slice(0, 10).map((customer: any, i: number) => (
                <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-600 text-sm font-medium">
                      {i + 1}
                    </div>
                    <div>
                      <p className="text-sm font-medium">{customer.company_name || customer.email}</p>
                      <p className="text-xs text-gray-500">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                            customer.tier === "enterprise"
                              ? "bg-purple-100 text-purple-800"
                              : customer.tier === "pro"
                              ? "bg-blue-100 text-blue-800"
                              : "bg-gray-100 text-gray-800"
                          }`}
                        >
                          {customer.tier}
                        </span>
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold">{customer.monthly_usage.toLocaleString()}</p>
                    <p className="text-xs text-gray-500">requests</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center py-8 text-gray-600">No customer data available</p>
          )}
        </CardContent>
      </Card>

      {/* Recent Safety Incidents */}
      {stats?.recent_incidents && stats.recent_incidents.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Safety Incidents</CardTitle>
            <CardDescription>Latest critical and high-severity incidents</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats.recent_incidents.slice(0, 5).map((incident: any) => (
                <div key={incident.incident_id} className="flex items-start gap-3 p-3 border rounded-lg">
                  <AlertTriangle
                    className={`w-5 h-5 mt-0.5 ${
                      incident.severity === "critical"
                        ? "text-red-600"
                        : "text-orange-600"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm font-medium">
                        {incident.violation_type.replace(/_/g, " ").replace(/\b\w/g, (l: string) => l.toUpperCase())}
                      </p>
                      <span
                        className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                          incident.severity === "critical"
                            ? "bg-red-100 text-red-800"
                            : "bg-orange-100 text-orange-800"
                        }`}
                      >
                        {incident.severity}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600">
                      Customer: {incident.customer_id} • {new Date(incident.timestamp).toLocaleString()}
                    </p>
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
