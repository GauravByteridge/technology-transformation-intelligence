/**
 * Technology Transformation Intelligence — Development Launcher
 * 
 * Zero-dependency Node.js server for managing backend and frontend processes.
 * Designed for Windows with full process isolation — parent never crashes
 * due to child process errors.
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
  try {
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), 'utf8');
  } catch (e) {
    console.error('Failed to save config:', e.message);
  }
}

function getServiceDir(serviceKey) {
  const svc = config.services[serviceKey];
  return path.resolve(__dirname, svc.directory);
}

// ─── Process Registry ────────────────────────────────────────────────────────

const processes = {};

function getServiceStatus(serviceKey) {
  const entry = processes[serviceKey];
  if (!entry) return { status: 'stopped', pid: null };
  return { status: entry.status, pid: entry.pid || null };
}

// ─── Logging (isolated, never throws) ────────────────────────────────────────

function appendLog(serviceKey, data, stream = 'stdout') {
  try {
    if (!processes[serviceKey]) return;
    const text = typeof data === 'string' ? data : data.toString('utf8');
    const lines = text.split('\n').filter(l => l.trim());
    const noisePatterns = (config.logging.noisePatterns || []).map(p => {
      try { return new RegExp(p, 'i'); } catch { return null; }
    }).filter(Boolean);

    for (const line of lines) {
      const isNoise = noisePatterns.some(p => p.test(line));
      if (isNoise) continue;
      processes[serviceKey].logs.push({
        time: new Date().toISOString(),
        stream,
        text: line.substring(0, 1000) // Cap line length
      });
    }

    // Trim buffer
    const maxLines = config.logging.maxBufferLines || 500;
    if (processes[serviceKey].logs.length > maxLines) {
      processes[serviceKey].logs = processes[serviceKey].logs.slice(-maxLines);
    }
  } catch (e) {
    // Never let logging crash the parent
  }
}

function getLogs(serviceKey, lastN = 100, search = null) {
  try {
    const entry = processes[serviceKey];
    if (!entry) return [];
    let logs = entry.logs.slice(-lastN);
    if (search) {
      const re = new RegExp(search, 'i');
      logs = logs.filter(l => re.test(l.text));
    }
    return logs;
  } catch (e) {
    return [];
  }
}

// ─── Port Checking ───────────────────────────────────────────────────────────

function checkPort(port) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(800);
    socket.once('connect', () => { socket.destroy(); resolve(true); });
    socket.once('timeout', () => { socket.destroy(); resolve(false); });
    socket.once('error', () => { socket.destroy(); resolve(false); });
    try {
      socket.connect(port, '127.0.0.1');
    } catch {
      resolve(false);
    }
  });
}

// Background port checker — updates status based on actual port availability
setInterval(async () => {
  try {
    for (const key of Object.keys(config.services)) {
      const entry = processes[key];
      if (!entry || entry.status === 'stopped') continue;
      const port = config.services[key].port;
      const up = await checkPort(port);
      if (up && entry.status === 'starting') {
        entry.status = 'running';
      }
    }
  } catch (e) {
    // Never crash the monitor loop
  }
}, 3000);

// ─── Process Lifecycle (fully isolated) ──────────────────────────────────────

function startService(serviceKey) {
  try {
    const existing = processes[serviceKey];
    if (existing && existing.status !== 'stopped') {
      return { error: `${serviceKey} is already running (status: ${existing.status})` };
    }

    const svc = config.services[serviceKey];
    if (!svc) return { error: `Unknown service: ${serviceKey}` };

    const cwd = getServiceDir(serviceKey);
    if (!fs.existsSync(cwd)) {
      return { error: `Service directory not found: ${cwd}` };
    }

    // Build environment — merge process.env with config.environment
    const env = { ...process.env };
    if (config.environment) {
      Object.assign(env, config.environment);
    }

    // Spawn with full isolation:
    // - detached: true → child gets its own process group
    // - stdio: ['ignore', 'pipe', 'pipe'] → no stdin, pipe stdout/stderr for logs
    // - windowsHide: true → no console window on Windows
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
      detached: true,
      windowsHide: true,
    });

    // Initialize process registry entry
    processes[serviceKey] = {
      proc,
      pid: proc.pid,
      status: 'starting',
      logs: [],
      startedAt: new Date().toISOString(),
    };

    // Pipe stdout — wrapped in try/catch so errors don't propagate
    if (proc.stdout) {
      proc.stdout.on('data', (data) => {
        try { appendLog(serviceKey, data, 'stdout'); } catch {}
      });
      proc.stdout.on('error', () => {}); // Swallow pipe errors
    }

    // Pipe stderr — wrapped in try/catch
    if (proc.stderr) {
      proc.stderr.on('data', (data) => {
        try { appendLog(serviceKey, data, 'stderr'); } catch {}
      });
      proc.stderr.on('error', () => {}); // Swallow pipe errors
    }

    // Handle process exit — never throws
    proc.on('close', (code, signal) => {
      try {
        if (processes[serviceKey]) {
          processes[serviceKey].status = 'stopped';
          processes[serviceKey].proc = null;
          appendLog(serviceKey, `Process exited (code=${code}, signal=${signal})`, 'system');
        }
      } catch {}
    });

    // Handle spawn errors — never throws
    proc.on('error', (err) => {
      try {
        if (processes[serviceKey]) {
          processes[serviceKey].status = 'stopped';
          processes[serviceKey].proc = null;
          appendLog(serviceKey, `Spawn error: ${err.message}`, 'system');
        }
      } catch {}
    });

    // Unref so parent can exit independently if needed
    proc.unref();

    return { success: true, pid: proc.pid };
  } catch (e) {
    return { error: `Failed to start ${serviceKey}: ${e.message}` };
  }
}

function stopService(serviceKey) {
  try {
    const entry = processes[serviceKey];
    if (!entry || entry.status === 'stopped') {
      // Even if we think it's stopped, try to kill the port as a safety measure
      const port = config.services[serviceKey]?.port;
      if (port) killPort(port);
      return { success: true, message: `${serviceKey} was already stopped` };
    }

    const pid = entry.pid;

    // On Windows, use taskkill with /T (tree) to kill all child processes
    if (process.platform === 'win32' && pid) {
      try {
        execSync(`taskkill /PID ${pid} /T /F`, { stdio: 'ignore', timeout: 5000 });
      } catch (e) {
        // Process might already be dead — try port-based kill as fallback
        const port = config.services[serviceKey]?.port;
        if (port) killPort(port);
      }
    } else if (pid) {
      try {
        process.kill(-pid, 'SIGTERM');
      } catch {}
    }

    // Update registry
    entry.status = 'stopped';
    entry.proc = null;
    appendLog(serviceKey, 'Service stopped by user', 'system');

    return { success: true };
  } catch (e) {
    return { error: `Failed to stop ${serviceKey}: ${e.message}` };
  }
}

async function restartService(serviceKey) {
  stopService(serviceKey);
  // Wait for port to be released
  const port = config.services[serviceKey]?.port;
  if (port) {
    for (let i = 0; i < 10; i++) {
      await new Promise(r => setTimeout(r, 500));
      const inUse = await checkPort(port);
      if (!inUse) break;
    }
  } else {
    await new Promise(r => setTimeout(r, 2000));
  }
  return startService(serviceKey);
}

// ─── Port Utilities ──────────────────────────────────────────────────────────

function killPort(port) {
  try {
    if (process.platform === 'win32') {
      const output = execSync(
        `netstat -ano | findstr "LISTENING" | findstr ":${port} "`,
        { encoding: 'utf8', timeout: 5000, stdio: ['pipe', 'pipe', 'pipe'] }
      );
      const pids = new Set();
      for (const line of output.trim().split('\n')) {
        const parts = line.trim().split(/\s+/);
        const pid = parts[parts.length - 1];
        if (pid && pid !== '0' && !isNaN(parseInt(pid))) pids.add(pid);
      }
      for (const pid of pids) {
        try { execSync(`taskkill /PID ${pid} /T /F`, { stdio: 'ignore', timeout: 5000 }); } catch {}
      }
      return { success: true, freed: Array.from(pids) };
    }
    return { success: true, freed: [] };
  } catch (e) {
    return { success: true, freed: [] }; // Port might already be free
  }
}

function freePort(port) {
  const result = killPort(port);
  // Also update any process registry entries that use this port
  for (const [key, svc] of Object.entries(config.services)) {
    if (svc.port === port && processes[key]) {
      processes[key].status = 'stopped';
      processes[key].proc = null;
    }
  }
  return result;
}

// ─── Database Operations ─────────────────────────────────────────────────────

function runSeed(seedKey) {
  const seed = config.seeds[seedKey];
  if (!seed) return { error: `Unknown seed: ${seedKey}` };

  const cwd = path.resolve(__dirname, seed.cwd);
  const env = { ...process.env, ...(config.environment || {}) };
  const results = [];

  for (const command of seed.commands) {
    try {
      const output = execSync(command, { cwd, env, encoding: 'utf8', timeout: 120000, stdio: ['pipe', 'pipe', 'pipe'] });
      results.push({ command, success: true, output: output.trim().substring(0, 500) });
    } catch (e) {
      results.push({ command, success: false, error: (e.stderr || e.message || '').substring(0, 500) });
      return { error: `Failed on: ${command}`, details: results };
    }
  }

  return { success: true, results };
}

// ─── HTTP Server ─────────────────────────────────────────────────────────────

function parseBody(req) {
  return new Promise((resolve) => {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try { resolve(JSON.parse(body)); }
      catch { resolve({}); }
    });
    req.on('error', () => resolve({}));
  });
}

function sendJSON(res, data, status = 200) {
  try {
    const json = JSON.stringify(data);
    res.writeHead(status, {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    });
    res.end(json);
  } catch (e) {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Internal server error' }));
  }
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://localhost:${config.launcherPort}`);
    const pathname = url.pathname;
    const method = req.method;

    // CORS preflight
    if (method === 'OPTIONS') {
      res.writeHead(204, {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      });
      return res.end();
    }

    // Serve dashboard
    if (pathname === '/' || pathname === '/index.html') {
      const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
      res.writeHead(200, { 'Content-Type': 'text/html' });
      return res.end(html);
    }

    // ─── API Routes ──────────────────────────────────────────────────────

    // GET /api/status — all services status
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
      return sendJSON(res, startService(startMatch[1]));
    }

    // POST /api/services/:key/stop
    const stopMatch = pathname.match(/^\/api\/services\/(\w+)\/stop$/);
    if (stopMatch && method === 'POST') {
      return sendJSON(res, stopService(stopMatch[1]));
    }

    // POST /api/services/:key/restart
    const restartMatch = pathname.match(/^\/api\/services\/(\w+)\/restart$/);
    if (restartMatch && method === 'POST') {
      const result = await restartService(restartMatch[1]);
      return sendJSON(res, result);
    }

    // GET /api/services/:key/logs
    const logsMatch = pathname.match(/^\/api\/services\/(\w+)\/logs$/);
    if (logsMatch && method === 'GET') {
      const last = parseInt(url.searchParams.get('last') || '100');
      const search = url.searchParams.get('search') || null;
      return sendJSON(res, { logs: getLogs(logsMatch[1], last, search) });
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
      for (const key of Object.keys(config.services)) {
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
      return sendJSON(res, runSeed(seedMatch[1]));
    }

    // POST /api/ports/:port/free
    const portFreeMatch = pathname.match(/^\/api\/ports\/(\d+)\/free$/);
    if (portFreeMatch && method === 'POST') {
      return sendJSON(res, freePort(parseInt(portFreeMatch[1])));
    }

    // POST /api/install
    if (pathname === '/api/install' && method === 'POST') {
      const body = await parseBody(req);
      const target = body.target;
      try {
        if (target === 'frontend') {
          const cwd = path.resolve(__dirname, '../../frontend');
          execSync('npm install', { cwd, encoding: 'utf8', timeout: 120000, stdio: ['pipe', 'pipe', 'pipe'] });
          return sendJSON(res, { success: true, message: 'npm install completed' });
        } else if (target === 'backend') {
          const cwd = path.resolve(__dirname, '../../backend');
          execSync('python -m pip install -r requirements.txt', { cwd, encoding: 'utf8', timeout: 120000, stdio: ['pipe', 'pipe', 'pipe'] });
          return sendJSON(res, { success: true, message: 'pip install completed' });
        }
        return sendJSON(res, { error: 'Unknown target' }, 400);
      } catch (e) {
        return sendJSON(res, { error: (e.stderr || e.message || 'Install failed').substring(0, 500) });
      }
    }

    // 404
    sendJSON(res, { error: 'Not found' }, 404);
  } catch (e) {
    // Global catch — NEVER let any request crash the server
    try {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Internal server error' }));
    } catch {}
  }
});

// Handle server errors gracefully
server.on('error', (e) => {
  if (e.code === 'EADDRINUSE') {
    console.error(`\n  ✗ Port ${config.launcherPort} already in use. Kill it or change launcherPort in config.\n`);
    process.exit(1);
  }
  console.error('Server error:', e.message);
});

const PORT = config.launcherPort || 9001;
server.listen(PORT, () => {
  console.log(`\n${'═'.repeat(50)}`);
  console.log(`  TTI Platform Launcher`);
  console.log(`  Dashboard: http://localhost:${PORT}`);
  console.log(`${'═'.repeat(50)}`);
  console.log(`\n  Services:`);
  for (const [key, svc] of Object.entries(config.services)) {
    console.log(`    ${svc.name} → http://localhost:${svc.port}`);
  }
  console.log(`\n  Use the dashboard to Start / Stop / Restart services.`);
  console.log(`${'─'.repeat(50)}\n`);
});

// ─── Graceful Shutdown ───────────────────────────────────────────────────────

function shutdown() {
  console.log('\n  Shutting down all services...');
  for (const key of Object.keys(processes)) {
    try { stopService(key); } catch {}
  }
  console.log('  Done. Goodbye.\n');
  process.exit(0);
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

// Prevent unhandled errors from crashing the launcher
process.on('uncaughtException', (err) => {
  console.error('Uncaught exception (ignored):', err.message);
});
process.on('unhandledRejection', (reason) => {
  console.error('Unhandled rejection (ignored):', reason);
});
