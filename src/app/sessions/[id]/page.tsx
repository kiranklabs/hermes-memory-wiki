import Link from "next/link";
import { getSession, getProjects } from "@/lib/data";
import { notFound } from "next/navigation";
import { formatDate, formatTime } from "@/lib/format";

export default async function SessionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const session = await getSession(id);
  const projects = await getProjects();

  if (!session) notFound();

  const displayTitle = session.auto_title || session.title || "(untitled)";
  const project = projects.find((p) => p.name === session.project);

  return (
    <main className="max-w-4xl mx-auto px-6 py-8">
      {/* Header */}
      <div
        className="rounded-xl p-6 mb-8"
        style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-3 mb-3">
          {project && (
            <Link
              href={`/projects/${encodeURIComponent(project.name)}`}
              className="text-xs px-2.5 py-1 rounded-full font-medium"
              style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
            >
              {project.emoji} {project.name}
            </Link>
          )}
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            {formatDate(session.started_at)}
          </span>
        </div>

        <h1 className="text-2xl font-bold mb-1">{displayTitle}</h1>

        {session.auto_title && session.auto_title !== session.title && session.title && (
          <div className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
            Original: {session.title}
          </div>
        )}

        {/* Narrative Summary */}
        {session.summary && (
          <p
            className="text-sm leading-relaxed mt-3"
            style={{ color: "var(--text)" }}
          >
            {session.summary}
          </p>
        )}

        {/* Stats row */}
        <div className="flex flex-wrap gap-3 text-sm mt-4" style={{ color: "var(--text-muted)" }}>
          <span>{"💬"} {session.message_count} messages</span>
          <span>{"🔧"} {session.tool_call_count} tool calls</span>
          <span className="capitalize">{"📡"} {session.source}</span>
          {session.input_tokens > 0 && (
            <span>{"⬆️"} {session.input_tokens.toLocaleString()} in</span>
          )}
          {session.output_tokens > 0 && (
            <span>{"⬇️"} {session.output_tokens.toLocaleString()} out</span>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="space-y-4">
        {session.messages.map((msg, i) => {
          const isUser = msg.role === "user";
          const isTool = msg.role === "tool";

          if (isTool) {
            return (
              <div
                key={i}
                className="rounded-lg px-4 py-2 text-sm font-mono"
                style={{
                  background: "rgba(244, 168, 51, 0.05)",
                  borderLeft: "3px solid var(--gold)",
                  color: "var(--text-muted)",
                }}
              >
                <span style={{ color: "var(--gold)" }}>{"⚙"} {msg.tool_name || "tool"}:</span>{" "}
                {msg.content.length > 300 ? msg.content.slice(0, 300) + "..." : msg.content}
              </div>
            );
          }

          return (
            <div
              key={i}
              className="rounded-xl p-5"
              style={{
                background: isUser ? "rgba(0, 200, 180, 0.08)" : "var(--surface)",
                border: isUser ? "1px solid var(--accent)" : "1px solid var(--border)",
              }}
            >
              <div className="flex items-center justify-between mb-3">
                <span
                  className="text-sm font-semibold"
                  style={{ color: isUser ? "var(--accent)" : "var(--gold)" }}
                >
                  {isUser ? "👤 You" : "🦉 Agent"}
                </span>
                {msg.timestamp && (
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {formatTime(msg.timestamp)}
                  </span>
                )}
              </div>
              <div
                className="whitespace-pre-wrap text-sm leading-relaxed"
                style={{ color: "var(--text)" }}
              >
                {msg.content}
              </div>
            </div>
          );
        })}
      </div>
    </main>
  );
}
