/* Checks for scripts/kit/local-server.mjs: it serves the folder, refuses paths and symlinks that leave it, and only
   answers requests addressed to itself (no DNS rebinding). Run: node tests/server_check.mjs (prints "ok N"). */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const {serveLocal} = await import(new URL('../scripts/kit/local-server.mjs', import.meta.url));

const root = await fs.mkdtemp(path.join(os.tmpdir(), 'motion-server-'));
const outside = await fs.mkdtemp(path.join(os.tmpdir(), 'motion-outside-'));
await fs.writeFile(path.join(root, 'index.html'), '<p>piece</p>');
await fs.writeFile(path.join(outside, 'secret.txt'), 'secret');
let symlinked = false;
try { await fs.symlink(path.join(outside, 'secret.txt'), path.join(root, 'link.txt')); symlinked = true; } catch { /* no symlink rights */ }

const server = await serveLocal(root);
const {port} = new URL(server.url);
const get = (pathname, host = `127.0.0.1:${port}`) => new Promise((resolve, reject) => {
  const req = http.request({host: '127.0.0.1', port, path: pathname, method: 'GET', headers: {host}}, res => {
    let body = ''; res.on('data', d => { body += d; }); res.on('end', () => resolve({status: res.statusCode, body}));
  });
  req.on('error', reject); req.end();
});

let checks = 0;
const same = (a, b, msg) => { checks++; assert.equal(a, b, msg); };
try {
  same((await get('/')).body, '<p>piece</p>', 'serves index.html');
  same((await get('/index.html', `localhost:${port}`)).status, 200, 'localhost is the same server');
  same((await get('/index.html', 'evil.example:80')).status, 421, 'a foreign Host header is refused (DNS rebinding)');
  same((await get('/../' + path.basename(outside) + '/secret.txt')).status === 200, false, 'no path outside the folder');
  same((await get('/%2e%2e/%2e%2e/etc/passwd')).status === 200, false, 'encoded traversal refused');
  same((await get('/missing.js')).status, 404, 'missing file is a 404');
  if (symlinked) same((await get('/link.txt')).status, 403, 'a symlink that leaves the folder is refused');
} finally {
  await server.close();
  await fs.rm(root, {recursive: true, force: true});
  await fs.rm(outside, {recursive: true, force: true});
}
console.log(`ok ${checks}${symlinked ? '' : ' (symlink check skipped: no rights to create one)'}`);
