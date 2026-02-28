#!/usr/bin/env node
import http from 'http'
import https from 'https'

const NVIDIA_API = 'integrate.api.nvidia.com'
const PORT = 11435

const MODELS = {
  object: 'list',
  data: [
    { id: 'moonshotai/kimi-k2-5', object: 'model', owned_by: 'moonshotai' },
    { id: 'moonshotai/kimi-k2.5', object: 'model', owned_by: 'moonshotai' }
  ]
}

const server = http.createServer((req, res) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`)
  
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization')

  if (req.method === 'OPTIONS') {
    res.writeHead(204)
    res.end()
    return
  }

  if (req.method === 'GET' && (req.url === '/v1/models' || req.url === '/health')) {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(MODELS))
    return
  }

  if (req.method === 'POST' && req.url === '/v1/chat/completions') {
    console.log('  -> MATCH! Handling POST /v1/chat/completions')
    let body = ''
    req.on('data', chunk => { body += chunk; console.log('  -> chunk received') })
    req.on('end', () => {
      console.log('  -> body complete, processing...')
      const authHeader = req.headers.authorization || ''
      const apiKey = authHeader.replace('Bearer ', '')

      if (!apiKey) {
        console.log('  -> No API key, returning 401')
        res.writeHead(401, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ error: { message: 'Missing API key' } }))
        return
      }

      console.log('  -> Proxying to NVIDIA...')

      const options = {
        hostname: NVIDIA_API,
        port: 443,
        path: '/v1/chat/completions',
        method: 'POST',
        timeout: 60000,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        }
      }

      const proxyReq = https.request(options, (proxyRes) => {
        console.log('  -> NVIDIA responded:', proxyRes.statusCode)
        res.writeHead(proxyRes.statusCode, { 'Content-Type': 'application/json' })
        proxyRes.pipe(res)
      })

      proxyReq.on('error', (e) => {
        console.error('  -> Proxy error:', e.message)
        res.writeHead(502, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ error: { message: e.message } }))
      })

      proxyReq.on('timeout', () => {
        console.error('  -> NVIDIA timeout')
        proxyReq.destroy()
        res.writeHead(504, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ error: { message: 'NVIDIA API timeout' } }))
      })

      proxyReq.write(body)
      proxyReq.end()
    })
    return
  } else {
    console.log('  -> No match, returning 404 JSON')
    res.writeHead(404, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ error: { message: 'Not found' } }))
  }
})

server.listen(PORT, () => {
  console.log(`NVIDIA NIM Proxy running on http://localhost:${PORT}`)
  console.log('Ready to proxy requests to Kimi K2.5')
})
