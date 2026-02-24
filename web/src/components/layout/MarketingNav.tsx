import Link from "next/link";
import Image from "next/image";

export default function MarketingNav() {
  return (
    <nav className="border-b border-border bg-surface/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <Image
            src="/porkchop-logo.jpg"
            alt="PorkChop"
            width={32}
            height={32}
            className="rounded"
            unoptimized
          />
          <span className="text-xl font-bold text-accent">PorkChop</span>
        </Link>
        <div className="flex items-center gap-8">
          <Link
            href="/how-it-works"
            className="text-text-dim hover:text-text text-sm transition-colors"
          >
            How It Works
          </Link>
          <Link
            href="/about"
            className="text-text-dim hover:text-text text-sm transition-colors"
          >
            About
          </Link>
          <Link
            href="/dashboard"
            className="bg-accent text-bg px-4 py-2 rounded-lg text-sm font-semibold hover:bg-accent-dim hover:text-white transition-colors"
          >
            Launch App
          </Link>
        </div>
      </div>
    </nav>
  );
}
