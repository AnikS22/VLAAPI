"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api-client";
import { Upload, Zap, AlertTriangle } from "lucide-react";

export default function PlaygroundPage() {
  const { toast } = useToast();
  const [image, setImage] = useState<string | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [instruction, setInstruction] = useState("");
  const [robotType, setRobotType] = useState("franka_panda");
  const [result, setResult] = useState<any>(null);

  const inferMutation = useMutation({
    mutationFn: () => api.runInference(image!, instruction, robotType),
    onSuccess: (data) => {
      setResult(data);
      toast({
        title: "Inference successful",
        description: "Your VLA inference has been completed",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Inference failed",
        description: error.response?.data?.detail || "An error occurred during inference",
        variant: "destructive",
      });
    },
  });

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast({
        title: "File too large",
        description: "Image must be less than 10MB",
        variant: "destructive",
      });
      return;
    }

    // Convert to base64
    const reader = new FileReader();
    reader.onload = (event) => {
      const base64 = event.target?.result as string;
      setImage(base64);
      setImagePreview(base64);
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!image) {
      toast({
        title: "Image required",
        description: "Please upload an image first",
        variant: "destructive",
      });
      return;
    }

    if (!instruction.trim()) {
      toast({
        title: "Instruction required",
        description: "Please enter an instruction",
        variant: "destructive",
      });
      return;
    }

    inferMutation.mutate();
  };

  const robotTypes = [
    { value: "franka_panda", label: "Franka Panda" },
    { value: "ur5", label: "UR5" },
    { value: "kuka_iiwa", label: "KUKA iiwa" },
    { value: "sawyer", label: "Sawyer" },
    { value: "xarm", label: "xArm" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Inference Playground</h1>
        <p className="text-gray-600 mt-2">
          Test VLA inference with custom images and instructions
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input Form */}
        <Card>
          <CardHeader>
            <CardTitle>Input</CardTitle>
            <CardDescription>Upload an image and provide instructions for the robot</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Image Upload */}
              <div className="space-y-2">
                <Label htmlFor="image">Scene Image</Label>
                <div className="border-2 border-dashed rounded-lg p-6 text-center">
                  {imagePreview ? (
                    <div className="space-y-3">
                      <img
                        src={imagePreview}
                        alt="Preview"
                        className="max-h-64 mx-auto rounded-lg"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setImage(null);
                          setImagePreview(null);
                          setResult(null);
                        }}
                      >
                        Change Image
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Upload className="w-8 h-8 text-gray-400 mx-auto" />
                      <div>
                        <Label
                          htmlFor="image"
                          className="cursor-pointer text-blue-600 hover:underline"
                        >
                          Upload an image
                        </Label>
                        <Input
                          id="image"
                          type="file"
                          accept="image/*"
                          className="hidden"
                          onChange={handleImageUpload}
                        />
                      </div>
                      <p className="text-xs text-gray-500">PNG, JPG up to 10MB</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Instruction */}
              <div className="space-y-2">
                <Label htmlFor="instruction">Instruction</Label>
                <Input
                  id="instruction"
                  placeholder="e.g., Pick up the red block and place it in the box"
                  value={instruction}
                  onChange={(e) => setInstruction(e.target.value)}
                />
                <p className="text-xs text-gray-500">
                  Describe what you want the robot to do in natural language
                </p>
              </div>

              {/* Robot Type */}
              <div className="space-y-2">
                <Label htmlFor="robotType">Robot Type</Label>
                <Select value={robotType} onValueChange={setRobotType}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select robot type" />
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

              {/* Submit Button */}
              <Button
                type="submit"
                className="w-full"
                disabled={inferMutation.isPending || !image || !instruction}
              >
                <Zap className="w-4 h-4 mr-2" />
                {inferMutation.isPending ? "Running Inference..." : "Run Inference"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Results */}
        <Card>
          <CardHeader>
            <CardTitle>Results</CardTitle>
            <CardDescription>7-DoF action vector and safety analysis</CardDescription>
          </CardHeader>
          <CardContent>
            {result ? (
              <div className="space-y-6">
                {/* Action Vector */}
                <div>
                  <h3 className="font-semibold mb-3">Action Vector (7-DoF)</h3>
                  <div className="grid grid-cols-1 gap-2">
                    {result.action_vector.map((value: number, i: number) => (
                      <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                        <span className="text-sm font-medium">
                          {["X", "Y", "Z", "Roll", "Pitch", "Yaw", "Gripper"][i]}
                        </span>
                        <span className="font-mono text-sm">{value.toFixed(4)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Safety Score */}
                <div>
                  <h3 className="font-semibold mb-3">Safety Analysis</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Safety Score</span>
                      <div className="flex items-center gap-2">
                        <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${
                              result.safety_score >= 0.8
                                ? "bg-green-500"
                                : result.safety_score >= 0.6
                                ? "bg-yellow-500"
                                : "bg-red-500"
                            }`}
                            style={{ width: `${result.safety_score * 100}%` }}
                          />
                        </div>
                        <span className="font-mono text-sm font-semibold">
                          {(result.safety_score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>

                    {result.safety_flags && result.safety_flags.length > 0 && (
                      <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <div className="flex items-start gap-2">
                          <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
                          <div>
                            <p className="text-sm font-medium text-yellow-800">Safety Warnings</p>
                            <ul className="mt-1 space-y-1">
                              {result.safety_flags.map((flag: string, i: number) => (
                                <li key={i} className="text-xs text-yellow-700">
                                  • {flag}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Metadata */}
                <div>
                  <h3 className="font-semibold mb-3">Metadata</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Inference ID</span>
                      <span className="font-mono text-xs">{result.log_id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Latency</span>
                      <span>{result.latency_ms.toFixed(0)}ms</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Status</span>
                      <span
                        className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                          result.status === "success"
                            ? "bg-green-100 text-green-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {result.status}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12">
                <Zap className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">No results yet</p>
                <p className="text-sm text-gray-500 mt-1">
                  Upload an image and run inference to see results
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
