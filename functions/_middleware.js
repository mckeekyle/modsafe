// Cloudflare Pages Functions middleware: one canonical host (https://modsafe.app).
//
// www.modsafe.app and modsafe.pages.dev served the whole site with 200, so Google
// saw duplicate hosts ("Duplicate without user-selected canonical"). Those hosts now
// 301 to the same path + query on https://modsafe.app.
//
// Per-deployment / branch preview URLs (<hash>.modsafe.pages.dev, <branch>.modsafe.pages.dev)
// are NOT redirected, so previews stay usable; they get X-Robots-Tag: noindex instead.
//
// Which paths run this at all is set by dist/_routes.json (generated in src/build.py):
// polled feeds, API, badges and static assets are excluded to stay far below the free
// 100k Function requests/day.
export const CANONICAL_HOST = "modsafe.app";
const REDIRECT_HOSTS = new Set(["www.modsafe.app", "modsafe.pages.dev"]);
const PREVIEW_SUFFIX = ".modsafe.pages.dev";

export function canonicalRedirect(url) {
  const u = new URL(url);
  const host = u.hostname.toLowerCase();
  if (!REDIRECT_HOSTS.has(host)) return null;
  return `https://${CANONICAL_HOST}${u.pathname}${u.search}`;
}

export function isPreviewHost(url) {
  return new URL(url).hostname.toLowerCase().endsWith(PREVIEW_SUFFIX);
}

export async function onRequest(context) {
  const { request } = context;
  const target = canonicalRedirect(request.url);
  if (target) {
    return new Response(null, {
      status: 301,
      headers: { Location: target, "Cache-Control": "public, max-age=86400" },
    });
  }
  const response = await context.next();
  if (isPreviewHost(request.url)) {
    const r = new Response(response.body, response);
    r.headers.set("X-Robots-Tag", "noindex");
    return r;
  }
  return response;
}
