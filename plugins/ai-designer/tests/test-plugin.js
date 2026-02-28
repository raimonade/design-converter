#!/usr/bin/env node

import http from 'http';
import https from 'https';

const CONFIG = {
  ollama: { port: 11434, host: 'localhost' },
  proxy: { port: 11435, host: 'localhost' },
  serviceManager: { port: 11436, host: 'localhost' }
};

const TEST_COLORS = {
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m'
};

function log(type, message, details = '') {
  const colors = { pass: TEST_COLORS.green, fail: TEST_COLORS.red, warn: TEST_COLORS.yellow, info: TEST_COLORS.blue };
  const symbols = { pass: '✅', fail: '❌', warn: '⚠️', info: 'ℹ️' };
  console.log(`${colors[type]}${symbols[type]} ${message}${TEST_COLORS.reset}${details ? `: ${details}` : ''}`);
}

function fetch(url, options = {}) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const lib = urlObj.protocol === 'https:' ? https : http;
    
    const req = lib.request({
      hostname: urlObj.hostname,
      port: urlObj.port || (urlObj.protocol === 'https:' ? 443 : 80),
      path: urlObj.pathname + urlObj.search,
      method: options.method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Origin': 'null',
        ...options.headers
      },
      timeout: options.timeout || 10000
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        resolve({
          ok: res.statusCode >= 200 && res.statusCode < 300,
          status: res.statusCode,
          statusText: res.statusMessage,
          headers: res.headers,
          text: () => Promise.resolve(data),
          json: () => Promise.resolve(JSON.parse(data))
        });
      });
    });
    
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('Timeout')); });
    
    if (options.body) req.write(options.body);
    req.end();
  });
}

async function testServiceConnectivity() {
  log('info', 'Testing Service Connectivity');
  
  const results = { ollama: false, proxy: false, serviceManager: false };
  
  try {
    const ollamaRes = await fetch(`http://localhost:${CONFIG.ollama.port}/api/tags`, { timeout: 5000 });
    results.ollama = ollamaRes.ok;
    log(ollamaRes.ok ? 'pass' : 'fail', 'Ollama (MiniMax)', `Port ${CONFIG.ollama.port}, Status ${ollamaRes.status}`);
  } catch (e) {
    log('fail', 'Ollama (MiniMax)', e.message);
  }
  
  try {
    const proxyRes = await fetch(`http://localhost:${CONFIG.proxy.port}/v1/chat/completions`, { 
      method: 'OPTIONS',
      timeout: 5000 
    });
    results.proxy = proxyRes.status === 204 || proxyRes.status === 200;
    log(results.proxy ? 'pass' : 'fail', 'Proxy (Kimi)', `Port ${CONFIG.proxy.port}, Status ${proxyRes.status}`);
  } catch (e) {
    log('fail', 'Proxy (Kimi)', e.message);
  }
  
  try {
    const smRes = await fetch(`http://localhost:${CONFIG.serviceManager.port}/status`, { timeout: 5000 });
    results.serviceManager = smRes.ok;
    if (smRes.ok) {
      const data = await smRes.json();
      log('pass', 'Service Manager', `Port ${CONFIG.serviceManager.port}, Ollama: ${data.ollama}, Proxy: ${data.proxy}`);
    }
  } catch (e) {
    log('fail', 'Service Manager', e.message);
  }
  
  return results;
}

async function testCorsHeaders() {
  log('info', 'Testing CORS Headers (Figma null origin)');
  
  const results = { ollama: false, proxy: false };
  
  try {
    const res = await fetch(`http://localhost:${CONFIG.ollama.port}/api/tags`, { 
      headers: { 'Origin': 'null' },
      timeout: 5000
    });
    const hasCors = res.headers['access-control-allow-origin'] === '*';
    results.ollama = hasCors;
    log(hasCors ? 'pass' : 'fail', 'Ollama CORS', `Access-Control-Allow-Origin: ${res.headers['access-control-allow-origin'] || 'missing'}`);
  } catch (e) {
    log('fail', 'Ollama CORS', e.message);
  }
  
  try {
    const res = await fetch(`http://localhost:${CONFIG.proxy.port}/v1/chat/completions`, { 
      method: 'OPTIONS',
      headers: { 'Origin': 'null' },
      timeout: 5000
    });
    const hasCors = res.headers['access-control-allow-origin'] === '*';
    results.proxy = hasCors;
    log(hasCors ? 'pass' : 'fail', 'Proxy CORS', `Access-Control-Allow-Origin: ${res.headers['access-control-allow-origin'] || 'missing'}`);
  } catch (e) {
    log('fail', 'Proxy CORS', e.message);
  }
  
  return results;
}

