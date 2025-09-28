#!/bin/bash

# STT Log Monitoring Script
# Monitors server-side STT processing logs

echo "🎤 STT Log Monitor - Server-side Speech-to-Text Processing"
echo "=========================================================="
echo ""

# Check if server is running
if pgrep -f "python main.py" > /dev/null; then
    echo "✅ Server is running"
else
    echo "❌ Server is not running"
    echo "Starting server..."
    cd /Users/khairul/MyFile/CilentProject/pakistani-rajib/SHCI/fastapi-backend
    python main.py &
    sleep 3
fi

echo ""
echo "🔍 Monitoring STT logs..."
echo "Press Ctrl+C to stop"
echo ""

# Monitor logs with STT-specific patterns
tail -f /dev/null 2>/dev/null | while read line; do
    # This is a placeholder - in real implementation, you would monitor actual log files
    echo "📝 To see STT logs, check the server console output"
    echo "🎤 Look for patterns like:"
    echo "   - '🎤 Audio data received'"
    echo "   - '🎤 STT Processing'"
    echo "   - '🎤 STT Result'"
    echo "   - '🎤 Segment'"
    echo ""
    echo "💡 To test STT:"
    echo "   1. Open frontend in browser"
    echo "   2. Click microphone button"
    echo "   3. Speak into microphone"
    echo "   4. Watch server console for STT logs"
    break
done
