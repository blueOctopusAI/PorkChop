"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Search } from "lucide-react";

export default function SearchInput({ defaultValue }: { defaultValue: string }) {
  const router = useRouter();
  const [query, setQuery] = useState(defaultValue);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-3 mb-6">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-dim" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search bills by title, subject, or summary..."
          className="w-full bg-surface border border-border text-text pl-10 pr-4 py-2.5 rounded-lg text-sm focus:outline-none focus:border-accent/50"
        />
      </div>
      <button
        type="submit"
        className="bg-accent text-bg px-5 py-2.5 rounded-lg text-sm font-semibold hover:bg-accent-dim hover:text-white transition-colors"
      >
        Search
      </button>
    </form>
  );
}
