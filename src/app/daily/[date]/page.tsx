import Link from "next/link";
import { getDailyLog } from "@/lib/data";
import { notFound } from "next/navigation";
import { formatDate } from "@/lib/format";

export default async function DailyLogPage({
  params,
}: {
  params: Promise<{ date: string }>;
}) {
  const { date } = await params;
  const log = await getDailyLog(date);

  if (!log) notFound();

  return (
    <main className="max-w-4xl mx-auto px-6 py-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold">
          📅{" "}
          {new Date(date + "T00:00:00Z").toLocaleDateString("en-CA", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
          })}
        </h1>
        <p className="mt-2" style={{ color: "var(--text-muted)" }}>
          {log.session_count} session{log.session_count !== 1 ? "s" : ""} across{" "}
          {log.projects.length} project{log.projects.length !== 1 ? "s" : ""}
        </p>
        {log.projects.length > 0 && (
          <div className="flex gap-2 mt-3 flex-wrap">
            {log.projects.map((p) => (
              <Link
                key={p}
                href={`/projects/${encodeURIComponent(p)}`}
                style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
                className="text-xs px-2 py-0.5 rounded-full"
              >
                {p}
              </Link>
            ))}
          </div>
        )}
      </header>

      <div className="space-y-6">
        {log.sessions.map((session) => {
          const displayTitle = session.auto_title || session.title || "(untitled)";
          return (
            <div
              key={session.id}
              style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
              className="rounded-xl overflow-hidden"
            >
              <Link
                href={`/sessions/${session.id}`}
                className="block p-5 transition-colors hover:bg-[rgba(0,200,180,0.05)]"
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-lg">{displayTitle}</h3>
                  <span className="text-sm" style={{ color: "var(--text-muted)" }}>
                    {session.message_count} msg{session.message_count !== 1 ? "s" : ""}
                  </span>
                </div>
                {session.summary && (
                  <p className="text-sm mt-2 leading-relaxed" style={{ color: "var(--text-muted)" }}>
                    {session.summary}
                  </p>
                )}
                <div
                  className="text-sm mt-2 flex items-center gap-3"
                  style={{ color: "var(--text-muted)" }}
                >
                  <span>{formatDate(session.started_at)}</span>
                  <span className="capitalize">{session.source}</span>
                  <span>{session.tool_call_count} tool calls</span>
                  <span
                    className="text-xs px-1.5 py-0.5 rounded"
                    style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
                  >
                    {session.project}
                  </span>
                </div>
              </Link>

              <div
                className="px-5 pb-5 space-y-3 border-t"
                style={{ borderColor: "var(--border)" }}
              >
                {session.messages.map((msg, i) => {
                  const isUser = msg.role === "user";
                  if (msg.role === "tool") return null;
                  return (
                    <div
                      key={i}
                      className="rounded-lg px-4 py-3 mt-3"
                      style={{
                        background: isUser
                          ? "rgba(0, 200, 180, 0.06)"
                          : "rgba(244, 168, 51, 0.04)",
                        borderLeft: `3px solid ${isUser ? "var(--accent)" : "var(--gold)"}`,
                      }}
                    >
                      <span
                        className="text-xs font-semibold"
                        style={{ color: isUser ? "var(--accent)" : "var(--gold)" }}
                      >
                        {isUser ? "👤" : "🦉"}
                      </span>{" "}
                      <span className="text-sm whitespace-pre-wrap" style={{ color: "var(--text)" }}>
                        {msg.content.length > 500
                          ? msg.content.slice(0, 500) + "…"
                          : msg.content}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </main>
  );
}
