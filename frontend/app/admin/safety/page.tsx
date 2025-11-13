"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { AlertTriangle, Shield, ChevronLeft, ChevronRight } from "lucide-react";

export default function SafetyPage() {
  const [page, setPage] = useState(1);
  const [severityFilter, setSeverityFilter] = useState("");
  const [selectedIncident, setSelectedIncident] = useState<any>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-safety-incidents", page, severityFilter],
    queryFn: () => api.getAllSafetyIncidents(page, 50, severityFilter),
  });

  const stats = [
    {
      name: "Total Incidents",
      value: data?.total_count?.toLocaleString() || "0",
      color: "text-orange-600",
      bgColor: "bg-orange-50",
    },
    {
      name: "Critical",
      value: data?.critical_count?.toLocaleString() || "0",
      color: "text-red-600",
      bgColor: "bg-red-50",
    },
    {
      name: "High Severity",
      value: data?.high_count?.toLocaleString() || "0",
      color: "text-orange-600",
      bgColor: "bg-orange-50",
    },
    {
      name: "Medium/Low",
      value: ((data?.total_count || 0) - (data?.critical_count || 0) - (data?.high_count || 0)).toLocaleString(),
      color: "text-yellow-600",
      bgColor: "bg-yellow-50",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Safety Incident Review</h1>
        <p className="text-gray-600 mt-2">
          Monitor and review safety violations across all customers
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-6 md:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.name}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                  <p className="text-2xl font-bold mt-2">{stat.value}</p>
                </div>
                <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                  <Shield className={`w-6 h-6 ${stat.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filter Incidents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="w-48">
              <Select value={severityFilter} onValueChange={(value) => {
                setSeverityFilter(value);
                setPage(1);
              }}>
                <SelectTrigger>
                  <SelectValue placeholder="All Severities" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Severities</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Incidents Table */}
      <Card>
        <CardHeader>
          <CardTitle>Safety Incidents</CardTitle>
          <CardDescription>
            {data?.total_count || 0} total incidents
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-center py-8 text-gray-600">Loading incidents...</p>
          ) : data && data.incidents && data.incidents.length > 0 ? (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Robot</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead>Action Taken</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.incidents.map((incident: any) => (
                    <TableRow key={incident.incident_id}>
                      <TableCell className="font-mono text-xs">
                        {new Date(incident.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            incident.severity === "critical"
                              ? "bg-red-100 text-red-800"
                              : incident.severity === "high"
                              ? "bg-orange-100 text-orange-800"
                              : incident.severity === "medium"
                              ? "bg-yellow-100 text-yellow-800"
                              : "bg-blue-100 text-blue-800"
                          }`}
                        >
                          {incident.severity}
                        </span>
                      </TableCell>
                      <TableCell className="max-w-xs truncate">
                        {incident.violation_type.replace(/_/g, " ").replace(/\b\w/g, (l: string) => l.toUpperCase())}
                      </TableCell>
                      <TableCell>{incident.robot_type}</TableCell>
                      <TableCell className="font-mono text-xs">{incident.customer_id.slice(0, 8)}...</TableCell>
                      <TableCell className="max-w-xs truncate">{incident.action_taken}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedIncident(incident)}
                        >
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {data && data.total_pages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-gray-600">
                    Page {page} of {data.total_pages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="w-4 h-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={page >= data.total_pages}
                    >
                      Next
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <Shield className="w-12 h-12 text-green-500 mx-auto mb-4" />
              <p className="text-gray-600">No safety incidents found</p>
              <p className="text-sm text-gray-500 mt-1">
                All systems operating safely within parameters
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Incident Pattern Analysis */}
      {data?.incident_patterns && data.incident_patterns.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Incident Patterns</CardTitle>
            <CardDescription>Most common violation types and trends</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {data.incident_patterns.map((pattern: any, i: number) => (
                <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div className="flex-1">
                    <p className="text-sm font-medium">
                      {pattern.type.replace(/_/g, " ").replace(/\b\w/g, (l: string) => l.toUpperCase())}
                    </p>
                    <p className="text-xs text-gray-500">
                      Trend: {pattern.trend > 0 ? "+" : ""}{pattern.trend}% vs last period
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold">{pattern.count}</p>
                    <p className="text-xs text-gray-500">occurrences</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Detail Modal */}
      <Dialog open={!!selectedIncident} onOpenChange={() => setSelectedIncident(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Incident Details</DialogTitle>
            <DialogDescription>
              Full information about this safety violation
            </DialogDescription>
          </DialogHeader>
          {selectedIncident && (
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-red-600 mt-0.5" />
                <div className="flex-1">
                  <p className="font-semibold text-red-900">
                    {selectedIncident.severity.toUpperCase()} Severity Incident
                  </p>
                  <p className="text-sm text-red-700 mt-1">
                    {selectedIncident.violation_type.replace(/_/g, " ").replace(/\b\w/g, (l: string) => l.toUpperCase())}
                  </p>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-xs text-gray-600">Incident ID</p>
                  <p className="font-mono text-sm">{selectedIncident.incident_id}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-600">Timestamp</p>
                  <p className="text-sm">{new Date(selectedIncident.timestamp).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-600">Robot Type</p>
                  <p className="text-sm">{selectedIncident.robot_type}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-600">Environment</p>
                  <p className="text-sm">{selectedIncident.environment_type || "N/A"}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-600">Customer ID</p>
                  <p className="font-mono text-sm">{selectedIncident.customer_id}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-600">Inference ID</p>
                  <p className="font-mono text-sm">{selectedIncident.log_id || "N/A"}</p>
                </div>
              </div>

              <div>
                <p className="text-xs text-gray-600 mb-2">Action Taken</p>
                <p className="text-sm p-3 bg-gray-50 rounded">{selectedIncident.action_taken}</p>
              </div>

              {selectedIncident.details && (
                <div>
                  <p className="text-xs text-gray-600 mb-2">Additional Details</p>
                  <div className="text-sm p-3 bg-gray-50 rounded space-y-1">
                    {Object.entries(selectedIncident.details).map(([key, value]: [string, any]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-600">{key.replace(/_/g, " ")}:</span>
                        <span className="font-mono">{JSON.stringify(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
