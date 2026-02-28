#!/bin/bash

SELF_HEALING_TEST_DIR="/Users/william/Projects Parent Folder/figma-ai-designer"
LOG_FILE="$SELF_HEALING_TEST_DIR/tests/test-loop.log"
MAX_RETRIES=3
RETRY_DELAY=5

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_and_start_services() {
  log "Checking services..."
  
  OLLAMA_RUNNING=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags 2>/dev/null)
  if [ "$OLLAMA_RUNNING" != "200" ]; then
    log "Ollama not running, starting with CORS..."
    OLLAMA_ORIGINS="*" ollama serve &
    sleep 2
  fi
  
  PROXY_RUNNING=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:11435/ 2>/dev/null)
  if [ "$PROXY_RUNNING" == "000" ]; then
    log "Proxy not running, starting..."
    cd "$SELF_HEALING_TEST_DIR" && node proxy/server.js &
    sleep 1
  fi
  
  SM_RUNNING=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:11436/status 2>/dev/null)
  if [ "$SM_RUNNING" != "200" ]; then
    log "Service Manager not running, starting..."
    cd "$SELF_HEALING_TEST_DIR" && node service-manager/server.js &
    sleep 1
  fi
  
  log "Services status: Ollama=$OLLAMA_RUNNING, Proxy=$PROXY_RUNNING, SM=$SM_RUNNING"
}

run_tests() {
  cd "$SELF_HEALING_TEST_DIR"
  node tests/test-plugin.js 2>&1
  return $?
}

fix_and_retry() {
  local attempt=$1
  log "Attempt $attempt failed, trying to fix..."
  
  check_and_start_services
  
  if [ $attempt -lt $MAX_RETRIES ]; then
    log "Waiting ${RETRY_DELAY}s before retry..."
    sleep $RETRY_DELAY
    return 0
  fi
  return 1
}

main() {
  log "=========================================="
  log "Starting Self-Healing Test Loop"
  log "=========================================="
  
  check_and_start_services
  
  attempt=1
  while [ $attempt -le $MAX_RETRIES ]; do
    log "Running tests (attempt $attempt/$MAX_RETRIES)..."
    
    if run_tests; then
      log "✅ All tests passed!"
      exit 0
    fi
    
    if ! fix_and_retry $attempt; then
      log "❌ Max retries reached. Tests failed."
      exit 1
    fi
    
    ((attempt++))
  done
  
  log "❌ Tests failed after $MAX_RETRIES attempts"
  exit 1
}

main "$@"
