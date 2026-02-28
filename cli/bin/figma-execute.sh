#!/bin/bash
#
# figma-execute.sh - Execute JavaScript code in Figma via Desktop Bridge
#
# Usage:
#   figma-execute.sh "figma.createRectangle()"
#   figma-execute.sh --file script.js
#   figma-execute.sh --rectangle "#FF0000" 100 100 200 150
#   figma-execute.sh --text "Hello" 18 "#000000"
#
# Requires: Desktop Bridge plugin running in Figma, connected to figma-console MCP

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

FIGMA_BRIDGE_PORT="${FIGMA_BRIDGE_PORT:-9223}"
TIMEOUT="${TIMEOUT:-10000}"

usage() {
    echo "Usage: $0 [OPTIONS] [CODE]"
    echo ""
    echo "Execute JavaScript in Figma via Desktop Bridge MCP."
    echo ""
    echo "Options:"
    echo "  --file FILE       Execute JavaScript from file"
    echo "  --rectangle COLOR X Y W H  Create a rectangle"
    echo "  --text CONTENT FONTSIZE COLOR  Create text (at selection)"
    echo "  --frame NAME W H  Create a frame"
    echo "  --port PORT       Bridge port (default: 9223)"
    echo "  --timeout MS      Execution timeout (default: 10000)"
    echo "  --help            Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 'figma.notify(\"Hello!\")'"
    echo "  $0 --rectangle '#FF0000' 100 100 200 150"
    echo "  $0 --file my-script.js"
    exit 0
}

# Check if bridge is running
check_bridge() {
    if ! lsof -i :$FIGMA_BRIDGE_PORT >/dev/null 2>&1; then
        echo -e "${RED}Error: No bridge listening on port $FIGMA_BRIDGE_PORT${NC}"
        echo ""
        echo "Make sure:"
        echo "  1. Figma is running"
        echo "  2. Desktop Bridge plugin is active (Plugins > Development > Desktop Bridge)"
        echo "  3. figma-console MCP is running"
        exit 1
    fi
}

# Execute code via Python WebSocket client
execute_code() {
    local CODE="$1"

    python3 << PYTHON_EOF
import json
import socket
import sys
import time

port = $FIGMA_BRIDGE_PORT
timeout = $TIMEOUT

# Create WebSocket client connection
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(('127.0.0.1', port))
except Exception as e:
    print(f"Error: Cannot connect to bridge on port {port}: {e}", file=sys.stderr)
    sys.exit(1)

# Wrap code in async IIFE if not already
code = '''$CODE'''
if 'async' not in code[:50] and 'figma.' in code:
    code = f'(async() => {{ {code} }})()'

# Send as EXECUTE_CODE message
msg = json.dumps({
    "id": f"cli_{int(time.time()*1000)}",
    "method": "EXECUTE_CODE",
    "params": {"code": code, "timeout": timeout}
}) + '\\n'

try:
    sock.sendall(msg.encode())

    # Read response
    sock.settimeout(timeout / 1000 + 5)
    response = sock.recv(8192).decode()

    if response:
        resp_data = json.loads(response)
        if 'result' in resp_data:
            result = resp_data['result']
            if isinstance(result, dict) and result.get('success'):
                print(f"✓ Success: {result}")
            else:
                print(f"Response: {result}")
        elif 'error' in resp_data:
            print(f"✗ Error: {resp_data['error']}", file=sys.stderr)
            sys.exit(1)
    else:
        print("✓ Code sent (no response)")
except socket.timeout:
    print("✗ Timeout waiting for response", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    sock.close()
PYTHON_EOF
}

# Parse arguments
CODE=""
MODE="code"

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            usage
            ;;
        --port)
            FIGMA_BRIDGE_PORT="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --file)
            MODE="file"
            FILE_PATH="$2"
            shift 2
            ;;
        --rectangle)
            MODE="rectangle"
            COLOR="$2"
            X="$3"
            Y="$4"
            W="$5"
            H="$6"
            shift 6
            ;;
        --text)
            MODE="text"
            TEXT_CONTENT="$2"
            FONT_SIZE="$3"
            TEXT_COLOR="$4"
            shift 4
            ;;
        --frame)
            MODE="frame"
            FRAME_NAME="$2"
            FRAME_W="$3"
            FRAME_H="$4"
            shift 4
            ;;
        *)
            CODE="$1"
            shift
            ;;
    esac
done

check_bridge

case $MODE in
    code)
        if [ -z "$CODE" ]; then
            echo -e "${RED}Error: No code provided${NC}"
            usage
        fi
        execute_code "$CODE"
        ;;
    file)
        if [ ! -f "$FILE_PATH" ]; then
            echo -e "${RED}Error: File not found: $FILE_PATH${NC}"
            exit 1
        fi
        CODE=$(cat "$FILE_PATH")
        execute_code "$CODE"
        ;;
    rectangle)
        # Convert hex color to RGB 0-1 using Python
        HEX="${COLOR#\#}"
        RGB=$(python3 -c "h='$HEX'; print(f'{int(h[0:2],16)/255:.4f} {int(h[2:4],16)/255:.4f} {int(h[4:6],16)/255:.4f}')")
        read R G B <<< "$RGB"

        CODE="(async()=>{
            const n=figma.createRectangle();
            figma.currentPage.appendChild(n);
            n.x=$X; n.y=$Y;
            n.resize($W,$H);
            n.fills=[{type:'SOLID',color:{r:$R,g:$G,b:$B,a:1}}];
            figma.notify('✓ Rectangle created');
            return{success:true,nodeId:n.id};
        })()"
        execute_code "$CODE"
        ;;
    text)
        # Convert hex color to RGB 0-1 using Python
        HEX="${TEXT_COLOR#\#}"
        RGB=$(python3 -c "h='$HEX'; print(f'{int(h[0:2],16)/255:.4f} {int(h[2:4],16)/255:.4f} {int(h[4:6],16)/255:.4f}')")
        read R G B <<< "$RGB"

        CODE="(async()=>{
            const n=figma.createText();
            figma.currentPage.appendChild(n);
            n.characters='$TEXT_CONTENT';
            n.fontSize=$FONT_SIZE;
            n.fills=[{type:'SOLID',color:{r:$R,g:$G,b:$B,a:1}}];
            figma.notify('✓ Text created');
            return{success:true,nodeId:n.id};
        })()"
        execute_code "$CODE"
        ;;
    frame)
        CODE="(async()=>{
            const n=figma.createFrame();
            figma.currentPage.appendChild(n);
            n.name='$FRAME_NAME';
            n.resize($FRAME_W,$FRAME_H);
            figma.notify('✓ Frame created');
            return{success:true,nodeId:n.id};
        })()"
        execute_code "$CODE"
        ;;
esac
