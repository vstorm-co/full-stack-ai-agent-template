import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import { requireAdmin } from "@/lib/admin-auth";

export async function GET(request: NextRequest) {
  try {
    const adminCheck = await requireAdmin(request);
    if ("error" in adminCheck) return adminCheck.error;
    const { accessToken } = adminCheck;

    const searchParams = request.nextUrl.searchParams;
    const rawFormat = searchParams.get("export_format");
    const export_format = rawFormat === "csv" || rawFormat === "json" ? rawFormat : "json";
    const ratingFilter = searchParams.get("rating_filter");
    const withCommentsOnly = searchParams.get("with_comments_only") === "true";

    let url = `/api/v1/admin/ratings/export?export_format=${export_format}`;
    if (ratingFilter) url += `&rating_filter=${encodeURIComponent(ratingFilter)}`;
    if (withCommentsOnly) url += `&with_comments_only=true`;

    const data = await backendFetch(url, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      raw: export_format === "csv",
    });

    const filename = `ratings_export_${new Date().toISOString().slice(0, 10)}.${export_format}`;

    if (export_format === "csv") {
      return new NextResponse(data as string, {
        headers: {
          "Content-Type": "text/csv",
          "Content-Disposition": `attachment; filename="${filename}"`,
        },
      });
    }

    return NextResponse.json(data, {
      headers: {
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        { detail: error.message || "Failed to export ratings" },
        { status: error.status },
      );
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
