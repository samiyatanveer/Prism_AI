import Link from "next/link";
import { ArrowRight, Bot, ChartNoAxesCombined, ChevronDown, LockKeyhole, ShieldCheck, Sparkles, WalletCards } from "lucide-react";
import { Button } from "@/components/ui/button";

const features = [
  { icon: Bot, title: "Ask in your own words", text: "Explore your portfolio and the market in English, Roman Urdu, or mixed language." },
  { icon: ChartNoAxesCombined, title: "Grounded analysis", text: "PrismAI pairs live market context with technical signals and clear uncertainty." },
  { icon: WalletCards, title: "One calm workspace", text: "Keep balances, watchlists, alerts, reports, and conversations in one focused view." },
];

const faqs = [
  ["Can PrismAI place trades?", "No. PrismAI is a read-only intelligence platform. It helps you understand your data; it does not execute trades."],
  ["Which exchange can I connect?", "Binance can be connected with the minimum read-only permissions needed to retrieve your permitted account data."],
  ["How is my exchange access handled?", "Exchange credentials are encrypted by the backend and are never exposed in the frontend or AI conversation."],
];

export default function HomePage() {
  return (
    <main className="min-h-screen overflow-hidden">
      <section className="prism-grid relative">
        <div className="absolute inset-x-0 top-0 h-px bg-white/10" />
        <header className="relative mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="group flex items-center gap-2.5" aria-label="PrismAI home">
            <span className="grid size-9 place-items-center rounded-xl bg-primary font-black text-primary-foreground shadow-lg shadow-primary/20 transition-transform group-hover:rotate-6">P</span>
            <span className="text-lg font-semibold tracking-tight">Prism<span className="text-primary">AI</span></span>
          </Link>
          <nav className="hidden items-center gap-7 text-sm text-muted-foreground md:flex" aria-label="Landing navigation">
            <a href="#how-it-works" className="transition-colors hover:text-foreground">How it works</a>
            <a href="#security" className="transition-colors hover:text-foreground">Security</a>
            <a href="#faq" className="transition-colors hover:text-foreground">FAQ</a>
          </nav>
          <Button asChild variant="outline" size="sm" className="border-white/15 bg-white/5 px-4"><Link href="/login">Sign in <ArrowRight className="size-3.5" /></Link></Button>
        </header>

        <div className="relative mx-auto grid max-w-7xl gap-14 px-5 pb-24 pt-14 sm:px-8 sm:pb-32 sm:pt-20 lg:grid-cols-[1.05fr_.95fr] lg:items-center lg:gap-16">
          <div className="max-w-2xl" style={{ animation: "prism-in .55s ease-out both" }}>
            <p className="prism-eyebrow"><Sparkles className="size-3.5" /> Intelligence, not noise</p>
            <h1 className="mt-6 text-5xl font-semibold leading-[1.03] tracking-[-0.045em] text-balance sm:text-6xl lg:text-7xl">Make your next crypto decision <span className="text-primary">clearer.</span></h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-muted-foreground sm:text-lg">PrismAI brings your connected portfolio, live market context, and AI-guided analysis into one private decision-support workspace.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg" className="h-11 rounded-xl px-5 font-semibold shadow-xl shadow-primary/20"><Link href="/login">Get Started <ArrowRight className="size-4" /></Link></Button>
              <Button asChild size="lg" variant="outline" className="h-11 rounded-xl border-white/15 bg-white/5 px-5"><a href="#how-it-works">How it works <ChevronDown className="size-4" /></a></Button>
            </div>
            <div className="mt-9 flex flex-wrap gap-x-6 gap-y-3 text-xs text-muted-foreground"><span className="inline-flex items-center gap-2"><ShieldCheck className="size-4 text-emerald-400" /> Read-only exchange access</span><span className="inline-flex items-center gap-2"><LockKeyhole className="size-4 text-primary" /> Private by design</span></div>
          </div>

          <div className="relative mx-auto w-full max-w-lg lg:max-w-none" style={{ animation: "prism-in .6s .12s ease-out both" }}>
            <div className="absolute -inset-10 rounded-full bg-primary/10 blur-3xl" />
            <div className="prism-surface relative overflow-hidden rounded-3xl p-4 sm:p-5">
              <div className="flex items-center justify-between border-b border-white/10 pb-4"><div className="flex items-center gap-2"><span className="size-2 rounded-full bg-emerald-400" /><span className="text-xs font-medium text-muted-foreground">PrismAI workspace</span></div><span className="rounded-full bg-primary/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-primary">Live context</span></div>
              <div className="mt-4 grid grid-cols-2 gap-3"><div className="rounded-2xl border border-white/10 bg-black/10 p-4"><p className="text-[11px] uppercase tracking-wider text-muted-foreground">Portfolio view</p><p className="mt-2 text-2xl font-semibold tracking-tight">In focus</p><div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/8"><div className="h-full w-3/4 rounded-full bg-emerald-400" /></div></div><div className="rounded-2xl border border-primary/20 bg-primary/8 p-4"><p className="text-[11px] uppercase tracking-wider text-muted-foreground">AI assessment</p><p className="mt-2 text-2xl font-semibold tracking-tight">Contextual</p><p className="mt-4 text-xs text-primary">Risk-aware insights</p></div></div>
              <div className="mt-3 rounded-2xl border border-white/10 bg-black/10 p-4"><div className="flex items-center justify-between"><p className="text-sm font-medium">Ask PrismAI</p><Bot className="size-4 text-primary" /></div><p className="mt-3 text-sm leading-6 text-muted-foreground">“I bought ETH higher. What context should I consider before I decide?”</p><div className="mt-4 flex items-center gap-2 border-t border-white/10 pt-3"><span className="size-6 rounded-full bg-primary/15" /><span className="text-xs text-muted-foreground">Analysis considers available market and portfolio context.</span></div></div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28"><div className="max-w-xl"><p className="prism-kicker">Built for deliberate decisions</p><h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">Everything you need to think with more signal.</h2></div><div className="mt-10 grid gap-4 md:grid-cols-3">{features.map(({ icon: Icon, title, text }) => <article key={title} className="prism-panel rounded-2xl p-6"><span className="grid size-10 place-items-center rounded-xl bg-primary/12 text-primary"><Icon className="size-5" /></span><h3 className="mt-5 text-lg font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-muted-foreground">{text}</p></article>)}</div></section>

      <section id="how-it-works" className="border-y border-white/10 bg-black/10"><div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28"><div className="grid gap-12 lg:grid-cols-[.8fr_1.2fr]"><div><p className="prism-kicker">A simple workflow</p><h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">From connection to a more informed next step.</h2><p className="mt-4 max-w-md text-sm leading-6 text-muted-foreground">The platform is designed to surface context, not to promise outcomes.</p></div><ol className="space-y-3">{[["01", "Connect securely", "Link Binance using restricted, read-only permissions."], ["02", "Bring the question", "Ask about holdings, an asset, a price level, or the broader market."], ["03", "Review the evidence", "See the analysis, indicators, risk context, and uncertainty in one place."]].map(([number, title, text]) => <li key={number} className="flex gap-5 rounded-2xl border border-white/10 bg-card/55 p-5"><span className="font-mono text-sm text-primary">{number}</span><div><h3 className="font-semibold">{title}</h3><p className="mt-1 text-sm text-muted-foreground">{text}</p></div></li>)}</ol></div></div></section>

      <section id="security" className="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28"><div className="prism-hero grid gap-8 p-7 sm:p-10 lg:grid-cols-[1.1fr_.9fr] lg:items-center"><div><p className="prism-kicker">Security is foundational</p><h2 className="mt-3 text-3xl font-semibold tracking-tight">Your data is for insight—not exposure.</h2><p className="mt-4 max-w-xl text-sm leading-6 text-muted-foreground">PrismAI is built around read-only access, encrypted exchange credentials, short-lived access tokens, and clear boundaries around what the AI can use.</p></div><div className="grid gap-3 sm:grid-cols-2"><div className="rounded-2xl border border-white/10 bg-black/15 p-4"><LockKeyhole className="size-5 text-primary" /><p className="mt-3 text-sm font-medium">Credentials stay protected</p><p className="mt-1 text-xs leading-5 text-muted-foreground">They are never returned to the frontend.</p></div><div className="rounded-2xl border border-white/10 bg-black/15 p-4"><ShieldCheck className="size-5 text-emerald-400" /><p className="mt-3 text-sm font-medium">Read-only by default</p><p className="mt-1 text-xs leading-5 text-muted-foreground">No automated trading in this workspace.</p></div></div></div></section>

      <section id="faq" className="mx-auto max-w-4xl px-5 pb-24 sm:px-8 sm:pb-32"><div className="text-center"><p className="prism-kicker">FAQ</p><h2 className="mt-3 text-3xl font-semibold tracking-tight">A few useful details.</h2></div><div className="mt-10 divide-y divide-white/10 rounded-2xl border border-white/10 bg-card/55 px-5">{faqs.map(([question, answer]) => <details key={question} className="group py-5"><summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-medium">{question}<ChevronDown className="size-4 text-primary transition-transform group-open:rotate-180" /></summary><p className="max-w-2xl pt-3 text-sm leading-6 text-muted-foreground">{answer}</p></details>)}</div><div className="mt-10 text-center"><Button asChild size="lg" className="rounded-xl px-5"><Link href="/login">Start with PrismAI <ArrowRight className="size-4" /></Link></Button></div></section>
      <footer className="border-t border-white/10 px-5 py-8 text-center text-xs text-muted-foreground">© {new Date().getFullYear()} PrismAI · AI-powered crypto intelligence</footer>
    </main>
  );
}
