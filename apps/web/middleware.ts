import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Known app page segments (second segment in /:orgSlug/:page URLs).
 */
const APP_PAGES = new Set([
  "dashboard",
  "invoices",
  "upload",
  "settings",
  "billing",
  "rules",
  "templates",
  "arhiviranje",
]);

const AUTH_ROUTES = ["/login", "/register", "/password-reset", "/invite"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isLoggedIn =
    request.cookies.get("saldora_logged_in")?.value === "true";

  // Check if path matches /:orgSlug/:page pattern (org-scoped app route)
  const segments = pathname.split("/").filter(Boolean);
  const isProtectedRoute =
    segments.length >= 2 && APP_PAGES.has(segments[1]);

  const isAuthRoute = AUTH_ROUTES.some((route) => pathname.startsWith(route));

  if (isProtectedRoute && !isLoggedIn) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (isAuthRoute && isLoggedIn && !pathname.startsWith("/register/organization")) {
    // Redirect to /app which will resolve to the correct orgSlug dashboard
    return NextResponse.redirect(new URL("/app", request.url));
  }

  // Logged-in user on landing page → redirect to /app
  if (pathname === "/" && isLoggedIn) {
    return NextResponse.redirect(new URL("/app", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except Next.js internals and static files.
     * The middleware checks the cookie and redirects as needed.
     */
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\.).*)",
  ],
};
