"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api-client";
import { ChevronLeft, ChevronRight, History, Search } from "lucide-react";

export default function HistoryPage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    status: "",
    robot_type: "",
    start_date: "",
    end_date: "",
  });
  const [selectedLog, setSelectedLog] = useState<any>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["inference-history", page, filters],
    queryFn: () => api.getInferenceHistory(page, 20, filters),
  });

  const robotTypes = [
    { value: "", label: "All Robots" },
    { value: "franka_panda", label: "Franka Panda" },
    { value: "ur5", label: "UR5" },
    { value: "kuka_iiwa", label: "KUKA iiwa" },
    { value: "sawyer", label: "Sawyer" },
    { value: "xarm", label: "xArm" },
  ];

  const statusOptions = [
    { value: "", label: "All Status" },
    { value: "success", label: "Success" },
    { value: "error", label: "Error" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Inference History</h1>
        <p className="text-gray-600 mt-2">
          Browse and filter your past VLA inference requests
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Filter inference logs by status, robot type, or date range</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select
                value={filters.status}
                onValueChange={(value) => {
                  setFilters({ ...filters, status: value });
                  setPage(1);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  {statusOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="robot_type">Robot Type</Label>
              <Select
                value={filters.robot_type}
                onValueChange={(value) => {
                  setFilters({ ...filters, robot_type: value });
                  setPage(1);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select robot" />
                </SelectTrigger>
                <SelectContent>
                  {robotTypes.map((robot) => (
                    <SelectItem key={robot.value} value={robot.value}>
                      {robot.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="start_date">Start Date</Label>
              <Input
                id="start_date"
                type="date"
                value={filters.start_date}
                onChange={(e) => {
                  setFilters({ ...filters, start_date: e.target.value });
                  setPage(1);
                }}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="end_date">End Date</Label>
              <Input
                id="end_date"
                type="date"
                value={filters.end_date}
                onChange={(e) => {
                  setFilters({ ...filters, end_date: e.target.value });
                  setPage(1);
                }}
              />
            </div>
          </div>

          <div className="mt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setFilters({ status: "", robot_type: "", start_date: "", end_date: "" });
                setPage(1);
              }}
            >
              Clear Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* History Table */}
      <Card>
        <CardHeader>
          <CardTitle>Inference Logs</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-center py-8 text-gray-600">Loading history...</p>
          ) : data && data.logs && data.logs.length > 0 ? (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Instruction</TableHead>
                    <TableHead>Robot</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Latency</TableHead>
                    <TableHead>Safety</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.logs.map((log: any) => (
                    <TableRow key={log.log_id} className="cursor-pointer hover:bg-gray-50">
                      <TableCell className="font-mono text-xs">
                        {new Date(log.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell className="max-w-xs truncate">{log.instruction}</TableCell>
                      <TableCell>
                        {log.robot_type.replace(/_/g, " ").replace(/\b\w/g, (l: string) => l.toUpperCase())}
                      </TableCell>
                      <TableCell>
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            log.status === "success"
                              ? "bg-green-100 text-green-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {log.status}
                        </span>
                      </TableCell>
                      <TableCell>{log.latency_ms.toFixed(0)}ms</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${
                                log.safety_score >= 0.8
                                  ? "bg-green-500"
                                  : log.safety_score >= 0.6
                                  ? "bg-yellow-500"
                                  : "bg-red-500"
                              }`}
                              style={{ width: `${log.safety_score * 100}%` }}
                            />
                          </div>
                          <span className="text-xs">{(log.safety_score * 100).toFixed(0)}%</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedLog(log)}
                        >
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-gray-600">
                  Showing page {page} of {data.total_pages} ({data.total_count} total logs)
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
            </>
          ) : (
            <div className="text-center py-12">
              <History className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No inference logs found</p>
              <p className="text-sm text-gray-500 mt-1">
                Try adjusting your filters or run some inferences in the playground
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Detail Modal */}
      <Dialog open={!!selectedLog} onOpenChange={() => setSelectedLog(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Inference Details</DialogTitle>
            <DialogDescription>
              Full information about this inference request
            </DialogDescription>
          </DialogHeader>
          {selectedLog && (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label className="text-xs text-gray-600">Log ID</Label>
                  <p className="font-mono text-sm">{selectedLog.log_id}</p>
                </div>
                <div>
                  <Label className="text-xs text-gray-600">Timestamp</Label>
                  <p className="text-sm">{new Date(selectedLog.timestamp).toLocaleString()}</p>
                </div>
                <div>
                  <Label className="text-xs text-gray-600">Robot Type</Label>
                  <p className="text-sm">{selectedLog.robot_type}</p>
                </div>
                <div>
                  <Label className="text-xs text-gray-600">Environment</Label>
                  <p className="text-sm">{selectedLog.environment_type || "N/A"}</p>
                </div>
              </div>

              <div>
                <Label className="text-xs text-gray-600">Instruction</Label>
                <p className="text-sm mt-1 p-3 bg-gray-50 rounded">{selectedLog.instruction}</p>
              </div>

              <div>
                <Label className="text-xs text-gray-600">Action Vector (7-DoF)</Label>
                <div className="grid grid-cols-7 gap-2 mt-1">
                  {selectedLog.action_vector?.map((value: number, i: number) => (
                    <div key={i} className="text-center">
                      <p className="text-xs text-gray-600">
                        {["X", "Y", "Z", "R", "P", "Y", "G"][i]}
                      </p>
                      <p className="font-mono text-xs">{value.toFixed(3)}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <Label className="text-xs text-gray-600">Safety Score</Label>
                  <p className="text-lg font-semibold">{(selectedLog.safety_score * 100).toFixed(1)}%</p>
                </div>
                <div>
                  <Label className="text-xs text-gray-600">Latency</Label>
                  <p className="text-lg font-semibold">{selectedLog.latency_ms.toFixed(0)}ms</p>
                </div>
                <div>
                  <Label className="text-xs text-gray-600">Status</Label>
                  <p className="text-lg font-semibold capitalize">{selectedLog.status}</p>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
