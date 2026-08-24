/**
 * Technology Transformation Intelligence - Phase 6 Development Launcher
 * Zero-dependency Node.js server for managing backend, frontend, and database operations.
 *
 * Run: node server.js
 * Dashboard: http://localhost:9001
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn, execSync } = require('child_process');
const net = require('net');

// ─── Configuration ───────────────────────────────────────────────────────────

const CONFIG_PATH = path.join(__dirname, 'launcher-config.json');
let config = loadConfig();

function loadConfig() {
  try {
    return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
  } catch (e) {
    console.error('Failed to load config:', e.message);
    process.exit(1);
  }
}

function saveConfig() {
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), 'utf8');
}

function getServiceDir(serviceKey) {
  const svc = config.services[serviceKey];
  return path.resolve(__dirname, svc.directory);
}

// ─── Process Registry ────────────────────────────────────────────────────────

const processes = {};

function getServiceStatus(serviceKey) {
  const entry = processes[serviceKey];
  if (!entry) return { status: 'stopped', pid: null, mode: null };
  return { status: entry.status, pid: entry.proc?.pid || null, mode: entry.mode };
}

// ─── Logging ─────────────────────────────────────────────────────────────────

function appendLog(serviceKey, data, stream = 'stdout') {
  if (!processes[serviceKey]) return;
  const lines = data.toString().split('\n').filter(l => l.trim());
  const noisePatterns = config.logging.noisePatterns.map(p => new RegExp(p, 'i'));

  for (const line of lines) {
    const isNoise = noisePatterns.some(p => p.test(line));
    if (isNoise) continue;
    processes[serviceKey].logs.push({
      time: new Date().toISOString(),
      stream,
      text: line
    });
    if (processes[serviceKey].logs.length > config.logging.maxBufferLines) {
      processes[serviceKey].logs.shift();
    }
  }
}

function getLogs(serviceKey, lastN = 100, search = null) {
  const entry = processes[serviceKey];
  if (!entry) return [];
  let logs = entry.logs.slice(-lastN);
  if (search) {
    const re = new RegExp(search, 'i');
    logs = logs.filter(l => re.test(l.text));
  }
  return logs;
}

// ─── Port Monitoring ─────────────────────────────────────────────────────────

function checkPort(port) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(1000);
    socket.once('connect', () => { socket.destroy(); resolve(true); });
    socket.once('timeout', () => { socket.destroy(); resolve(false); });
    socket.once('error', () => { socket.destroy(); resolve(false); });
    socket.connect(port, '127.0.0.1');
  });
}

setInterval(async () => {
  for (const key of Object.keys(config.services)) {
    const entry = processes[key];
    if (!entry || entry.status === 'stopped') continue;
    const port = config.services[key].port;
    const up = await checkPort(port);
    if (up && entry.status === 'starting') {
      entry.status = 'running';
    } else if (!up && entry.status === 'running') {
      entry.status = 'starting';
    }
  }
}, 3000);

// ─── Process Lifecycle ───────────────────────────────────────────────────────

function startService(serviceKey, mode = 'run') {
  if (processes[serviceKey] && processes[serviceKey].status !== 'stopped') {
    return { error: `${serviceKey} is already running` };
  }

  const svc = config.services[serviceKey];
  const cwd = getServiceDir(serviceKey);
  const env = { ...process.env, ...config.environment };

  let cmd, args;
  if (process.platform === 'win32') {
    cmd = 'cmd.exe';
    args = ['/c', svc.runCommand];
  } else {
    cmd = '/bin/sh';
    args = ['-c', svc.runCommand];
  }

  const proc = spawn(cmd, args, {
    cwd,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true
  });

  processes[serviceKey] = { proc, mode, status: 'starting', logs: [] };

  proc.stdout.on('data', (data) => appendLog(serviceKey, data, 'stdout'));
  proc.stderr.on('data', (data) => appendLog(serviceKey, data, 'stderr'));

  proc.on('close', (code) => {
    if (processes[serviceKey]) {
      processes[serviceKey].status = 'stopped';
      appendLog(serviceKey, `Process exited with code ${code}`, 'system');
    }
  });

  proc.on('error', (err) => {
    if (processes[serviceKey]) {
      processes[serviceKey].status = 'stopped';
      appendLog(serviceKey, `Process error: ${err.message}`, 'system');
    }
  });

  return { success: true, pid: proc.pid };
}

function stopService(serviceKey) {
  const entry = processes[serviceKey];
  if (!entry || entry.status === 'stopped') {
    return { error: `${serviceKey} is not running` };
  }

  try {
    if (process.platform === 'win32') {
      execSync(`taskkill /PID ${entry.proc.pid} /T /F`, { stdio: 'ignore' });
    } else {
      process.kill(-entry.proc.pid, 'SIGTERM');
    }
  } catch (e) {
    // Process might already be dead
  }

  entry.status = 'stopped';
  entry.proc = null;
  return { success: true };
}

function restartService(serviceKey, mode) {
  stopService(serviceKey);
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(startService(serviceKey, mode || processes[serviceKey]?.mode || 'run'));
    }, 2000);
  });
}

// ─── Database Operations ─────────────────────────────────────────────────────

function runSeed(seedKey) {
  const seed = config.seeds[seedKey];
  if (!seed) return { error: `Unknown seed: ${seedKey}` };

  const cwd = path.resolve(__dirname, seed.cwd);
  const env = { ...process.env, ...config.environment };
  const results = [];

  for (const command of seed.commands) {
    try {
      const output = execSync(command, { cwd, env, encoding: 'utf8', timeout: 120000 });
      results.push({ command, success: true, output: output.trim() });
    } catch (e) {
      results.push({ command, success: false, error: e.message });
      return { error: `Failed on: ${command}`, details: results };
    }
  }

  return { success: true, results };
}

function checkDatabase(dbKey) {
  const db = config.databases[dbKey];
  if (!db) return { error: `Unknown database: ${dbKey}` };

  const env = { ...process.env, PGPASSWORD: db.password };
  try {
    execSync(
      `psql -h ${db.host} -p ${db.port} -U ${db.username} -d ${db.database} -c "SELECT 1"`,
      { env, encoding: 'utf8', timeout: 5000, stdio: 'pipe' }
    );
    return { success: true, status: 'connected' };
  } catch (e) {
    return { success: false, status: 'unreachable', error: e.message };
  }
}

// ─── Port Utilities ──────────────────────────────────────────────────────────

function freePort(port) {
  try {
    if (process.platform === 'win32') {
      const output = execSync(`netstat -ano | findstr "LISTENING" | findstr ":${port} "`, { encoding: 'utf8' });
      const lines = output.trim().split('\n');
      const pids = new Set();
      for (const line of lines) {
        const parts = line.trim().split(/\s+/);
        const pid = parts[parts.length - 1];
        if (pid && pid !== '0') pids.add(pid);
      }
      for (const pid of pids) {
        try { execSync(`taskkill /PID ${pid} /T /F`, { stdio: 'ignore' }); } catch (e) {}
      }
      return { success: true, freed: Array.from(pids) };
    }
    return { error: 'Port freeing only supported on Windows' };
  } catch (e) {
    return { success: true, freed: [] }; // Port might already be free
  }
}

// ─── HTTP Server & API ───────────────────────────────────────────────────────

function parseBody(req) {
  return new Promise((resolve) => {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try { resolve(JSON.parse(body)); }
      catch { resolve({}); }
    });
  });
}

function sendJSON(res, data, status = 200) {
  res.writeHead(status, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
  res.end(JSON.stringify(data));
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${config.launcherPort}`);
  const pathname = url.pathname;
  const method = req.method;

  // CORS preflight
  if (method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE',
      'Access-Control-Allow-Headers': 'Content-Type'
    });
    return res.end();
  }

  // Serve HTML dashboard
  if (pathname === '/' || pathname === '/index.html') {
    const htmlPath = path.join(__dirname, 'index.html');
    const html = fs.readFileSync(htmlPath, 'utf8');
    res.writeHead(200, { 'Content-Type': 'text/html' });
    return res.end(html);
  }

  // ─── API Routes ────────────────────────────────────────────────────────

  // GET /api/status
  if (pathname === '/api/status' && method === 'GET') {
    const statuses = {};
    for (const key of Object.keys(config.services)) {
      const svc = config.services[key];
      const st = getServiceStatus(key);
      const portUp = await checkPort(svc.port);
      statuses[key] = { ...svc, ...st, portUp };
    }
    return sendJSON(res, statuses);
  }

  // POST /api/services/:key/start
  const startMatch = pathname.match(/^\/api\/services\/(\w+)\/start$/);
  if (startMatch && method === 'POST') {
    const body = await parseBody(req);
    const result = startService(startMatch[1], body.mode || 'run');
    return sendJSON(res, result);
  }

  // POST /api/services/:key/stop
  const stopMatch = pathname.match(/^\/api\/services\/(\w+)\/stop$/);
  if (stopMatch && method === 'POST') {
    const result = stopService(stopMatch[1]);
    return sendJSON(res, result);
  }

  // POST /api/services/:key/restart
  const restartMatch = pathname.match(/^\/api\/services\/(\w+)\/restart$/);
  if (restartMatch && method === 'POST') {
    const body = await parseBody(req);
    const result = await restartService(restartMatch[1], body.mode);
    return sendJSON(res, result);
  }

  // GET /api/services/:key/logs
  const logsMatch = pathname.match(/^\/api\/services\/(\w+)\/logs$/);
  if (logsMatch && method === 'GET') {
    const last = parseInt(url.searchParams.get('last') || '100');
    const search = url.searchParams.get('search') || null;
    const logs = getLogs(logsMatch[1], last, search);
    return sendJSON(res, { logs });
  }

  // POST /api/start-all
  if (pathname === '/api/start-all' && method === 'POST') {
    const results = {};
    for (const key of Object.keys(config.services)) {
      results[key] = startService(key);
    }
    return sendJSON(res, results);
  }

  // POST /api/stop-all
  if (pathname === '/api/stop-all' && method === 'POST') {
    const results = {};
    for (const key of Object.keys(processes)) {
      results[key] = stopService(key);
    }
    return sendJSON(res, results);
  }

  // GET /api/config
  if (pathname === '/api/config' && method === 'GET') {
    return sendJSON(res, config);
  }

  // PUT /api/config
  if (pathname === '/api/config' && method === 'PUT') {
    const body = await parseBody(req);
    if (body.environment) config.environment = body.environment;
    if (body.databases) config.databases = body.databases;
    if (body.logging) config.logging = body.logging;
    saveConfig();
    return sendJSON(res, { success: true });
  }

  // POST /api/db/:key/seed
  const seedMatch = pathname.match(/^\/api\/db\/(\w+)\/seed$/);
  if (seedMatch && method === 'POST') {
    const result = runSeed(seedMatch[1]);
    return sendJSON(res, result);
  }

  // GET /api/db/:key/check
  const dbCheckMatch = pathname.match(/^\/api\/db\/(\w+)\/check$/);
  if (dbCheckMatch && method === 'GET') {
    const result = checkDatabase(dbCheckMatch[1]);
    return sendJSON(res, result);
  }

  // POST /api/ports/:port/free
  const portFreeMatch = pathname.match(/^\/api\/ports\/(\d+)\/free$/);
  if (portFreeMatch && method === 'POST') {
    const result = freePort(parseInt(portFreeMatch[1]));
    return sendJSON(res, result);
  }

  // POST /api/install
  if (pathname === '/api/install' && method === 'POST') {
    const body = await parseBody(req);
    const target = body.target; // 'backend' or 'frontend'
    try {
      if (target === 'frontend') {
        const cwd = path.resolve(__dirname, '../../frontend');
        execSync('npm install', { cwd, encoding: 'utf8', timeout: 120000 });
        return sendJSON(res, { success: true, message: 'npm install completed' });
      } else if (target === 'backend') {
        const cwd = path.resolve(__dirname, '../../backend');
        execSync('pip install -r requirements.txt', { cwd, encoding: 'utf8', timeout: 120000 });
        return sendJSON(res, { success: true, message: 'pip install completed' });
      }
      return sendJSON(res, { error: 'Unknown target. Use "frontend" or "backend".' }, 400);
    } catch (e) {
      return sendJSON(res, { error: e.message });
    }
  }

  // 404
  sendJSON(res, { error: 'Not found' }, 404);
});

const PORT = config.launcherPort || 9001;
server.listen(PORT, () => {
  console.log(`\n${'═'.repeat(54)}`);
  console.log(`  TTI Platform Launcher (Phase 6)`);
  console.log(`  Dashboard: http://localhost:${PORT}`);
  console.log(`${'═'.repeat(54)}`);
  console.log(`\n  Services:`);
  console.log(`    Backend  → http://localhost:${config.services.backend.port}`);
  console.log(`    Frontend → http://localhost:${config.services.frontend.port}`);
  console.log(`\n  Actions:`);
  console.log(`    Start All, Stop All, Seed DB, Install Deps`);
  console.log(`${'─'.repeat(54)}\n`);
});

// Cleanup on exit
process.on('SIGINT', () => {
  console.log('\nShutting down all services...');
  for (const key of Object.keys(processes)) {
    stopService(key);
  }
  process.exit(0);
});
