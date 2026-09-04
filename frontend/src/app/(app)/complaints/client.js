"use client";

import { useState } from "react";
import {
  HelpCircle,
  Plus,
  MessageSquare,
  Clock,
  CheckCircle2,
  AlertCircle,
  Send,
  X,
  ShieldCheck,
  User as UserIcon,
  Tag,
  AlertTriangle,
  FolderOpen,
} from "lucide-react";
import {
  useComplaints,
  useComplaintSummary,
  useComplaintDetail,
  useCreateComplaint,
  useAddComplaintMessage,
  useUpdateComplaintStatus,
} from "@/hooks/use-complaints";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

const CATEGORIES = [
  "Account & Security",
  "Exchange Connection",
  "Market & Charts Data",
  "AI Assistant & Analyses",
  "Portfolio Tracking",
  "Bug Report",
  "General Inquiry",
];

const PRIORITIES = [
  { value: "low", label: "Low", color: "bg-muted text-muted-foreground" },
  { value: "medium", label: "Medium", color: "bg-sky-500/10 text-sky-400 border-sky-500/20" },
  { value: "high", label: "High", color: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
  { value: "urgent", label: "Urgent", color: "bg-rose-500/10 text-rose-400 border-rose-500/20" },
];

export default function ComplaintsPageClient() {
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [activeComplaintId, setActiveComplaintId] = useState(null);

  const { data: complaints, isLoading } = useComplaints({
    status: selectedStatus,
    category: selectedCategory,
  });
  const { data: summary } = useComplaintSummary();
  const { data: activeDetail, isLoading: isLoadingDetail } = useComplaintDetail(activeComplaintId);

  const { mutate: createComplaint, isPending: isCreating } = useCreateComplaint();
  const { mutate: addMessage, isPending: isSending } = useAddComplaintMessage();
  const { mutate: updateStatus, isPending: isUpdatingStatus } = useUpdateComplaintStatus();

  // Create ticket modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [subjectInput, setSubjectInput] = useState("");
  const [categoryInput, setCategoryInput] = useState("General Inquiry");
  const [priorityInput, setPriorityInput] = useState("medium");
  const [descriptionInput, setDescriptionInput] = useState("");

  // Thread reply state
  const [replyInput, setReplyInput] = useState("");

  const handleCreateSubmit = (e) => {
    e.preventDefault();
    if (!subjectInput.trim() || !descriptionInput.trim()) return;

    createComplaint(
      {
        subject: subjectInput.trim(),
        category: categoryInput,
        priority: priorityInput,
        description: descriptionInput.trim(),
      },
      {
        onSuccess: (data) => {
          setShowCreateModal(false);
          setSubjectInput("");
          setDescriptionInput("");
          setActiveComplaintId(data.id);
        },
      }
    );
  };

  const handleSendReply = (e) => {
    e.preventDefault();
    if (!replyInput.trim() || !activeComplaintId) return;

    addMessage(
      {
        complaintId: activeComplaintId,
        message: replyInput.trim(),
      },
      {
        onSuccess: () => {
          setReplyInput("");
        },
      }
    );
  };

  const handleStatusChange = (status) => {
    if (!activeComplaintId) return;
    updateStatus({
      complaintId: activeComplaintId,
      status,
    });
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "open":
        return <Badge variant="outline" className="text-xs bg-sky-500/10 text-sky-400 border-sky-500/30">Open</Badge>;
      case "in_progress":
        return <Badge variant="outline" className="text-xs bg-amber-500/10 text-amber-400 border-amber-500/30">In Progress</Badge>;
      case "resolved":
        return <Badge variant="outline" className="text-xs bg-emerald-500/10 text-emerald-400 border-emerald-500/30">Resolved</Badge>;
      default:
        return <Badge variant="secondary" className="text-xs">Closed</Badge>;
    }
  };

  const getPriorityBadge = (priority) => {
    const item = PRIORITIES.find((p) => p.value === priority) || PRIORITIES[1];
    return <Badge variant="outline" className={`text-[10px] font-semibold uppercase ${item.color}`}>{item.label}</Badge>;
  };

  return (
    <main className="max-w-6xl mx-auto space-y-8 p-4 md:p-8">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight">Support & Complaints</h1>
            {summary && summary.total > 0 && (
              <Badge variant="secondary" className="font-mono">
                {summary.total}
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Submit issues, report exchange anomalies, and track resolution status with support.
          </p>
        </div>

        <div>
          <Button
            size="sm"
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5"
            id="create-complaint-btn"
          >
            <Plus className="w-4 h-4" />
            <span>New Ticket</span>
          </Button>
        </div>
      </header>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="p-4 bg-card/60">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Total Tickets</span>
            <HelpCircle className="w-4 h-4 text-muted-foreground" />
          </div>
          <p className="text-2xl font-bold font-mono mt-1">{summary?.total ?? 0}</p>
        </Card>
        <Card className="p-4 bg-card/60 border-sky-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs text-sky-400">Open</span>
            <FolderOpen className="w-4 h-4 text-sky-400" />
          </div>
          <p className="text-2xl font-bold font-mono mt-1 text-sky-400">{summary?.open ?? 0}</p>
        </Card>
        <Card className="p-4 bg-card/60 border-amber-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs text-amber-400">In Progress</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-bold font-mono mt-1 text-amber-400">{summary?.in_progress ?? 0}</p>
        </Card>
        <Card className="p-4 bg-card/60 border-emerald-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs text-emerald-400">Resolved</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold font-mono mt-1 text-emerald-400">{summary?.resolved ?? 0}</p>
        </Card>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3">
        {/* Status Tabs */}
        <div className="flex flex-wrap items-center gap-2">
          {["all", "open", "in_progress", "resolved", "closed"].map((tab) => (
            <button
              key={tab}
              onClick={() => setSelectedStatus(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors ${
                selectedStatus === tab
                  ? "bg-primary text-primary-foreground"
                  : "bg-card hover:bg-accent text-muted-foreground border"
              }`}
              id={`filter-${tab}`}
            >
              {tab.replace("_", " ")}
            </button>
          ))}
        </div>

        {/* Category Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground whitespace-nowrap">Category:</span>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="text-xs bg-card border rounded-md px-2 py-1 text-foreground"
          >
            <option value="all">All Categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-24 w-full rounded-xl" />
        </div>
      )}

      {/* Empty State */}
      {!isLoading && complaints && complaints.length === 0 && (
        <Card className="border-dashed bg-card/40">
          <CardContent className="p-12 text-center space-y-4">
            <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <HelpCircle className="w-6 h-6" />
            </div>
            <div className="space-y-1 max-w-sm mx-auto">
              <h3 className="text-lg font-semibold">No tickets found</h3>
              <p className="text-xs text-muted-foreground">
                {selectedStatus === "all" && selectedCategory === "all"
                  ? "You have not submitted any support complaints or tickets."
                  : "No tickets matching the current filter criteria."}
              </p>
            </div>
            <Button size="sm" onClick={() => setShowCreateModal(true)} className="gap-1.5">
              <Plus className="w-4 h-4" />
              <span>Submit Ticket</span>
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Complaints List */}
      {!isLoading && complaints && complaints.length > 0 && (
        <div className="space-y-3">
          {complaints.map((c) => (
            <Card
              key={c.id}
              className="transition-all hover:border-primary/40 bg-card/70 cursor-pointer"
              onClick={() => setActiveComplaintId(c.id)}
            >
              <CardContent className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs text-muted-foreground">#{c.id.slice(0, 8)}</span>
                    <h3 className="font-bold text-sm sm:text-base text-foreground truncate">{c.subject}</h3>
                    {getStatusBadge(c.status)}
                    {getPriorityBadge(c.priority)}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
                    <span className="flex items-center gap-1">
                      <Tag className="w-3 h-3" />
                      {c.category}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(c.created_at).toLocaleDateString()}
                    </span>
                    <span className="flex items-center gap-1 text-primary">
                      <MessageSquare className="w-3 h-3" />
                      {c.message_count} {c.message_count === 1 ? "message" : "messages"}
                    </span>
                  </div>
                  <p className="text-xs text-foreground/80 line-clamp-1 mt-1">{c.description}</p>
                </div>

                <div className="self-end sm:self-center">
                  <Button variant="outline" size="xs" className="gap-1 text-xs">
                    <span>View Thread</span>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Complaint Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-lg shadow-2xl border bg-card">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-lg font-bold flex items-center gap-1.5">
                  <HelpCircle className="w-4 h-4 text-primary" />
                  <span>Submit Support Ticket</span>
                </CardTitle>
                <CardDescription className="text-xs">
                  Describe your inquiry or issue and support staff will review and respond.
                </CardDescription>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-md"
              >
                <X className="w-4 h-4" />
              </button>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">Subject *</label>
                  <Input
                    required
                    placeholder="e.g. Binance exchange balance sync error"
                    value={subjectInput}
                    onChange={(e) => setSubjectInput(e.target.value)}
                    className="text-sm"
                    id="input-ticket-subject"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold">Category</label>
                    <select
                      value={categoryInput}
                      onChange={(e) => setCategoryInput(e.target.value)}
                      className="w-full text-xs bg-muted/30 border rounded-md p-2 text-foreground"
                    >
                      {CATEGORIES.map((cat) => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold">Priority</label>
                    <select
                      value={priorityInput}
                      onChange={(e) => setPriorityInput(e.target.value)}
                      className="w-full text-xs bg-muted/30 border rounded-md p-2 text-foreground"
                    >
                      {PRIORITIES.map((p) => (
                        <option key={p.value} value={p.value}>{p.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">Detailed Description *</label>
                  <textarea
                    required
                    rows={4}
                    placeholder="Please describe the steps to reproduce the issue, error messages, or details of your request..."
                    value={descriptionInput}
                    onChange={(e) => setDescriptionInput(e.target.value)}
                    className="w-full text-xs bg-muted/30 border rounded-md p-2.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    id="input-ticket-description"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button type="button" variant="outline" size="sm" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={isCreating || !subjectInput.trim() || !descriptionInput.trim()}>
                    {isCreating ? "Submitting…" : "Submit Ticket"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Ticket Conversation Thread Modal */}
      {activeComplaintId && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
          <Card className="w-full max-w-2xl shadow-2xl border bg-card my-8 flex flex-col max-h-[85vh]">
            <CardHeader className="flex flex-row items-start justify-between pb-3 border-b shrink-0">
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono text-xs text-muted-foreground">#{activeComplaintId.slice(0, 8)}</span>
                  <CardTitle className="text-lg font-bold">
                    {activeDetail ? activeDetail.subject : "Loading Ticket…"}
                  </CardTitle>
                  {activeDetail && getStatusBadge(activeDetail.status)}
                  {activeDetail && getPriorityBadge(activeDetail.priority)}
                </div>
                {activeDetail && (
                  <p className="text-xs text-muted-foreground">
                    Category: <span className="font-medium text-foreground">{activeDetail.category}</span> • Created on {new Date(activeDetail.created_at).toLocaleString()}
                  </p>
                )}
              </div>

              <button
                onClick={() => setActiveComplaintId(null)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </CardHeader>

            {/* Conversation Thread */}
            <CardContent className="space-y-4 p-4 overflow-y-auto flex-1">
              {isLoadingDetail && (
                <div className="space-y-3 p-4">
                  <Skeleton className="h-16 w-3/4 rounded-xl" />
                  <Skeleton className="h-16 w-3/4 ml-auto rounded-xl" />
                </div>
              )}

              {!isLoadingDetail && activeDetail && (
                <>
                  {/* Messages Timeline */}
                  <div className="space-y-3">
                    {activeDetail.messages.map((msg, idx) => {
                      const isStaff = msg.sender_role === "admin" || msg.sender_role === "support";

                      return (
                        <div
                          key={msg.id || idx}
                          className={`p-3.5 rounded-xl border text-xs leading-relaxed space-y-1.5 ${
                            isStaff
                              ? "bg-primary/10 border-primary/30 ml-4"
                              : "bg-muted/30 border-border mr-4"
                          }`}
                        >
                          <div className="flex items-center justify-between text-[11px]">
                            <div className="flex items-center gap-1.5 font-semibold">
                              {isStaff ? (
                                <>
                                  <ShieldCheck className="w-3.5 h-3.5 text-primary" />
                                  <span className="text-primary">Support Staff</span>
                                </>
                              ) : (
                                <>
                                  <UserIcon className="w-3.5 h-3.5 text-muted-foreground" />
                                  <span>User</span>
                                </>
                              )}
                            </div>
                            <span className="text-muted-foreground font-mono text-[10px]">
                              {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {new Date(msg.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <p className="text-foreground/90 whitespace-pre-wrap">{msg.message}</p>
                        </div>
                      );
                    })}
                  </div>

                  {/* Resolution Notes Banner if resolved */}
                  {activeDetail.resolution_notes && (
                    <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs">
                      <span className="font-bold text-emerald-400 block mb-0.5">Resolution Notes:</span>
                      <p className="text-emerald-300/90">{activeDetail.resolution_notes}</p>
                    </div>
                  )}
                </>
              )}
            </CardContent>

            {/* Reply Footer */}
            {activeDetail && (
              <div className="p-4 border-t bg-card/50 space-y-3 shrink-0">
                <form onSubmit={handleSendReply} className="flex gap-2">
                  <Input
                    placeholder="Type your reply message..."
                    value={replyInput}
                    onChange={(e) => setReplyInput(e.target.value)}
                    className="text-xs"
                    id="input-ticket-reply"
                  />
                  <Button type="submit" size="sm" disabled={isSending || !replyInput.trim()} className="gap-1 px-3">
                    <Send className="w-3.5 h-3.5" />
                    <span>Send</span>
                  </Button>
                </form>

                <div className="flex items-center justify-between pt-1 text-xs">
                  <div className="flex items-center gap-2">
                    {activeDetail.status !== "resolved" && (
                      <Button
                        type="button"
                        variant="outline"
                        size="xs"
                        onClick={() => handleStatusChange("resolved")}
                        disabled={isUpdatingStatus}
                        className="text-emerald-400 hover:text-emerald-300"
                      >
                        <CheckCircle2 className="w-3 h-3 mr-1" />
                        Mark as Resolved
                      </Button>
                    )}
                    {activeDetail.status !== "closed" && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="xs"
                        onClick={() => handleStatusChange("closed")}
                        disabled={isUpdatingStatus}
                        className="text-muted-foreground"
                      >
                        Close Ticket
                      </Button>
                    )}
                  </div>

                  <Button variant="ghost" size="xs" onClick={() => setActiveComplaintId(null)}>
                    Done
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </div>
      )}
    </main>
  );
}
