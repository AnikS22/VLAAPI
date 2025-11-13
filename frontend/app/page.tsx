import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Hero Section */}
      <section className="flex-1 flex flex-col items-center justify-center px-4 py-16 bg-gradient-to-b from-blue-50 to-white">
        <div className="max-w-4xl text-center space-y-8">
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight">
            VLA Inference Infrastructure
            <br />
            <span className="text-blue-600">Built for Production Robots</span>
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Production-ready Vision-Language-Action inference API with integrated safety monitoring,
            real-time streaming, and comprehensive analytics.
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/auth/register">
              <Button size="lg" className="text-lg">
                Start Free Trial
              </Button>
            </Link>
            <Link href="/auth/login">
              <Button size="lg" variant="outline" className="text-lg">
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4 bg-white">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">
            Production-Ready VLA Inference
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-6 border rounded-lg">
              <h3 className="text-xl font-semibold mb-3">Real-Time Inference</h3>
              <p className="text-gray-600">
                Sub-100ms inference with WebSocket streaming for live robot control
              </p>
            </div>
            <div className="p-6 border rounded-lg">
              <h3 className="text-xl font-semibold mb-3">Safety Monitoring</h3>
              <p className="text-gray-600">
                Built-in workspace validation, velocity limits, and collision detection
              </p>
            </div>
            <div className="p-6 border rounded-lg">
              <h3 className="text-xl font-semibold mb-3">Analytics Dashboard</h3>
              <p className="text-gray-600">
                Track usage, performance, safety incidents, and robot-specific metrics
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-20 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">Simple Pricing</h2>
          <div className="grid md:grid-cols-3 gap-8">
            {/* Free Tier */}
            <div className="p-8 border rounded-lg bg-white">
              <h3 className="text-2xl font-bold mb-2">Researcher</h3>
              <div className="text-4xl font-bold mb-4">
                Free
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-start">
                  <span className="text-green-500 mr-2">✓</span>
                  10 RPM, 1K RPD
                </li>
                <li className="flex items-start">
                  <span className="text-green-500 mr-2">✓</span>
                  10K requests/month
                </li>
                <li className="flex items-start">
                  <span className="text-green-500 mr-2">✓</span>
                  Community support
                </li>
              </ul>
              <Link href="/auth/register">
                <Button className="w-full" variant="outline">
                  Start Free
                </Button>
              </Link>
            </div>

            {/* Pro Tier */}
            <div className="p-8 border-2 border-blue-600 rounded-lg bg-white relative">
              <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-4 py-1 rounded-full text-sm">
                Popular
              </div>
              <h3 className="text-2xl font-bold mb-2">Startup</h3>
              <div className="text-4xl font-bold mb-4">
                $499<span className="text-lg text-gray-600">/mo</span>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-start">
                  <span className="text-green-500 mr-2">✓</span>
                  100 RPM, 10K RPD
                </li>
                <li className="flex items-start">
                  <span className="text-green-500 mr-2">✓</span>
                  100K requests/month
                </li>
                <li className="flex items-start">
                  <span className="text-green-500 mr-2">✓</span>
                  Priority support
                </li>
                <li className="flex items-start">
                  <span className="text-green-500 mr-2">✓</span>
                  Advanced analytics
                </li>
              </ul>
              <Link href="/auth/register">
                <Button className="w-full">
                  Start Trial
                </Button>
              </Link>
            </div>

            {/* Enterprise Tier */}
            <div className="p-8 border rounded-lg bg-white">
              <h3 className="text-2xl font-bold mb-2">Enterprise</h3>
              <div className="text-4xl font-bold mb-4">
                Custom
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-start">
                  <span className="text-green-500 mr-2">✓</span>
                  Custom rate limits
                </li>
                <li className="flex items-start">
                  <span className="text-green-500 mr-2">✓</span>
                  Unlimited requests
                </li>
                <li className="flex items-start">
                  <span className="text-green-500 mr-2">✓</span>
                  24/7 support
                </li>
                <li className="flex items-start">
                  <span className="text-green-500 mr-2">✓</span>
                  Custom deployment
                </li>
              </ul>
              <Link href="/auth/register">
                <Button className="w-full" variant="outline">
                  Contact Sales
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-4 border-t">
        <div className="max-w-6xl mx-auto text-center text-gray-600">
          <p>© 2025 Praxis Labs. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
