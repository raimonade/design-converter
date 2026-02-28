#!/bin/bash
# AI Designer - Start all services
# Run this before using the plugin in Figma

echo "🚀 Starting AI Designer services..."
echo ""

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "📦 Starting Ollama with CORS enabled..."
    OLLAMA_ORIGINS="*" ollama serve &
    sleep 2
else
    echo "✅ Ollama already running"
fi

# Start the NVIDIA proxy for Kimi
echo ""
echo "🔄 Starting NVIDIA NIM proxy for Kimi K2.5..."
node proxy/server.js &
PROXY_PID=$!

echo ""
echo "✅ All services started!"
echo ""
echo "📋 Services running:"
echo "   • Ollama (MiniMax M2.5): http://localhost:11434"
echo "   • NVIDIA Proxy (Kimi):   http://localhost:11435"
echo ""
echo "⌨️  Press Ctrl+C to stop all services"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping services...'; kill $PROXY_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait
