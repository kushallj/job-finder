#!/bin/bash
# ==============================================================================
# JobFinder Mobile Access Launcher
# Allows accessing JobFinder from iPhone/Android via ngrok, Cloudflare, or Wi-Fi
# ==============================================================================

PORT=5173
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")

echo "================================================================="
echo "📱 JobFinder AI — Mobile Access Launcher"
echo "================================================================="
echo ""
echo "Option 1: Same Wi-Fi Network (No setup required)"
echo "------------------------------------------------"
echo "👉 Open this URL on your phone's browser (Safari / Chrome):"
echo "   http://${LOCAL_IP}:${PORT}"
echo ""

if command -v ngrok &> /dev/null; then
    echo "Option 2: ngrok Global Tunnel (Access from anywhere/cellular)"
    echo "------------------------------------------------------------"
    echo "Starting ngrok tunnel on port ${PORT}..."
    echo "Hit Ctrl+C to stop tunnel."
    echo ""
    ngrok http ${PORT}
elif command -v cloudflared &> /dev/null; then
    echo "Option 2: Cloudflare Quick Tunnel (Access from anywhere)"
    echo "--------------------------------------------------------"
    echo "Starting cloudflare tunnel on port ${PORT}..."
    cloudflared tunnel --url http://localhost:${PORT}
else
    echo "Option 2: Global Mobile Tunnel (ngrok / cloudflared)"
    echo "----------------------------------------------------"
    echo "To access over cellular data or outside home Wi-Fi:"
    echo "1. Install ngrok: brew install ngrok"
    echo "2. Run: ngrok http ${PORT}"
    echo "3. Open the generated https://xxxx.ngrok-free.app link on your phone!"
fi
