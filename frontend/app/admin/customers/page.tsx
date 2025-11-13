"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api-client";
import { Users, Search, ChevronLeft, ChevronRight, TrendingUp } from "lucide-react";

export default function CustomersPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);
  const [newTier, setNewTier] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["admin-customers", page],
    queryFn: () => api.getAllCustomers(page, 50),
  });

  const { data: customerDetails } = useQuery({
    queryKey: ["customer-details", selectedCustomer?.customer_id],
    queryFn: () => api.getCustomerDetails(selectedCustomer.customer_id),
    enabled: !!selectedCustomer,
  });

  const updateTierMutation = useMutation({
    mutationFn: ({ customer_id, tier }: { customer_id: string; tier: string }) =>
      api.updateCustomerTier(customer_id, tier),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-customers"] });
      queryClient.invalidateQueries({ queryKey: ["customer-details"] });
      toast({
        title: "Tier updated",
        description: "Customer tier has been updated successfully",
      });
      setSelectedCustomer(null);
    },
    onError: () => {
      toast({
        title: "Update failed",
        description: "Failed to update customer tier",
        variant: "destructive",
      });
    },
  });

  const filteredCustomers = data?.customers?.filter((customer: any) => {
    const search = searchQuery.toLowerCase();
    return (
      customer.email?.toLowerCase().includes(search) ||
      customer.company_name?.toLowerCase().includes(search) ||
      customer.customer_id?.toLowerCase().includes(search)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Customer Management</h1>
        <p className="text-gray-600 mt-2">
          View and manage all platform customers
        </p>
      </div>

      {/* Search & Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Search Customers</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="Search by email, company, or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Customers Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Customers</CardTitle>
          <CardDescription>
            {data?.total_count || 0} total customers
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-center py-8 text-gray-600">Loading customers...</p>
          ) : filteredCustomers && filteredCustomers.length > 0 ? (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email / Company</TableHead>
                    <TableHead>Tier</TableHead>
                    <TableHead>Usage</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredCustomers.map((customer: any) => (
                    <TableRow key={customer.customer_id}>
                      <TableCell>
                        <div>
                          <p className="text-sm font-medium">{customer.email}</p>
                          {customer.company_name && (
                            <p className="text-xs text-gray-500">{customer.company_name}</p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            customer.tier === "enterprise"
                              ? "bg-purple-100 text-purple-800"
                              : customer.tier === "pro"
                              ? "bg-blue-100 text-blue-800"
                              : "bg-gray-100 text-gray-800"
                          }`}
                        >
                          {customer.tier}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          <p className="font-medium">{customer.monthly_usage?.toLocaleString() || 0}</p>
                          {customer.monthly_quota && (
                            <p className="text-xs text-gray-500">
                              / {customer.monthly_quota.toLocaleString()}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm">
                        {new Date(customer.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            customer.is_active
                              ? "bg-green-100 text-green-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {customer.is_active ? "Active" : "Suspended"}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedCustomer(customer)}
                        >
                          View Details
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
              <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No customers found</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Customer Detail Modal */}
      <Dialog open={!!selectedCustomer} onOpenChange={() => setSelectedCustomer(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Customer Details</DialogTitle>
            <DialogDescription>
              Detailed information and management options
            </DialogDescription>
          </DialogHeader>
          {selectedCustomer && customerDetails && (
            <div className="space-y-6">
              {/* Basic Info */}
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label className="text-xs text-gray-600">Customer ID</Label>
                  <p className="font-mono text-sm">{selectedCustomer.customer_id}</p>
                </div>
                <div>
                  <Label className="text-xs text-gray-600">Email</Label>
                  <p className="text-sm">{selectedCustomer.email}</p>
                </div>
                <div>
                  <Label className="text-xs text-gray-600">Company</Label>
                  <p className="text-sm">{selectedCustomer.company_name || "N/A"}</p>
                </div>
                <div>
                  <Label className="text-xs text-gray-600">Created</Label>
                  <p className="text-sm">{new Date(selectedCustomer.created_at).toLocaleDateString()}</p>
                </div>
              </div>

              {/* Usage Stats */}
              <div>
                <h3 className="font-semibold mb-3">Usage Statistics</h3>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-600">Monthly Usage</p>
                    <p className="text-lg font-semibold mt-1">
                      {customerDetails.monthly_usage?.toLocaleString() || 0}
                    </p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-600">Total Requests</p>
                    <p className="text-lg font-semibold mt-1">
                      {customerDetails.total_requests?.toLocaleString() || 0}
                    </p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-600">Success Rate</p>
                    <p className="text-lg font-semibold mt-1">
                      {customerDetails.success_rate?.toFixed(1) || 0}%
                    </p>
                  </div>
                </div>
              </div>

              {/* Tier Management */}
              <div>
                <h3 className="font-semibold mb-3">Tier Management</h3>
                <div className="flex items-end gap-4">
                  <div className="flex-1">
                    <Label htmlFor="tier">Update Tier</Label>
                    <Select value={newTier || selectedCustomer.tier} onValueChange={setNewTier}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select tier" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="free">Free</SelectItem>
                        <SelectItem value="pro">Pro</SelectItem>
                        <SelectItem value="enterprise">Enterprise</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button
                    onClick={() => {
                      if (newTier && newTier !== selectedCustomer.tier) {
                        updateTierMutation.mutate({
                          customer_id: selectedCustomer.customer_id,
                          tier: newTier,
                        });
                      }
                    }}
                    disabled={!newTier || newTier === selectedCustomer.tier || updateTierMutation.isPending}
                  >
                    <TrendingUp className="w-4 h-4 mr-2" />
                    {updateTierMutation.isPending ? "Updating..." : "Update Tier"}
                  </Button>
                </div>
              </div>

              {/* Recent Activity */}
              {customerDetails.recent_inferences && customerDetails.recent_inferences.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-3">Recent Inferences</h3>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {customerDetails.recent_inferences.slice(0, 10).map((log: any) => (
                      <div key={log.log_id} className="flex items-center justify-between p-2 bg-gray-50 rounded text-xs">
                        <span className="font-mono">{new Date(log.timestamp).toLocaleString()}</span>
                        <span className="truncate max-w-xs">{log.instruction}</span>
                        <span
                          className={`px-2 py-0.5 rounded-full ${
                            log.status === "success"
                              ? "bg-green-100 text-green-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {log.status}
                        </span>
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
