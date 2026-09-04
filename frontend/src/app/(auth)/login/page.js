"use client";

/**
 * Login / Register page
 *
 * Provides a minimal auth form that:
 *  - Calls POST /auth/login or POST /auth/register
 *  - Stores the access token in Zustand on success
 *  - Redirects to /dashboard
 *
 * This is the full stack validation page — it confirms the
 * API client, Zustand store, and auth service all work end-to-end.
 */

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuthStore } from "@/store/auth-store";
import apiClient from "@/lib/api-client";
import { ArrowLeft, Check, ShieldCheck, Sparkles } from "lucide-react";


export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();

  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (mode === "register" && password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);

    try {
      const endpoint = mode === "login" ? "/auth/login" : "/auth/register";
      const payload =
        mode === "login"
          ? { email: email.trim(), password }
          : { email: email.trim(), password, full_name: fullName.trim() || undefined };

      const { data } = await apiClient.post(endpoint, payload);

      // Store user + access token in memory
      setAuth(data.user, data.tokens.access_token);

      router.push("/dashboard");
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = Array.isArray(detail)
        ? detail[0]?.msg || "Please check the information and try again."
        : detail ||
          (err.request
            ? "Unable to reach PrismAI. Please make sure the backend is running."
            : mode === "login"
              ? "Invalid credentials."
              : "Registration failed. Please try again.");
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="prism-grid relative grid min-h-screen overflow-hidden lg:grid-cols-2">
      <div className="prism-orb size-80 bg-primary/14 -top-40 -left-28" />
      <div className="prism-orb size-72 bg-emerald-400/10 -bottom-32 -right-28" style={{ animationDelay: "-4s" }} />
      <section className="relative hidden border-r border-white/10 p-10 lg:flex lg:flex-col lg:justify-between">
        <Link href="/" className="relative z-10 flex items-center gap-2.5 self-start"><span className="grid size-9 place-items-center rounded-xl bg-primary font-black text-primary-foreground shadow-lg shadow-primary/25">P</span><span className="text-lg font-semibold tracking-tight">Prism<span className="text-primary">AI</span></span></Link>
        <div className="relative z-10 max-w-lg"><p className="prism-eyebrow"><Sparkles className="size-3.5" /> Private intelligence</p><h1 className="mt-5 text-5xl font-semibold leading-[1.06] tracking-[-.04em]">A calmer way to understand crypto.</h1><p className="mt-5 text-base leading-7 text-muted-foreground">Bring your questions, portfolio, and market context together—without handing over control.</p><ul className="mt-8 space-y-3 text-sm text-muted-foreground"><li className="flex items-center gap-3"><Check className="size-4 text-emerald-400" /> Read-only Binance connection</li><li className="flex items-center gap-3"><Check className="size-4 text-emerald-400" /> Live data and technical context</li><li className="flex items-center gap-3"><Check className="size-4 text-emerald-400" /> Clear risk and uncertainty signals</li></ul></div>
        <p className="relative z-10 text-xs text-muted-foreground">Decision support only. Never a promise of outcome.</p>
      </section>
      <section className="relative flex items-center justify-center px-4 py-12 sm:px-8">
      <div className="w-full max-w-md space-y-6" style={{ animation: "prism-in .45s ease-out both" }}>
        {/* Brand */}
        <div className="text-center space-y-1">
          <Link href="/" className="mb-5 inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground lg:hidden"><ArrowLeft className="size-3.5" /> Back to home</Link>
          <p className="prism-kicker mb-2">Private by design</p>
          <div className="mx-auto mb-3 grid size-12 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-xl shadow-primary/25"><Sparkles className="size-5" /></div>
          <h1 className="text-4xl font-bold tracking-tight">
            Prism<span className="text-primary">AI</span>
          </h1>
          <p className="text-sm text-muted-foreground">
            AI-powered crypto trading intelligence
          </p>
        </div>

        <Card className="prism-panel rounded-3xl border-primary/20">
          <CardHeader className="pb-3">
            <CardTitle className="text-xl">
              {mode === "login" ? "Sign in" : "Create account"}
            </CardTitle>
            <CardDescription>
              {mode === "login"
                ? "Enter your credentials to access your dashboard."
                : "Register a new PrismAI account."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4" id="auth-form">
              {mode === "register" && (
                <div className="space-y-1.5">
                  <Label htmlFor="full-name">Full name</Label>
                  <Input
                    id="full-name"
                    type="text"
                    placeholder="Jane Smith"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    autoComplete="name"
                  />
                </div>
              )}

              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  minLength={8}
                />
              </div>

              {mode === "register" && (
                <div className="space-y-1.5">
                  <Label htmlFor="confirm-password">Confirm password</Label>
                  <Input
                    id="confirm-password"
                    type="password"
                    placeholder="â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    minLength={8}
                  />
                </div>
              )}

              {error && (
                <p className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
                  {error}
                </p>
              )}

              <Button
                type="submit"
                className="w-full"
                disabled={isLoading}
                id="auth-submit-btn"
              >
                {isLoading
                  ? mode === "login"
                    ? "Signing in…"
                    : "Creating account…"
                  : mode === "login"
                  ? "Sign in"
                  : "Create account"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="flex items-center justify-center gap-2 text-center text-xs text-muted-foreground"><ShieldCheck className="size-3.5 shrink-0 text-emerald-400" /> Refresh tokens remain in a secure httpOnly cookie.</div>

        <p className="text-center text-sm text-muted-foreground">
          {mode === "login" ? "Don't have an account?" : "Already have an account?"}{" "}
          <button
            type="button"
            id="toggle-auth-mode"
            className="text-primary underline-offset-4 hover:underline font-medium"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError(null);
            }}
          >
            {mode === "login" ? "Sign up" : "Sign in"}
          </button>
        </p>
      </div>
      </section>
    </main>
  );
}
