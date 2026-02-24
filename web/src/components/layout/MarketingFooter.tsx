import Link from "next/link";

export default function MarketingFooter() {
  return (
    <footer className="border-t border-border mt-20 py-12 px-6">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
        <div>
          <span className="text-accent font-bold">PorkChop</span>
          <span className="text-text-dim text-sm ml-2">
            AI that reads the bills so you don&apos;t have to
          </span>
        </div>
        <div className="flex gap-6 text-sm text-text-dim">
          <Link href="/how-it-works" className="hover:text-text transition-colors">
            How It Works
          </Link>
          <Link href="/about" className="hover:text-text transition-colors">
            About
          </Link>
          <Link href="/dashboard" className="hover:text-text transition-colors">
            Dashboard
          </Link>
        </div>
      </div>
    </footer>
  );
}
