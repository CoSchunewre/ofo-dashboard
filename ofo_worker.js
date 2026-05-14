/**
 * OFO Dashboard - Cloudflare Worker Proxy
 * Uses Cloudflare Browser Rendering API for JS-rendered pages
 * For static HTML pages, falls back to regular fetch
 */

const ALLOWED_DOMAINS = [
  'pipeline2.kindermorgan.com',
  'peplmessenger.energytransfer.com',
  'ebb.anrpl.com',
  'infopost.enbridge.com',
  'pipeline.tallgrassenergylp.com',
  'csi.southernstar.com',
  'dtmidstream.trellisenergy.com',
  'ebb.tceconnects.com',
  'northernnaturalgas.com',
  'www.northernnaturalgas.com',
];

// Pipelines that require JS rendering (dynamic content)
const JS_RENDERED = [
  'pipeline2.kindermorgan.com',
  'pipeline.tallgrassenergylp.com',
  'peplmessenger.energytransfer.com',
  'csi.southernstar.com',
  'dtmidstream.trellisenergy.com',
  'ebb.tceconnects.com',
  'infopost.enbridge.com',
];

export default {
  async fetch(request, env, ctx) {

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    if (request.method !== 'GET') {
      return new Response('Method not allowed', { status: 405, headers: corsHeaders() });
    }

    const incoming = new URL(request.url);
    const targetUrl = incoming.searchParams.get('url');

    if (!targetUrl) {
      return new Response('Missing ?url= parameter', { status: 400, headers: corsHeaders() });
    }

    let parsedTarget;
    try {
      parsedTarget = new URL(targetUrl);
    } catch (e) {
      return new Response('Invalid URL', { status: 400, headers: corsHeaders() });
    }

    const hostname = parsedTarget.hostname;
    const isAllowed = ALLOWED_DOMAINS.some(d => hostname === d || hostname.endsWith('.' + d));

    if (!isAllowed) {
      return new Response(`Domain not allowed: ${hostname}`, { status: 403, headers: corsHeaders() });
    }

    const needsBrowser = JS_RENDERED.some(d => hostname === d || hostname.endsWith('.' + d));

    // ── Browser Rendering for JS-heavy pages ──
    if (needsBrowser && env.BROWSER) {
      try {
        const browser = await env.BROWSER.fetch(targetUrl, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
          },
          waitUntil: 'networkidle0',
        });
        const html = await browser.text();
        return new Response(html, {
          status: 200,
          headers: { ...corsHeaders(), 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'public, max-age=300' },
        });
      } catch (err) {
        // Fall through to regular fetch if browser rendering fails
      }
    }

    // ── Regular fetch fallback ──
    try {
      const response = await fetch(targetUrl, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.9',
          'Cache-Control': 'no-cache',
          'Sec-Fetch-Dest': 'document',
          'Sec-Fetch-Mode': 'navigate',
          'Sec-Fetch-Site': 'none',
          'Upgrade-Insecure-Requests': '1',
        },
        redirect: 'follow',
      });

      const html = await response.text();

      return new Response(html, {
        status: response.status,
        headers: {
          ...corsHeaders(),
          'Content-Type': 'text/html; charset=utf-8',
          'Cache-Control': 'public, max-age=300',
        },
      });

    } catch (err) {
      return new Response(`Fetch failed: ${err.message}`, {
        status: 502,
        headers: corsHeaders(),
      });
    }
  },
};

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}
