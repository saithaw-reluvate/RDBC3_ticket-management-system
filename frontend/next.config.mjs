const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN || "http://localhost:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Step 5: the frontend Docker image copies only .next/standalone into the
  // runtime stage (docs/DEPLOYMENT.md), so it needs the self-contained
  // server.js build output rather than a full node_modules install.
  output: "standalone",
  // Without this, Next.js's own trailing-slash normalization redirects
  // /api/tickets/ -> /api/tickets BEFORE the rewrite below runs, stripping
  // the slash Django's URLconf requires. Rewritten /api/* paths must reach
  // Django exactly as the browser sent them.
  skipTrailingSlashRedirect: true,
  async headers() {
    // The access token lives in the URL path — never leak it via Referer.
    // Matches /track/[token] and, as a harmless superset, /track/link too.
    return [
      {
        source: "/track/:path*",
        headers: [{ key: "Referrer-Policy", value: "no-referrer" }],
      },
    ];
  },
  async rewrites() {
    // Browser-origin proxy per docs/ARCHITECTURE.md Decision 3 — the browser
    // only ever talks to the Next.js origin. Server Components must NOT use
    // this; they call BACKEND_ORIGIN directly (see lib/api.ts).
    //
    // :path(.*) (a raw regex capture) rather than :path* — the segment-array
    // form (:path*) drops a trailing slash when reconstructing the
    // destination, and Django's URLconf (and APPEND_SLASH for POST) requires
    // the exact slash the browser sent.
    return [
      {
        source: "/api/:path(.*)",
        destination: `${BACKEND_ORIGIN}/api/:path`,
      },
    ];
  },
};

export default nextConfig;
