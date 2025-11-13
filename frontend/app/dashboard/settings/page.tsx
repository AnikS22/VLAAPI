"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api-client";
import { CreditCard, ExternalLink, Lock, Settings as SettingsIcon, User } from "lucide-react";

export default function SettingsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [profileData, setProfileData] = useState({ full_name: "", company_name: "" });
  const [passwordData, setPasswordData] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [consentData, setConsentData] = useState({
    data_collection: true,
    model_training: true,
    analytics: true,
  });

  const { data: user } = useQuery({
    queryKey: ["user-profile"],
    queryFn: () => api.getMe(),
  });

  useEffect(() => {
    if (user) {
      setProfileData({
        full_name: user.full_name || "",
        company_name: "", // This would come from customer data
      });
    }
  }, [user]);

  const { data: subscription } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => api.getSubscription(),
  });

  const profileMutation = useMutation({
    mutationFn: () => api.updateUserProfile(profileData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-profile"] });
      toast({ title: "Profile updated", description: "Your profile has been saved" });
    },
    onError: () => {
      toast({ title: "Update failed", description: "Failed to update profile", variant: "destructive" });
    },
  });

  const passwordMutation = useMutation({
    mutationFn: () => api.changePassword(passwordData.current_password, passwordData.new_password),
    onSuccess: () => {
      setPasswordData({ current_password: "", new_password: "", confirm_password: "" });
      toast({ title: "Password changed", description: "Your password has been updated" });
    },
    onError: () => {
      toast({ title: "Password change failed", description: "Check your current password", variant: "destructive" });
    },
  });

  const consentMutation = useMutation({
    mutationFn: () => api.updateConsentPreferences(consentData),
    onSuccess: () => {
      toast({ title: "Preferences updated", description: "Your consent preferences have been saved" });
    },
  });

  const handlePasswordChange = (e: React.FormEvent) => {
    e.preventDefault();

    if (passwordData.new_password !== passwordData.confirm_password) {
      toast({ title: "Passwords don't match", variant: "destructive" });
      return;
    }

    if (passwordData.new_password.length < 8) {
      toast({ title: "Password too short", description: "Password must be at least 8 characters", variant: "destructive" });
      return;
    }

    passwordMutation.mutate();
  };

  const handleUpgrade = async (tier: string) => {
    try {
      const successUrl = `${window.location.origin}/dashboard/settings?upgrade=success`;
      const cancelUrl = `${window.location.origin}/dashboard/settings?upgrade=cancelled`;
      const { url } = await api.createCheckoutSession(tier, successUrl, cancelUrl);
      window.location.href = url;
    } catch (error) {
      toast({ title: "Checkout failed", description: "Unable to create checkout session", variant: "destructive" });
    }
  };

  const handleBillingPortal = async () => {
    try {
      const returnUrl = `${window.location.origin}/dashboard/settings`;
      const { url } = await api.getBillingPortal(returnUrl);
      window.location.href = url;
    } catch (error) {
      toast({ title: "Portal access failed", description: "Unable to open billing portal", variant: "destructive" });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-gray-600 mt-2">
          Manage your account, billing, and preferences
        </p>
      </div>

      {/* Profile Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="w-5 h-5" />
            Profile Information
          </CardTitle>
          <CardDescription>Update your personal and company information</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              profileMutation.mutate();
            }}
            className="space-y-4"
          >
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" value={user?.email || ""} disabled />
              </div>

              <div className="space-y-2">
                <Label htmlFor="full_name">Full Name</Label>
                <Input
                  id="full_name"
                  value={profileData.full_name}
                  onChange={(e) => setProfileData({ ...profileData, full_name: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="company_name">Company Name</Label>
                <Input
                  id="company_name"
                  value={profileData.company_name}
                  onChange={(e) => setProfileData({ ...profileData, company_name: e.target.value })}
                />
              </div>
            </div>

            <Button type="submit" disabled={profileMutation.isPending}>
              {profileMutation.isPending ? "Saving..." : "Save Profile"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Password Change */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="w-5 h-5" />
            Change Password
          </CardTitle>
          <CardDescription>Update your password to keep your account secure</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handlePasswordChange} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="current_password">Current Password</Label>
              <Input
                id="current_password"
                type="password"
                value={passwordData.current_password}
                onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="new_password">New Password</Label>
                <Input
                  id="new_password"
                  type="password"
                  value={passwordData.new_password}
                  onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm_password">Confirm Password</Label>
                <Input
                  id="confirm_password"
                  type="password"
                  value={passwordData.confirm_password}
                  onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
                />
              </div>
            </div>

            <Button type="submit" disabled={passwordMutation.isPending}>
              {passwordMutation.isPending ? "Changing..." : "Change Password"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Subscription & Billing */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="w-5 h-5" />
            Subscription & Billing
          </CardTitle>
          <CardDescription>Manage your plan and billing information</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Current Plan */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold">Current Plan</h3>
                <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full capitalize">
                  {subscription?.tier || "Free"}
                </span>
              </div>
              <div className="grid gap-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Monthly Usage</span>
                  <span className="font-medium">
                    {subscription?.monthly_usage?.toLocaleString() || 0}
                    {subscription?.monthly_quota && ` / ${subscription.monthly_quota.toLocaleString()}`}
                  </span>
                </div>
                {subscription?.status && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Status</span>
                    <span className="font-medium capitalize">{subscription.status}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Upgrade Options */}
            {subscription?.tier === "free" && (
              <div>
                <h3 className="font-semibold mb-3">Upgrade Your Plan</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="border rounded-lg p-4">
                    <h4 className="font-semibold text-lg">Pro</h4>
                    <p className="text-2xl font-bold mt-2">$499<span className="text-sm text-gray-600">/month</span></p>
                    <ul className="mt-4 space-y-2 text-sm">
                      <li>✓ 50,000 requests/month</li>
                      <li>✓ Priority support</li>
                      <li>✓ Advanced analytics</li>
                      <li>✓ Custom robot types</li>
                    </ul>
                    <Button className="w-full mt-4" onClick={() => handleUpgrade("pro")}>
                      Upgrade to Pro
                    </Button>
                  </div>

                  <div className="border rounded-lg p-4">
                    <h4 className="font-semibold text-lg">Enterprise</h4>
                    <p className="text-2xl font-bold mt-2">Custom</p>
                    <ul className="mt-4 space-y-2 text-sm">
                      <li>✓ Unlimited requests</li>
                      <li>✓ Dedicated support</li>
                      <li>✓ Custom SLA</li>
                      <li>✓ On-premise deployment</li>
                    </ul>
                    <Button variant="outline" className="w-full mt-4">
                      Contact Sales
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Billing Portal */}
            {subscription?.tier !== "free" && (
              <Button variant="outline" onClick={handleBillingPortal}>
                <ExternalLink className="w-4 h-4 mr-2" />
                Manage Billing in Stripe
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Consent Preferences */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <SettingsIcon className="w-5 h-5" />
            Consent Preferences
          </CardTitle>
          <CardDescription>Control how your data is used</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              consentMutation.mutate();
            }}
            className="space-y-4"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="data_collection">Data Collection</Label>
                  <p className="text-sm text-gray-600">Allow collection of inference data for service improvement</p>
                </div>
                <input
                  id="data_collection"
                  type="checkbox"
                  checked={consentData.data_collection}
                  onChange={(e) => setConsentData({ ...consentData, data_collection: e.target.checked })}
                  className="h-4 w-4"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="model_training">Model Training</Label>
                  <p className="text-sm text-gray-600">Use my data to improve VLA models</p>
                </div>
                <input
                  id="model_training"
                  type="checkbox"
                  checked={consentData.model_training}
                  onChange={(e) => setConsentData({ ...consentData, model_training: e.target.checked })}
                  className="h-4 w-4"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="analytics">Analytics</Label>
                  <p className="text-sm text-gray-600">Share anonymized usage analytics</p>
                </div>
                <input
                  id="analytics"
                  type="checkbox"
                  checked={consentData.analytics}
                  onChange={(e) => setConsentData({ ...consentData, analytics: e.target.checked })}
                  className="h-4 w-4"
                />
              </div>
            </div>

            <Button type="submit" disabled={consentMutation.isPending}>
              {consentMutation.isPending ? "Saving..." : "Save Preferences"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
