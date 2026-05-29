"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { DailyLog, Project, CronJob } from "@/lib/data";
import { formatQuickDate } from "@/lib/format";

const CRON_CAT_LABELS: Record<string, string> = {
  auto_scan: "Auto Scan",
  backup: "Backup",
  priority_check: "Priority Check",
  other: "Other",
};

interface SidebarProps {
  dailyLogs: DailyLog[];
  projects: Project[];
  cronJobs: CronJob[];
}

export default function Sidebar({ dailyLogs, projects, cronJobs }: SidebarProps) {
  const pathname = usePathname();
  const [expandedDates, setExpandedDates] = useState<Set<string>>(new Set());
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());
  const [expandedCron, setExpandedCron] = useState<Set<string>>(new Set());

  const toggleDate = (date: string) => {
    setExpandedDates((prev) => {
      const next = new Set(prev);
      if (next.has(date)) next.delete(date);
      else next.add(date);
      return next;
    });
  };

  const toggleProject = (name: string) => {
    setExpandedProjects((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const toggleCron = (cat: string) => {
    setExpandedCron((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  const sessionTitleCache: Record<string, string> = {};
  const sessionDateCache: Record<string, string> = {};
  for (const log of dailyLogs) {
    for (const s of log.sessions) {
      sessionTitleCache[s.id] = s.auto_title || s.title || "(untitled)";
      sessionDateCache[s.id] = s.started_at || "";
    }
  }

  // Group cron jobs by category
  const cronByCat: Record<string, CronJob[]> = {};
  for (const job of cronJobs) {
    const cat = job.category || "other";
    if (!cronByCat[cat]) cronByCat[cat] = [];
    cronByCat[cat].push(job);
  }

  return (
    <aside
      className="w-72 min-h-screen overflow-y-auto flex-shrink-0 border-r flex flex-col"
      style={{ background: "var(--bg)", borderColor: "var(--border)" }}
    >
      <div className="px-5 py-5 border-b flex-shrink-0" style={{ borderColor: "var(--border)" }}>
        <Link href="/" className="flex items-center gap-2">
          <span style={{ color: "var(--accent)" }} className="text-xl">{"⚡"}</span>
          <span className="font-bold text-lg">Hermes Memory Wiki</span>
        </Link>
      </div>

      <nav className="py-3 px-3 flex-1 overflow-y-auto">
        {/* Home */}
        <Link
          href="/"
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
          style={{
            background: pathname === "/" ? "var(--accent-dim)" : "transparent",
            color: pathname === "/" ? "var(--accent)" : "var(--text)",
          }}
        >
          <span>{"🏠"}</span> Overview
        </Link>

        <div className="my-3 border-t" style={{ borderColor: "var(--border)" }} />

        {/* Facts */}
        <Link
          href="/facts"
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
          style={{
            background: pathname === "/facts" ? "var(--accent-dim)" : "transparent",
            color: pathname === "/facts" ? "var(--accent)" : "var(--text)",
          }}
        >
          <span>{"📋"}</span> Facts
        </Link>

        {/* Decisions */}
        <Link
          href="/decisions"
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
          style={{
            background: pathname === "/decisions" ? "var(--accent-dim)" : "transparent",
            color: pathname === "/decisions" ? "var(--accent)" : "var(--text)",
          }}
        >
          <span>{"⚖️"}</span> Decisions
        </Link>

        <div className="my-3 border-t" style={{ borderColor: "var(--border)" }} />

        {/* Projects Tree */}
        <div className="mb-4">
          <div
            className="text-xs font-semibold uppercase tracking-wider px-3 mb-2"
            style={{ color: "var(--text-muted)" }}
          >
            {"📁"} Projects
          </div>
          <div className="space-y-0.5">
            {projects.map((project) => {
              const isExpanded = expandedProjects.has(project.name);
              const isActive = pathname === `/projects/${encodeURIComponent(project.name)}`;
              return (
                <div key={project.name}>
                  <button
                    onClick={() => toggleProject(project.name)}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors text-left"
                    style={{
                      background: isActive ? "var(--accent-dim)" : "transparent",
                      color: isActive ? "var(--accent)" : "var(--text)",
                    }}
                  >
                    <span
                      className="text-xs transition-transform"
                      style={{
                        color: "var(--text-muted)",
                        transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)",
                      }}
                    >
                      {"▶"}
                    </span>
                    <span className="text-base">{project.emoji}</span>
                    <span className="flex-1 truncate font-medium">{project.name}</span>
                    <span
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{ background: "var(--surface)", color: "var(--text-muted)" }}
                    >
                      {project.session_count}
                    </span>
                  </button>
                  {isExpanded && (
                    <div className="ml-5 pl-3 border-l space-y-0.5 mt-0.5" style={{ borderColor: "var(--border)" }}>
                      {[...project.sessions]
                        .sort((a, b) => {
                          const dateA = sessionDateCache[a] || "";
                          const dateB = sessionDateCache[b] || "";
                          return dateB.localeCompare(dateA);
                        })
                        .slice(0, 10)
                        .map((sid) => {
                        const sessionTitle = sessionTitleCache[sid] || sid;
                        const isActiveSession = pathname === `/sessions/${sid}`;
                        return (
                          <Link
                            key={sid}
                            href={`/sessions/${sid}`}
                            className="block px-2 py-1.5 rounded text-xs truncate transition-colors"
                            style={{
                              background: isActiveSession ? "var(--accent-dim)" : "transparent",
                              color: isActiveSession ? "var(--accent)" : "var(--text-muted)",
                            }}
                            title={sessionTitle}
                          >
                            {sessionTitle}
                          </Link>
                        );
                      })}
                      {project.sessions.length > 10 && (
                        <Link
                          href={`/projects/${encodeURIComponent(project.name)}`}
                          className="block px-2 py-1.5 rounded text-xs"
                          style={{ color: "var(--accent)" }}
                        >
                          +{project.sessions.length - 10} more →
                        </Link>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="my-3 border-t" style={{ borderColor: "var(--border)" }} />

        {/* Daily Logs Tree */}
        <div className="mb-4">
          <div
            className="text-xs font-semibold uppercase tracking-wider px-3 mb-2"
            style={{ color: "var(--text-muted)" }}
          >
            {"📅"} Timeline
          </div>
          <div className="space-y-0.5">
            {dailyLogs.map((log) => {
              const isExpanded = expandedDates.has(log.date);
              const isActive = pathname === `/daily/${log.date}`;
              return (
                <div key={log.date}>
                  <button
                    onClick={() => toggleDate(log.date)}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors text-left"
                    style={{
                      background: isActive ? "var(--accent-dim)" : "transparent",
                      color: isActive ? "var(--accent)" : "var(--text)",
                    }}
                  >
                    <span
                      className="text-xs transition-transform"
                      style={{
                        color: "var(--text-muted)",
                        transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)",
                      }}
                    >
                      {"▶"}
                    </span>
                    <span className="flex-1 truncate font-medium">{formatQuickDate(log.date)}</span>
                    <span
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{ background: "var(--surface)", color: "var(--text-muted)" }}
                    >
                      {log.session_count}
                    </span>
                  </button>
                  {isExpanded && (
                    <div className="ml-5 pl-3 border-l space-y-0.5 mt-0.5" style={{ borderColor: "var(--border)" }}>
                      {[...log.sessions]
                        .sort((a, b) => {
                          const dateA = a.started_at || "";
                          const dateB = b.started_at || "";
                          return dateB.localeCompare(dateA);
                        })
                        .map((s) => {
                        const sessionTitle = s.auto_title || s.title || "(untitled)";
                        const isActiveSession = pathname === `/sessions/${s.id}`;
                        return (
                          <Link
                            key={s.id}
                            href={`/sessions/${s.id}`}
                            className="block px-2 py-1.5 rounded text-xs truncate transition-colors"
                            style={{
                              background: isActiveSession ? "var(--accent-dim)" : "transparent",
                              color: isActiveSession ? "var(--accent)" : "var(--text-muted)",
                            }}
                            title={sessionTitle}
                          >
                            <span style={{ color: "var(--text-muted)" }} className="mr-1">
                              {"•"}
                            </span>
                            {sessionTitle}
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="my-3 border-t" style={{ borderColor: "var(--border)" }} />

        {/* Cron Jobs — at the very bottom */}
        <div>
          <div
            className="text-xs font-semibold uppercase tracking-wider px-3 mb-2"
            style={{ color: "var(--text-muted)" }}
          >
            {"⚙️"} Cron Jobs
          </div>
          <div className="space-y-0.5">
            {Object.entries(cronByCat).map(([cat, jobs]) => {
              const isExpanded = expandedCron.has(cat);
              return (
                <div key={cat}>
                  <button
                    onClick={() => toggleCron(cat)}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors text-left"
                    style={{ color: "var(--text)" }}
                  >
                    <span
                      className="text-xs transition-transform"
                      style={{
                        color: "var(--text-muted)",
                        transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)",
                      }}
                    >
                      {"▶"}
                    </span>
                    <span className="flex-1 truncate font-medium">
                      {CRON_CAT_LABELS[cat] || cat}
                    </span>
                    <span
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{ background: "var(--surface)", color: "var(--text-muted)" }}
                    >
                      {jobs.length}
                    </span>
                  </button>
                  {isExpanded && (
                    <div className="ml-5 pl-3 border-l space-y-0.5 mt-0.5" style={{ borderColor: "var(--border)" }}>
                      {jobs.slice(0, 10).map((job) => (
                        <div
                          key={job.id}
                          className="px-2 py-1.5 rounded text-xs truncate"
                          style={{ color: "var(--text-muted)" }}
                          title={job.title}
                        >
                          {job.title.length > 30 ? job.title.slice(0, 30) + "..." : job.title}
                          <span className="ml-1 text-xs" style={{ color: "var(--text-muted)", opacity: 0.6 }}>
                            {job.date || ""}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </nav>
    </aside>
  );
}
