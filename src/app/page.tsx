import Link from "next/link";
import { formatDate, formatShortDate } from "@/lib/format";
import { getSessions, getProjects, getDailyLogs } from "@/lib/data";

export default async function Home() {
  const [sessions, projects, dailyLogs] = await Promise.all([
    getSessions(),
    getProjects(),
    getDailyLogs(),
  ]);

  const totalMessages = sessions.reduce((a, s) => a + s.message_count, 0);
  const recentSessions = sessions.slice(0, 8);

  return (
    <main className="max-w-5xl mx-auto px-6 py-8">
      {/* Stats */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        {[
          { label: "Sessions", value: sessions.length, color: "var(--accent)" },
          { label: "Messages", value: totalMessages.toLocaleString(), color: "var(--gold)" },
          { label: "Projects", value: projects.length, color: "var(--accent)" },
          { label: "Days", value: dailyLogs.length, color: "var(--gold)" },
        ].map((stat) => (
          <div
            key={stat.label}
            style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
            className="rounded-xl p-5"
          >
            <div className="text-3xl font-bold" style={{ color: stat.color }}>
              {stat.value}
            </div>
            <div className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
              {stat.label}
            </div>
          </div>
        ))}
      </section>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Projects */}
        <section>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span style={{ color: "var(--accent)" }}>📁</span> Projects
          </h2>
          <div className="space-y-2">
            {projects.filter(p => p.name !== "Greetings & Casual").map((project) => (
              <Link
                key={project.name}
                href={`/projects/${encodeURIComponent(project.name)}`}
                style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
                className="block rounded-lg px-4 py-3 transition-colors hover:border-[var(--accent)]"
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">{project.emoji}</span>
                  <span className="font-medium">{project.name}</span>
                  <span className="text-xs ml-auto" style={{ color: "var(--text-muted)" }}>
                    {project.session_count} session{project.session_count !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                  {project.description}
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* Recent Sessions */}
        <section>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span style={{ color: "var(--gold)" }}>◆</span> Recent Sessions
          </h2>
          <div className="space-y-2">
            {recentSessions.map((session) => {
              const title = session.auto_title || session.title || "(untitled)";
              return (
                <Link
                  key={session.id}
                  href={`/sessions/${session.id}`}
                  style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
                  className="block rounded-lg px-4 py-3 transition-colors hover:border-[var(--gold)]"
                >
                  <div className="font-medium truncate">{title}</div>
                  {session.summary && (
                    <div className="text-xs mt-1 line-clamp-2" style={{ color: "var(--text-muted)" }}>
                      {session.summary}
                    </div>
                  )}
                  <div
                    className="text-sm mt-1.5 flex items-center gap-3"
                    style={{ color: "var(--text-muted)" }}
                  >
                    <span>{formatDate(session.started_at)}</span>
                    <span>{session.message_count} msg{session.message_count !== 1 ? "s" : ""}</span>
                    <span
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
                    >
                      {session.project}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      </div>

      {/* Recent Days */}
      <section className="mt-10">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <span style={{ color: "var(--accent)" }}>📅</span> Recent Days
        </h2>
        <div className="space-y-2">
          {dailyLogs.slice(0, 7).map((log) => (
            <Link
              key={log.date}
              href={`/daily/${log.date}`}
              style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
              className="flex items-center justify-between rounded-lg px-4 py-3 transition-colors hover:border-[var(--accent)]"
            >
              <div>
                <span className="font-medium">{formatShortDate(log.date)}</span>
                <div className="text-sm mt-1 flex gap-2 flex-wrap" style={{ color: "var(--text-muted)" }}>
                  {log.projects.map((p) => (
                    <span
                      key={p}
                      style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
                      className="text-xs px-2 py-0.5 rounded-full"
                    >
                      {p}
                    </span>
                  ))}
                </div>
              </div>
              <span className="text-sm" style={{ color: "var(--text-muted)" }}>
                {log.session_count} session{log.session_count !== 1 ? "s" : ""}
              </span>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
