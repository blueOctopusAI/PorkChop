"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { LayoutDashboard, FileText, Search, PlusCircle, Settings } from "lucide-react";
import { useState } from "react";
import SettingsModal from "@/components/SettingsModal";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/bills", label: "Bills", icon: FileText },
  { href: "/process", label: "Analyze", icon: PlusCircle },
  { href: "/search", label: "Search", icon: Search },
];

export default function AppSidebar() {
  const pathname = usePathname();
  const [showSettings, setShowSettings] = useState(false);

  return (
    <>
      <aside className="w-60 border-r border-border bg-surface min-h-screen hidden md:flex flex-col fixed left-0 top-0">
        <div className="p-5 border-b border-border">
          <Link href="/" className="flex items-center gap-2.5">
            <Image
              src="/porkchop-logo.jpg"
              alt="PorkChop"
              width={28}
              height={28}
              className="rounded"
              unoptimized
            />
            <span className="text-xl font-bold text-accent">PorkChop</span>
          </Link>
          <p className="text-[11px] text-text-dim mt-1 ml-[38px]">AI Bill Analyzer</p>
        </div>
        <nav className="flex-1 py-4">
          {navItems.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-5 py-2.5 text-sm transition-colors ${
                  active
                    ? "text-accent bg-accent/10 border-r-2 border-accent"
                    : "text-text-dim hover:text-text hover:bg-surface-hover"
                }`}
              >
                <item.icon className="w-4 h-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-5 border-t border-border flex items-center justify-between">
          <Link
            href="/"
            className="text-xs text-text-dim hover:text-text transition-colors"
          >
            Back to Home
          </Link>
          <button
            onClick={() => setShowSettings(true)}
            className="text-text-dim hover:text-text transition-colors"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </aside>

      <SettingsModal
        open={showSettings}
        onClose={() => setShowSettings(false)}
      />
    </>
  );
}
