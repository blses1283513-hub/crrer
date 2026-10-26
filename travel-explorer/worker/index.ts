// Cloudflare Worker: serves the built app from ./dist and the /api/articles endpoint.
// Deploy with `npm run build && npx wrangler deploy` (see README).
import { handleArticles, type ArticlesEnv } from '../server/articles';

interface Env extends ArticlesEnv {
  ASSETS: Fetcher;
}

export default {
  async fetch(req, env) {
    if (new URL(req.url).pathname === '/api/articles') return handleArticles(req, env);
    return env.ASSETS.fetch(req);
  },
} satisfies ExportedHandler<Env>;
