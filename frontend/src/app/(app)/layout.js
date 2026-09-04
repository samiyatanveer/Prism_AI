"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, Bot, ChartNoAxesCombined, CircleUserRound, LayoutDashboard, ListChecks, WalletCards } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";

const navigation = [
  ["/dashboard", "Overview", LayoutDashboard],
  ["/assistant", "Assistant", Bot],
  ["/portfolio", "Portfolio", WalletCards],
  ["/watchlists", "Watchlists", ListChecks],
  ["/analyses", "Reports", ChartNoAxesCombined],
  ["/alerts", "Alerts", Bell],
];

export default function AppLayout({ children }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isHydrating, user } = useAuthStore();

  useEffect(() => {
    if (!isHydrating && !isAuthenticated) router.replace("/login");
  }, [isAuthenticated, isHydrating, router]);

  if (isHydrating) {
    return <main className="grid min-h-screen place-items-center"><div className="prism-loader" aria-label="Restoring your secure session" /></main>;
  }
  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen pb-20 sm:pb-0">
      <header className="sticky top-0 z-30 border-b border-white/10 bg-background/78 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-10">
          <Link href="/dashboard" className="group flex items-center gap-2" aria-label="PrismAI dashboard">
            <span className="grid size-8 place-items-center rounded-xl bg-primary text-sm font-black text-primary-foreground shadow-lg shadow-primary/30 transition-transform duration-200 group-hover:rotate-6">P</span>
            <span className="font-semibold tracking-tight">Prism<span className="text-primary">AI</span></span>
          </Link>
          <nav className="hidden items-center gap-0.5 lg:flex" aria-label="Primary navigation">
            {navigation.map(([href, label, Icon]) => <NavLink key={href} href={href} label={label} Icon={Icon} active={pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`))} />)}
          </nav>
          <Link href="/profile" className="flex items-center gap-2 rounded-xl px-2 py-1.5 text-sm transition-colors hover:bg-white/8" aria-label="Open profile and security settings">
            <span className="hidden max-w-28 truncate sm:block">{user?.full_name || user?.email}</span><CircleUserRound className="size-5 text-muted-foreground" />
          </Link>
        </div>
      </header>
      {children}
      <nav className="fixed inset-x-3 bottom-3 z-40 grid grid-cols-5 rounded-2xl border border-white/10 bg-card/95 p-1 shadow-2xl backdrop-blur-xl lg:hidden" aria-label="Mobile navigation">
        {navigation.slice(0, 5).map(([href, label, Icon]) => <NavLink key={href} href={href} label={label} Icon={Icon} active={pathname === href || pathname.startsWith(`${href}/`)} compact />)}
      </nav>
    </div>
  );
}

function NavLink({ href, label, Icon, active, compact = false }) {
  return <Link href={href} className={`flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-xs font-medium transition-all ${active ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25" : "text-muted-foreground hover:bg-white/8 hover:text-foreground"}`}><Icon className="size-4" /><span className={compact ? "sr-only" : ""}>{label}</span></Link>;
}
