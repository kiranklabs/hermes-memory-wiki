import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import SearchBar from "@/components/SearchBar";
import { getDailyLogs, getProjects } from "@/lib/data";

export const metadata: Metadata = {
  title: "Memory Wiki",
  description: "A browsable, searchable memory layer for AI agent conversations",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [dailyLogs, projects] = await Promise.all([
    getDailyLogs(),
    getProjects(),
  ]);

  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex antialiased">
        <Sidebar dailyLogs={dailyLogs} projects={projects} />
        <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
          <header
            className="flex-shrink-0 px-6 py-4 border-b flex items-center gap-4"
            style={{ borderColor: "var(--border)", background: "var(--bg)" }}
          >
            <div className="flex-1 max-w-2xl">
              <SearchBar />
            </div>
          </header>
          <div className="flex-1 overflow-y-auto">{children}</div>
        </div>
      </body>
    </html>
  );
}