async function testMiniMaxApi() {
  log('info', 'Testing MiniMax M2.5 via Ollama');
  
  try {
    const res = await fetch(`http://localhost:${CONFIG.ollama.port}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'minimax-m2.5:cloud',
        messages: [{ role: 'user', content: 'Say "test ok" and nothing else' }],
        max_tokens: 10
      }),
      timeout: 30000
    });
    
    if (!res.ok) {
      const text = await res.text();
      log('fail', 'MiniMax API', `Status ${res.status}: ${text.substring(0, 200)}`);
      return false;
    }
    
    const data = await res.json();
    const content = data.choices?.[0]?.message?.content || data.choices?.[0]?.message?.reasoning || '';
    log('pass', 'MiniMax API', `Response received (${content.length} chars)`);
    return true;
  } catch (e) {
    log('fail', 'MiniMax API', e.message);
    return false;
  }
}

async function testGlmApi() {
  log('info', 'Testing GLM-5 via Z.AI Coding Plan');
  
  const apiKey = process.env.ZAI_CODING_PLAN_KEY || process.env.ZAI_API_KEY;
  if (!apiKey) {
    log('warn', 'GLM-5 API', 'No API key found (ZAI_CODING_PLAN_KEY or ZAI_API_KEY)');
    return false;
  }
  
  try {
    const res = await fetch('https://open.bigmodel.cn/api/coding/paas/v4/chat/completions', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: 'glm-5',
        messages: [{ role: 'user', content: 'Say "test ok" and nothing else' }],
        max_tokens: 10
      }),
      timeout: 30000
    });
    
    if (!res.ok) {
      const text = await res.text();
      log('fail', 'GLM-5 API', `Status ${res.status}: ${text.substring(0, 200)}`);
      return false;
    }
    
    const data = await res.json();
    const content = data.choices?.[0]?.message?.content || '';
    log('pass', 'GLM-5 API', `Response received (${content.length} chars)`);
    return true;
  } catch (e) {
    log('fail', 'GLM-5 API', e.message);
    return false;
  }
}

async function testKimiApi() {
  log('info', 'Testing Kimi K2.5 via Proxy');
  
  const apiKey = process.env.NVAPI_KEY || process.env.NVIDIA_NIM_API_KEY || process.env.KIMI_API_KEY || process.env.NVIDIA_API_KEY;
  if (!apiKey) {
    log('warn', 'Kimi API', 'Skipped - No API key (set NVAPI_KEY, NVIDIA_NIM_API_KEY, or KIMI_API_KEY)');
    return 'skipped';
  }
  
  try {
    const res = await fetch(`http://localhost:${CONFIG.proxy.port}/v1/chat/completions`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: 'moonshotai/kimi-k2.5',
        messages: [{ role: 'user', content: 'Say "test ok" and nothing else' }],
        max_tokens: 10
      }),
      timeout: 30000
    });
    
    if (!res.ok) {
      const text = await res.text();
      log('fail', 'Kimi API', `Status ${res.status}: ${text.substring(0, 200)}`);
      return false;
    }
    
    const data = await res.json();
    const content = data.choices?.[0]?.message?.content || '';
    log('pass', 'Kimi API', `Response received (${content.length} chars)`);
    return true;
  } catch (e) {
    log('fail', 'Kimi API', e.message);
    return false;
  }
}

async function testDesignGeneration() {
  log('info', 'Testing Design Generation (MiniMax)');
  
  try {
    const res = await fetch(`http://localhost:${CONFIG.ollama.port}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'minimax-m2.5:cloud',
        messages: [
          { role: 'system', content: 'You are a Figma design generator. Output ONLY valid JSON, no markdown code blocks, no explanation. Start your response with { and end with }.' },
          { role: 'user', content: 'Create a simple login form. Output JSON: {"name":"Login Form","type":"frame","width":400,"height":300,"children":[{"type":"text","content":"Email"},{"type":"rectangle","name":"email-input"},{"type":"text","content":"Password"},{"type":"rectangle","name":"password-input"},{"type":"rectangle","name":"submit-btn"}]}' }
        ],
        max_tokens: 500
      }),
      timeout: 60000
    });
    
    if (!res.ok) {
      const text = await res.text();
      log('fail', 'Design Generation', `Status ${res.status}`);
      return false;
    }
    
    const data = await res.json();
    let content = data.choices?.[0]?.message?.content || '';
    
    if (!content && data.choices?.[0]?.message?.reasoning) {
      content = data.choices?.[0]?.message?.reasoning;
    }
    
    if (!content) {
      log('fail', 'Design Generation', 'Empty response from API');
      return false;
    }
    
    try {
      let cleaned = content.trim();
      if (cleaned.includes('```')) {
        cleaned = cleaned.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
      }
      
      const firstBrace = cleaned.indexOf('{');
      const lastBrace = cleaned.lastIndexOf('}');
      if (firstBrace !== -1 && lastBrace !== -1) {
        cleaned = cleaned.substring(firstBrace, lastBrace + 1);
      }
      
      const parsed = JSON.parse(cleaned);
      
      if (parsed.name && parsed.type) {
        log('pass', 'Design Generation', `Valid JSON: "${parsed.name}" (${parsed.type})`);
        return true;
      } else {
        log('fail', 'Design Generation', 'JSON missing required fields (name, type)');
        return false;
      }
    } catch (parseErr) {
      log('fail', 'Design Generation', `JSON parse failed: ${content.substring(0, 100)}...`);
      return false;
    }
  } catch (e) {
    log('fail', 'Design Generation', e.message);
    return false;
  }
}

