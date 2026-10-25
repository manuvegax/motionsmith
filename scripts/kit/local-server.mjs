/* Loopback-only static server for one composition folder: same origin for WebGL textures,
   no paths outside the folder (symlinks included), ephemeral port, closed by the caller. Requests whose Host header is
   not this server are refused, so a web page in another browser cannot reach it through DNS rebinding. */
import {createServer} from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
  '.svg': 'image/svg+xml', '.ttf': 'font/ttf', '.otf': 'font/otf', '.woff': 'font/woff', '.woff2': 'font/woff2',
  '.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.mp4': 'video/mp4', '.webm': 'video/webm',
};

export async function serveLocal(root) {
  root = await fs.realpath(path.resolve(root));
  let port = 0;
  const server = createServer(async (req, res) => {
    try {
      if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405); res.end(); return; }
      if (![`127.0.0.1:${port}`, `localhost:${port}`].includes(req.headers.host)) { res.writeHead(421); res.end(); return; }
      const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
      const file = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
      if (!file.startsWith(root + path.sep)) { res.writeHead(403); res.end(); return; }
      const real = await fs.realpath(file);                     // a symlink must also stay inside the folder
      if (!real.startsWith(root + path.sep)) { res.writeHead(403); res.end(); return; }
      const bytes = await fs.readFile(real);
      const headers = {'Content-Type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream',
        'Cache-Control': 'no-store', 'Accept-Ranges': 'bytes'};
      const range = req.headers.range && /^bytes=(\d*)-(\d*)$/.exec(req.headers.range);
      if (req.headers.range) {
        // bytes=a-b, bytes=a- and the suffix form bytes=-n; an end past the size is clamped (RFC 7233).
        let start = -1, end = bytes.length - 1;
        if (range && range[1] !== '') { start = Number(range[1]); if (range[2] !== '') end = Math.min(Number(range[2]), bytes.length - 1); }
        else if (range && range[2] !== '') start = Math.max(0, bytes.length - Number(range[2]));
        if (!range || start < 0 || end < start || start >= bytes.length) {
          res.writeHead(416, {'Content-Range': `bytes */${bytes.length}`}); res.end(); return;
        }
        res.writeHead(206, {...headers, 'Content-Length': end - start + 1, 'Content-Range': `bytes ${start}-${end}/${bytes.length}`});
        res.end(req.method === 'HEAD' ? undefined : bytes.subarray(start, end + 1));
        return;
      }
      res.writeHead(200, {...headers, 'Content-Length': bytes.length});
      res.end(req.method === 'HEAD' ? undefined : bytes);
    } catch {
      res.writeHead(404); res.end('Not found');
    }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  port = server.address().port;
  return {
    url: `http://127.0.0.1:${server.address().port}/`,
    close: async () => { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); },
  };
}
