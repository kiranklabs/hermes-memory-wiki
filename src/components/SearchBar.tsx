"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { SearchResult } from "@/lib/data";

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => {
    setOpen(false);
    setQuery("");
  }, [pathname]);

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      setResults(data.results || []);
      setOpen(true);
    } catch {
      setResults([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => doSearch(query), 250);
    return () => clearTimeout(timer);
  }, [query, doSearch]);

  return (
    <div ref={wrapperRef} className="relative w-full max-w-xl">
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4"
          style={{ color: "var(--text-muted)" }}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
          placeholder="Search sessions, projects, conversations…"
          className="w-full pl-10 pr-4 py-2.5 rounded-lg text-sm outline-none transition-colors"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            color: "var(--text)",
          }}
        />
        {loading && (
          <div
            className="absolute right-3 top-1/2 -translate-y-1/2 w-3 h-3 border-2 rounded-full animate-spin"
            style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
          />
        )}
      </div>

      {open && (
        <div
          className="absolute top-full left-0 right-0 mt-2 rounded-xl overflow-hidden z-50 max-h-[60vh] overflow-y-auto"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            boxShadow: "0 8px 30px rgba(0,0,0,0.4)",
          }}
        >
          {results.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm" style={{ color: "var(--text-muted)" }}>
              {query.trim() ? "No results found" : "Type to search…"}
            </div>
          ) : (
            results.map((r) => (
              <Link
                key={r.id}
                href={`/sessions/${r.id}`}
                onClick={() => { setOpen(false); setQuery(""); }}
                className="block px-4 py-3 transition-colors hover:bg-[rgba(0,200,180,0.08)] border-b"
                style={{ borderColor: "var(--border)" }}
              >
                <div className="font-medium text-sm truncate">{r.title}</div>
                {r.snippet && (
                  <div
                    className="text-xs mt-1 line-clamp-2"
                    style={{ color: "var(--text-muted)" }}
                  >
                    {r.snippet}
                  </div>
                )}
                <div className="flex items-center gap-2 mt-1.5">
                  {r.date && (
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {r.date}
                    </span>
                  )}
                  <span
                    className="text-xs capitalize px-1.5 py-0.5 rounded"
                    style={{
                      background: "var(--gold-dim)",
                      color: "var(--gold)",
                    }}
                  >
                    {r.source}
                  </span>
                  <span
                    className="text-xs px-1.5 py-0.5 rounded"
                    style={{
                      background: "var(--accent-dim)",
                      color: "var(--accent)",
                    }}
                  >
                    {r.project}
                  </span>
                </div>
              </Link>
            ))
          )}
        </div>
      )}
    </div>
  );
}
