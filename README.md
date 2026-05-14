# ofo-dashboard

Live dashboard that aggregates Operational Flow Order notices from 9 natural gas pipeline EBBs into one view. Live at https://coschunewre.github.io/ofo-dashboard/.

## Files

- `index.html` — the dashboard. Static HTML + client-side JS that fetches each EBB through the Cloudflare Worker, parses notices, and renders status cards.
- `ofo_worker.js` — Cloudflare Worker source for the `ofo-proxy` CORS proxy.

## Deploy

**`index.html` deploys automatically.** Push to `main` → GitHub Pages rebuilds in 5–60 seconds.

**`ofo_worker.js` does NOT auto-deploy.** This file is the version-controlled source of truth, but the live Worker is deployed manually:

1. Open the Cloudflare dashboard → Workers & Pages → `ofo-proxy` → Edit code
2. Paste the contents of `ofo_worker.js`
3. Save and Deploy

If you change `ofo_worker.js` and only push to GitHub, the live site will keep running the old Worker.
