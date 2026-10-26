import type { IncomingMessage, ServerResponse } from 'node:http';
import { defineConfig, loadEnv, type Connect, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { handleArticles, type ArticlesEnv } from './server/articles';

/** Serves /api/articles during `npm run dev` / `npm run preview`, reading BRAVE_API_KEY from .env.local. */
function articlesApi(env: ArticlesEnv): Plugin {
  const middleware: Connect.NextHandleFunction = async (req: IncomingMessage, res: ServerResponse) => {
    const chunks: Buffer[] = [];
    for await (const c of req) chunks.push(c as Buffer);
    const request = new Request(`http://localhost${req.url ?? ''}`, {
      method: req.method,
      headers: Object.entries(req.headers).flatMap(([k, v]) => (typeof v === 'string' ? [[k, v] as [string, string]] : [])),
      body: chunks.length && req.method !== 'GET' && req.method !== 'HEAD' ? Buffer.concat(chunks) : undefined,
    });
    const response = await handleArticles(request, env);
    res.statusCode = response.status;
    response.headers.forEach((v, k) => res.setHeader(k, v));
    res.end(Buffer.from(await response.arrayBuffer()));
  };
  return {
    name: 'articles-api',
    configureServer: (server) => void server.middlewares.use('/api/articles', middleware),
    configurePreviewServer: (server) => void server.middlewares.use('/api/articles', middleware),
  };
}

export default defineConfig(({ mode }) => {
  // Load all variables (not only VITE_*) for the server side; only VITE_* ones ever reach the browser.
  const env = loadEnv(mode, process.cwd(), '');
  return {
    plugins: [react(), articlesApi({ BRAVE_API_KEY: env.BRAVE_API_KEY, ALLOWED_ORIGINS: env.ALLOWED_ORIGINS })],
  };
});
