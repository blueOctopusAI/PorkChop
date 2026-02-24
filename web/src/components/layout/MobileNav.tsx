"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { LayoutDashboard, FileText, Search } from "lucide-react";

const navItems = [
  { href: "/dashboard", icon: LayoutDashboard },
  { href: "/bills", icon: FileText },
  { href: "/search", icon: Search },
];

export default function MobileNav() {
  const pathname = usePathname();

  return (
    <div className="md:hidden fixed top-0 left-0 right-0 z-50 bg-surface border-b border-border">
      <div className="flex items-center justify-between px-4 h-14">
        <Link href="/" className="flex items-center gap-2">
          <Image
            src="/porkchop-logo.jpg"
            alt="PorkChop"
            width={24}
            height={24}
            className="rounded"
            unoptimized
          />
          <span className="font-bold text-accent">PorkChop</span>
        </Link>
        <nav className="flex items-center gap-5">
          {navItems.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={active ? "text-accent" : "text-text-dim"}
              >
                <item.icon className="w-5 h-5" />
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
