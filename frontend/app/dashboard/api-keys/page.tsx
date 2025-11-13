"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api-client";
import { Copy, Key, Plus, Trash2 } from "lucide-react";

export default function APIKeysPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  const { data: apiKeys, isLoading } = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => api.getAPIKeys(),
  });

  const createKeyMutation = useMutation({
    mutationFn: (name: string) => api.createAPIKey(name, ["inference"]),
    onSuccess: (data) => {
      setCreatedKey(data.api_key!);
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
      setNewKeyName("");
      toast({
        title: "API Key created",
        description: "Your new API key has been generated. Copy it now - you won't see it again!",
      });
    },
    onError: () => {
      toast({
        title: "Failed to create API key",
        description: "An error occurred while creating the API key",
        variant: "destructive",
      });
    },
  });

  const revokeKeyMutation = useMutation({
    mutationFn: (keyId: string) => api.revokeAPIKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
      toast({
        title: "API Key revoked",
        description: "The API key has been revoked successfully",
      });
    },
    onError: () => {
      toast({
        title: "Failed to revoke API key",
        description: "An error occurred while revoking the API key",
        variant: "destructive",
      });
    },
  });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: "Copied to clipboard",
      description: "API key has been copied to your clipboard",
    });
  };

  const handleCreateKey = () => {
    if (!newKeyName.trim()) {
      toast({
        title: "Name required",
        description: "Please enter a name for your API key",
        variant: "destructive",
      });
      return;
    }
    createKeyMutation.mutate(newKeyName);
  };

  const handleCloseCreateDialog = () => {
    setCreateDialogOpen(false);
    setCreatedKey(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">API Keys</h1>
          <p className="text-gray-600 mt-2">
            Manage your API keys for accessing the VLA inference API
          </p>
        </div>
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Create API Key
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create API Key</DialogTitle>
              <DialogDescription>
                Generate a new API key for accessing the inference API
              </DialogDescription>
            </DialogHeader>
            {createdKey ? (
              <div className="space-y-4">
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                  <p className="text-sm font-medium text-yellow-800 mb-2">
                    ⚠️ Copy this key now - you won&apos;t be able to see it again!
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 p-2 bg-white rounded border text-sm font-mono">
                      {createdKey}
                    </code>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => copyToClipboard(createdKey)}
                    >
                      <Copy className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="keyName">Key Name</Label>
                  <Input
                    id="keyName"
                    placeholder="e.g., Production API Key"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                  />
                </div>
              </div>
            )}
            <DialogFooter>
              {createdKey ? (
                <Button onClick={handleCloseCreateDialog}>Done</Button>
              ) : (
                <>
                  <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateKey} disabled={createKeyMutation.isPending}>
                    {createKeyMutation.isPending ? "Creating..." : "Create Key"}
                  </Button>
                </>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* API Keys Table */}
      <Card>
        <CardHeader>
          <CardTitle>Your API Keys</CardTitle>
          <CardDescription>
            API keys grant access to the inference API. Keep them secure!
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p>Loading API keys...</p>
          ) : apiKeys && apiKeys.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Key Prefix</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Last Used</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {apiKeys.map((key) => (
                  <TableRow key={key.key_id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Key className="w-4 h-4 text-gray-400" />
                        {key.key_name || "Unnamed Key"}
                      </div>
                    </TableCell>
                    <TableCell>
                      <code className="text-sm">{key.key_prefix}...</code>
                    </TableCell>
                    <TableCell>
                      {new Date(key.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {key.last_used_at
                        ? new Date(key.last_used_at).toLocaleDateString()
                        : "Never"}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          key.is_active
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {key.is_active ? "Active" : "Revoked"}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      {key.is_active && (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => revokeKeyMutation.mutate(key.key_id)}
                          disabled={revokeKeyMutation.isPending}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12">
              <Key className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No API keys yet</p>
              <p className="text-sm text-gray-500 mt-1">
                Create your first API key to start using the inference API
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
