"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/store/auth-store";
import { useProfile, useRevokeSecuritySession, useSecuritySessions, useUpdateProfile } from "@/hooks/use-profile";

export default function ProfilePage() {
  const router = useRouter();
  const { isAuthenticated, isHydrating } = useAuthStore();
  const profile = useProfile();
  const sessions = useSecuritySessions();
  const updateProfile = useUpdateProfile();
  const revoke = useRevokeSecuritySession();
  const [fullName, setFullName] = useState("");
  const [riskProfile, setRiskProfile] = useState("moderate");

  useEffect(() => {
    if (!isHydrating && !isAuthenticated) router.replace("/login");
  }, [isAuthenticated, isHydrating, router]);
  useEffect(() => {
    if (profile.data) {
      // Form state is initialized from the asynchronously loaded profile.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFullName(profile.data.full_name || "");
      setRiskProfile(profile.data.risk_profile || "moderate");
    }
  }, [profile.data]);
  if (isHydrating || !isAuthenticated) return null;

  return <main className="prism-shell"><div className="prism-page max-w-4xl">
    <header className="prism-hero"><p className="prism-kicker">Identity & controls</p><h1 className="mt-1 text-2xl font-bold">Profile & security</h1><p className="mt-1 text-sm text-muted-foreground">Preferences, connected-exchange security, and active sessions.</p></header>
    <Card className="prism-panel"><CardHeader><CardTitle>Preferences</CardTitle><CardDescription>Risk preferences inform the context used for decision support; they never enable trading.</CardDescription></CardHeader><CardContent className="space-y-4">
      <Input aria-label="Full name" value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Full name" />
      <label className="block text-sm font-medium">Risk profile<select className="mt-1 w-full rounded-md border bg-background p-2" value={riskProfile} onChange={(event) => setRiskProfile(event.target.value)}><option value="conservative">Conservative</option><option value="moderate">Moderate</option><option value="aggressive">Aggressive</option></select></label>
      <Button disabled={updateProfile.isPending} onClick={() => updateProfile.mutate({ full_name: fullName || null, risk_profile: riskProfile })}>{updateProfile.isPending ? "Saving…" : "Save preferences"}</Button>
    </CardContent></Card>
    <Card className="prism-panel"><CardHeader><CardTitle>Active sessions</CardTitle><CardDescription>Revoke a device session you no longer recognize. Refresh tokens are stored only as hashes.</CardDescription></CardHeader><CardContent className="space-y-3">
      {sessions.isLoading && <p className="text-sm text-muted-foreground">Loading sessions…</p>}
      {sessions.data?.map((session) => <div key={session.id} className="flex items-center justify-between gap-4 border rounded-md p-3"><div className="text-sm"><p>{session.user_agent || "Unknown device"} {session.is_current ? "(current)" : ""}</p><p className="text-muted-foreground">{session.ip_address || "IP unavailable"} · expires {new Date(session.expires_at).toLocaleDateString()}</p></div><Button variant="outline" size="sm" disabled={revoke.isPending} onClick={() => revoke.mutate(session.id)}>Revoke</Button></div>)}
      {sessions.data?.length === 0 && <p className="text-sm text-muted-foreground">No active refresh sessions found.</p>}
    </CardContent></Card>
  </div></main>;
}
