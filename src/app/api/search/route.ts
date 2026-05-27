import { NextRequest, NextResponse } from "next/server";
import { searchAll } from "@/lib/data";

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q") || "";
  if (!q.trim()) {
    return NextResponse.json({ results: [] });
  }
  const results = await searchAll(q);
  return NextResponse.json({ results, query: q });
}