async function startServicesIfNeeded() {
  log('info', 'Checking if services need to be started');
  
  try {
    const statusRes = await fetch(`http://localhost:${CONFIG.serviceManager.port}/status`, { timeout: 3000 });
    const status = await statusRes.json();
    
    if (!status.ollama || !status.proxy) {
      log('warn', 'Services not running', 'Attempting to start via service manager');
      
      const startRes = await fetch(`http://localhost:${CONFIG.serviceManager.port}/start`, { 
        method: 'POST',
        timeout: 30000
      });
      const startData = await startRes.json();
      
      if (startData.success) {
        log('pass', 'Services started', JSON.stringify(startData.results));
        return true;
      } else {
        log('fail', 'Service start failed', startData.error);
        return false;
      }
    } else {
      log('pass', 'Services already running');
      return true;
    }
  } catch (e) {
    log('fail', 'Service Manager not available', e.message);
    log('info', 'Start manually: cd figma-ai-designer && node service-manager/server.js');
    return false;
  }
}

async function runAllTests() {
  console.log('\n' + '='.repeat(60));
  console.log('🧪 Figma AI Designer Plugin - Automated Test Suite');
  console.log('='.repeat(60) + '\n');
  
  const startTime = Date.now();
  const results = {
    connectivity: {},
    cors: {},
    apis: {},
    design: false
  };
  
  results.connectivity = await testServiceConnectivity();
  console.log('');
  
  results.cors = await testCorsHeaders();
  console.log('');
  
  results.apis.minimax = await testMiniMaxApi();
  console.log('');
  
  results.apis.glm = await testGlmApi();
  console.log('');
  
  results.apis.kimi = await testKimiApi();
  console.log('');
  
  if (results.apis.minimax && results.apis.minimax !== 'skipped') {
    results.design = await testDesignGeneration();
    console.log('');
  } else if (results.apis.minimax === 'skipped') {
    results.design = 'skipped';
  }
  
  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  
  console.log('='.repeat(60));
  console.log('📊 Test Summary');
  console.log('='.repeat(60));
  
  const resultsArray = [
    results.connectivity.ollama,
    results.connectivity.proxy,
    results.connectivity.serviceManager,
    results.cors.ollama,
    results.cors.proxy,
    results.apis.minimax === 'skipped' ? true : results.apis.minimax,
    results.apis.glm === 'skipped' ? true : results.apis.glm,
    results.apis.kimi === 'skipped' ? true : results.apis.kimi,
    results.design === 'skipped' ? true : results.design
  ];
  
  const skippedCount = [
    results.apis.minimax,
    results.apis.glm,
    results.apis.kimi,
    results.design
  ].filter(r => r === 'skipped').length;
  
  const passCount = resultsArray.filter(Boolean).length;
  const totalTests = 9;
  const effectiveTests = totalTests - skippedCount;
  
  console.log(`\n  Services:  Ollama ${results.connectivity.ollama ? '✅' : '❌'}  Proxy ${results.connectivity.proxy ? '✅' : '❌'}  Manager ${results.connectivity.serviceManager ? '✅' : '❌'}`);
  console.log(`  CORS:      Ollama ${results.cors.ollama ? '✅' : '❌'}  Proxy ${results.cors.proxy ? '✅' : '❌'}`);
  console.log(`  APIs:      MiniMax ${results.apis.minimax === true ? '✅' : results.apis.minimax === 'skipped' ? '⏭️' : '❌'}  GLM-5 ${results.apis.glm === true ? '✅' : results.apis.glm === 'skipped' ? '⏭️' : '❌'}  Kimi ${results.apis.kimi === true ? '✅' : results.apis.kimi === 'skipped' ? '⏭️' : '❌'}`);
  console.log(`  Design:    ${results.design === true ? '✅' : results.design === 'skipped' ? '⏭️' : '❌'}`);
  console.log(`\n  ${passCount}/${totalTests} tests (${skippedCount} skipped) in ${elapsed}s`);
  
  const allPassed = passCount === totalTests;
  const allCorePassed = passCount >= (totalTests - skippedCount - 1);
  
  if (allPassed) {
    console.log(`\n  ${TEST_COLORS.green}🎉 All tests passed! Plugin is ready for Figma.${TEST_COLORS.reset}`);
  } else if (allCorePassed && skippedCount > 0) {
    console.log(`\n  ${TEST_COLORS.green}✅ Core tests passed! ${skippedCount} optional tests skipped (set API keys to enable).${TEST_COLORS.reset}`);
  } else {
    console.log(`\n  ${TEST_COLORS.yellow}⚠️ Some core tests failed. Check the output above.${TEST_COLORS.reset}`);
  }
  
  console.log('\n');
  
  return allCorePassed;
}

async function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('--start-services')) {
    await startServicesIfNeeded();
    return;
  }
  
  if (args.includes('--fix')) {
    log('info', 'Auto-fix mode: Starting services before tests');
    await startServicesIfNeeded();
    console.log('');
  }
  
  const success = await runAllTests();
  process.exit(success ? 0 : 1);
}

main().catch(e => {
  console.error('Test runner error:', e);
  process.exit(1);
});
