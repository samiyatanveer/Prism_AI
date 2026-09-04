export default function AppLoading() {
  return (
    <main className="prism-page" aria-label="Loading workspace" aria-busy="true">
      <div className="h-7 w-52 animate-pulse rounded-lg bg-muted" />
      <div className="grid gap-4 md:grid-cols-3">
        {[1, 2, 3].map((item) => <div key={item} className="h-32 animate-pulse rounded-2xl border border-white/10 bg-card/60" />)}
      </div>
      <div className="grid gap-5 lg:grid-cols-2"><div className="h-72 animate-pulse rounded-2xl border border-white/10 bg-card/60" /><div className="h-72 animate-pulse rounded-2xl border border-white/10 bg-card/60" /></div>
    </main>
  );
}
