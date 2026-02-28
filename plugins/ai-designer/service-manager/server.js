#!/usr/bin/env node
import { spawn } from 'child_process';
import http from 'http';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PROJECT_ROOT = join(__dirname, '..');

const PORT = 11436;

const processes = { ollama: null, proxy: null };

async function checkPort(port) {
  return new Promise((resolve) => {
    const req = http.request({
      hostname: 'localhost',
      port: port,
      path: '/',
      method: 'GET',
      timeout: 1000
    }, (res) => {
      resolve(true);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
    req.end();
  });
}

function startOllama() {
  return new Promise((resolve, reject) => {
    if (processes.ollama) { resolve({ alreadyRunning: true }); return; }
    console.log('Starting Ollama with CORS...');
    const proc = spawn('ollama', ['serve'], {
      cwd: PROJECT_ROOT,
      env: { ...process.env, OLLAMA_ORIGINS: '*' },
      detached: true,
      stdio: 'ignore'
    });
    proc.on('error', reject);
    processes.ollama = proc;
    proc.unref();
    setTimeout(() => resolve({ started: true }), 1000);
  });
}

function startProxy() {
  return new Promise((resolve, reject) => {
    if (processes.proxy) { resolve({ alreadyRunning: true }); return; }
    console.log('Starting NVIDIA Proxy...');
    const proc = spawn('node', ['proxy/server.js'], {
      cwd: PROJECT_ROOT,
      detached: true,
      stdio: 'ignore'
    });
    proc.on('error', reject);
    processes.proxy = proc;
    proc.unref();
    setTimeout(() => resolve({ started: true }), 500);
  });
}

const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }
  
  if (req.method === 'GET' && req.url === '/status') {
    try {
      const [ollamaUp, proxyUp] = await Promise.all([
        checkPort(11434),
        checkPort(11435)
      ]);
      
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        ollama: ollamaUp,
        proxy: proxyUp,
        timestamp: Date.now()
      }));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }
  
  if (req.method === 'POST' && req.url === '/start') {
    try {
      const results = {};
      const [ollamaUp, proxyUp] = await Promise.all([
        checkPort(11434),
        checkPort(11435)
      ]);
      
      if (!ollamaUp) {
        await startOllama();
        results.ollama = 'started';
      } else {
        results.ollama = 'already-running';
      }
      
      if (!proxyUp) {
        await startProxy();
        results.proxy = 'started';
      } else {
        results.proxy = 'already-running';
      }
      
      await new Promise(r => setTimeout(r, 1500));
      const [finalOllama, finalProxy] = await Promise.all([
        checkPort(11434),
        checkPort(11435)
      ]);
      
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        success: true,
        results,
        status: {
          ollama: finalOllama,
          proxy: finalProxy
        }
      }));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ 
        success: false, 
        error: err.message 
      }));
    }
    return;
  }
  
  // Proxy endpoint for Ollama (MiniMax)
  if (req.method === 'POST' && req.url.startsWith('/proxy/ollama')) {
    const ollamaUp = await checkPort(11434);
    if (!ollamaUp) {
      res.writeHead(503, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Ollama not running' }));
      return;
    }
    
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      try {
        const proxyRes = await fetch('http://localhost:11434/v1/chat/completions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: body
        });
        const data = await proxyRes.text();
        res.writeHead(proxyRes.status, { 'Content-Type': 'application/json' });
        res.end(data);
      } catch (e) {
        res.writeHead(502, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }
  
  // Proxy endpoint for Kimi (NVIDIA NIM)
  if (req.method === 'POST' && req.url.startsWith('/proxy/kimi')) {
    const proxyUp = await checkPort(11435);
    if (!proxyUp) {
      res.writeHead(503, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Kimi proxy not running' }));
      return;
    }
    
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      try {
        const proxyRes = await fetch('http://localhost:11435/v1/chat/completions', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': req.headers.authorization || ''
          },
          body: body
        });
        const data = await proxyRes.text();
        res.writeHead(proxyRes.status, { 'Content-Type': 'application/json' });
        res.end(data);
      } catch (e) {
        res.writeHead(502, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }
  
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found' }));
});

server.listen(PORT, () => {
  console.log(`\n🚀 Service Manager running on http://localhost:${PORT}`);
  console.log('   GET  /status - Check service status');
  console.log('   POST /start  - Start Ollama + Proxy\n');
});
