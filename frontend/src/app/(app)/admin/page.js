"use client";

import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ShieldCheck, UsersRound, MessageSquareWarning } from "lucide-react";
import apiClient from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const complaintStatuses = ["open", "in_progress", "resolved", "closed"];

export default function AdminPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, isAuthenticated, isHydrating } = useAuthStore();
  const users = useQuery({ queryKey: ["admin", "users"], queryFn: async () => (await apiClient.get("/admin/users")).data, enabled: user?.role === "admin" });
  const complaints = useQuery({ queryKey: ["admin", "complaints"], queryFn: async () => (await apiClient.get("/admin/complaints")).data, enabled: user?.role === "admin" });
  const updateUser = useMutation({ mutationFn: ({ id, is_active }) => apiClient.patch(`/admin/users/${id}`, { is_active }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "users"] }) });
  const updateComplaint = useMutation({ mutationFn: ({ id, status }) => apiClient.patch(`/complaints/${id}/status`, { status }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "complaints"] }) });

  useEffect(() => { if (!isHydrating && (!isAuthenticated || user?.role !== "admin")) router.replace("/dashboard"); }, [isAuthenticated, isHydrating, router, user?.role]);
  if (isHydrating || !isAuthenticated || user?.role !== "admin") return null;
  const hasError = users.isError || complaints.isError;

  return <main className="prism-shell"><div className="mx-auto max-w-6xl space-y-6" style={{ animation: "prism-in .35s ease-out both" }}>
    <header className="rounded-2xl border border-primary/20 bg-primary/8 p-5 sm:p-7"><div className="flex items-start gap-4"><span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-primary text-primary-foreground"><ShieldCheck className="size-5" /></span><div><p className="prism-kicker">Restricted workspace</p><h1 className="mt-1 text-2xl font-semibold tracking-tight">Operations console</h1><p className="mt-1 text-sm text-muted-foreground">Review access and support records without exposing sensitive account data.</p></div></div></header>
    {hasError && <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm"><span>Unable to load one or more operational records.</span><Button size="sm" variant="outline" onClick={() => { users.refetch(); complaints.refetch(); }}>Try again</Button></div>}
    <section className="grid gap-4 sm:grid-cols-2"><Stat icon={UsersRound} label="Users" value={users.isLoading ? "…" : users.data?.length ?? "—"} /><Stat icon={MessageSquareWarning} label="Support tickets" value={complaints.isLoading ? "…" : complaints.data?.length ?? "—"} /></section>
    <section className="grid gap-5 lg:grid-cols-2">
      <Card className="prism-panel"><CardHeader><CardTitle>Account access</CardTitle><CardDescription>Activate or disable accounts. Your own account cannot be disabled.</CardDescription></CardHeader><CardContent className="space-y-2">{users.isLoading ? <p className="text-sm text-muted-foreground">Loading accounts…</p> : users.data?.length ? users.data.slice(0, 25).map((item) => <div key={item.id} className="flex items-center justify-between gap-3 rounded-xl bg-muted/45 p-3"><div className="min-w-0"><p className="truncate text-sm font-medium">{item.email}</p><p className="text-xs text-muted-foreground">{item.role}</p></div><Button size="sm" variant={item.is_active ? "outline" : "default"} disabled={item.id === user.id || updateUser.isPending} onClick={() => updateUser.mutate({ id: item.id, is_active: !item.is_active })}>{item.is_active ? "Disable" : "Enable"}</Button></div>) : <p className="text-sm text-muted-foreground">No accounts found.</p>}</CardContent></Card>
      <Card className="prism-panel"><CardHeader><CardTitle>Support triage</CardTitle><CardDescription>Update ticket status directly from the review queue.</CardDescription></CardHeader><CardContent className="space-y-2">{complaints.isLoading ? <p className="text-sm text-muted-foreground">Loading tickets…</p> : complaints.data?.length ? complaints.data.slice(0, 25).map((item) => <div key={item.id} className="flex items-center justify-between gap-3 rounded-xl bg-muted/45 p-3"><div className="min-w-0"><p className="truncate text-sm font-medium">{item.subject}</p><Badge variant="secondary" className="mt-1">{item.status.replace("_", " ")}</Badge></div><select aria-label={`Set status for ${item.subject}`} value={item.status} disabled={updateComplaint.isPending} onChange={(event) => updateComplaint.mutate({ id: item.id, status: event.target.value })} className="rounded-lg border border-border bg-background px-2 py-1.5 text-xs"><>{complaintStatuses.map((status) => <option key={status} value={status}>{status.replace("_", " ")}</option>)}</></select></div>) : <p className="text-sm text-muted-foreground">No support tickets found.</p>}</CardContent></Card>
    </section>
  </div></main>;
}

function Stat({ icon: Icon, label, value }) { return <Card className="prism-panel"><CardContent className="flex items-center gap-4 p-5"><span className="grid size-10 place-items-center rounded-xl bg-primary/12 text-primary"><Icon className="size-5" /></span><div><p className="text-sm text-muted-foreground">{label}</p><p className="text-2xl font-semibold tracking-tight">{value}</p></div></CardContent></Card>; }
