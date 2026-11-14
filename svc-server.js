#!/usr/bin/env node
// Server kecil untuk voice changer lagu -> suara Selena (port 8895). Satu pekerjaan berjalan sekali (2 CPU), sisanya antre.
// POST /svc/upload?name=lagu.mp3 (body = file mentah) -> {id,pos}; GET /svc/status?id=; GET /svc/result?id= (mp3, dukung Range)
const http = require('http'), fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const PORT = 8895, ROOT = __dirname, JOBS = path.join(ROOT, 'jobs'), PY = path.join(ROOT, 'venv/bin/python');
const MAX = 80 * 1024 * 1024, KEEP = 12, EXT = new Set(['.mp3', '.m4a', '.wav', '.ogg', '.flac', '.aac', '.mp4', '.webm', '.opus']);
fs.mkdirSync(JOBS, { recursive: true });
const queue = []; let running = null;
const jd = id => path.join(JOBS, id);
const rd = (id, f) => { try { return JSON.parse(fs.readFileSync(path.join(jd(id), f), 'utf8')); } catch { return null; } };

function next() {
  if (running || !queue.length) return;
  const id = queue.shift(); running = id;
  const meta = rd(id, 'meta.json') || {};
  const p = spawn('nice', ['-n', '15', PY, path.join(ROOT, 'svc.py'), path.join(jd(id), meta.file), jd(id)], { stdio: ['ignore', 'ignore', fs.openSync(path.join(jd(id), 'err.log'), 'a')] });
  p.on('exit', code => {
    const st = rd(id, 'status.json');
    if (code !== 0 && (!st || st.stage !== 'selesai')) fs.writeFileSync(path.join(jd(id), 'status.json'), JSON.stringify({ stage: 'gagal', pct: 0, err: 'proses berhenti (kode ' + code + ')', t: Date.now() / 1000 }));
    running = null; prune(); next();
  });
}
function prune() {
  const ds = fs.readdirSync(JOBS).map(n => ({ n, t: fs.statSync(jd(n)).mtimeMs })).sort((a, b) => b.t - a.t);
  for (const d of ds.slice(KEEP)) if (d.n !== running && !queue.includes(d.n)) fs.rmSync(jd(d.n), { recursive: true, force: true });
}
const json = (res, code, o) => { res.writeHead(code, { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' }); res.end(JSON.stringify(o)); };

http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Range');
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }
  const u = new URL(req.url, 'http://x'), id = (u.searchParams.get('id') || '').replace(/[^a-z0-9]/gi, '');
  if (u.pathname === '/svc/upload' && req.method === 'POST') {
    const name = (u.searchParams.get('name') || 'lagu').slice(0, 80); let ext = path.extname(name).toLowerCase();
    if (!EXT.has(ext)) ext = '.mp3';
    const jid = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    fs.mkdirSync(jd(jid)); const file = 'in' + ext, out = fs.createWriteStream(path.join(jd(jid), file));
    let n = 0, bad = false;
    req.on('data', c => { n += c.length; if (n > MAX && !bad) { bad = true; out.destroy(); fs.rmSync(jd(jid), { recursive: true, force: true }); json(res, 413, { ok: false, err: 'file terlalu besar (maks 80 MB)' }); req.destroy(); } });
    req.pipe(out);
    out.on('finish', () => {
      if (bad) return;
      fs.writeFileSync(path.join(jd(jid), 'meta.json'), JSON.stringify({ name, file, size: n, t0: Date.now() }));
      fs.writeFileSync(path.join(jd(jid), 'status.json'), JSON.stringify({ stage: 'antre', pct: 0, t: Date.now() / 1000 }));
      queue.push(jid); next(); json(res, 200, { ok: true, id: jid, pos: queue.indexOf(jid) + 1 + (running && running !== jid ? 1 : 0) });
    });
  } else if (u.pathname === '/svc/status') {
    if (!id || !fs.existsSync(jd(id))) return json(res, 404, { ok: false, err: 'tidak ditemukan' });
    const st = rd(id, 'status.json') || { stage: 'antre', pct: 0 }, m = rd(id, 'meta.json') || {};
    json(res, 200, { ok: true, ...st, name: m.name, elapsed: m.t0 ? Math.round((Date.now() - m.t0) / 1000) : 0, pos: queue.indexOf(id) + 1, queued: queue.length + (running ? 1 : 0) });
  } else if (u.pathname === '/svc/result') {
    const f = path.join(jd(id || 'x'), 'hasil.mp3');
    if (!id || !fs.existsSync(f)) return json(res, 404, { ok: false, err: 'belum selesai' });
    const size = fs.statSync(f).size, rg = /bytes=(\d*)-(\d*)/.exec(req.headers.range || '');
    if (rg) { const s = rg[1] ? +rg[1] : 0, e = rg[2] ? Math.min(+rg[2], size - 1) : size - 1; res.writeHead(206, { 'Content-Type': 'audio/mpeg', 'Content-Range': `bytes ${s}-${e}/${size}`, 'Accept-Ranges': 'bytes', 'Content-Length': e - s + 1 }); fs.createReadStream(f, { start: s, end: e }).pipe(res); }
    else { res.writeHead(200, { 'Content-Type': 'audio/mpeg', 'Accept-Ranges': 'bytes', 'Content-Length': size }); fs.createReadStream(f).pipe(res); }
  } else json(res, 404, { ok: false });
}).listen(PORT, () => console.log('SVC server :' + PORT));
