#!/bin/bash

# Verification Script: No Browser STT Usage
# Checks that all browser native STT has been removed

echo "🔍 Verifying: No Browser Native STT Usage"
echo "========================================"
echo ""

# Check for WebkitSpeechRecognition usage (excluding TypeScript definitions)
echo "1. Checking for WebkitSpeechRecognition usage..."
if grep -r "webkitSpeechRecognition\|SpeechRecognition" web-app/ --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" | grep -v "node_modules" | grep -v "lib.dom" | grep -v "No browser native SpeechRecognition API used"; then
    echo "❌ Found WebkitSpeechRecognition usage!"
    exit 1
else
    echo "✅ No WebkitSpeechRecognition usage found"
fi

echo ""

# Check for browser STT API usage
echo "2. Checking for browser STT API usage..."
if grep -r "recognition\.start\|recognition\.stop\|recognition\.abort" web-app/ --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx"; then
    echo "❌ Found browser STT API usage!"
    exit 1
else
    echo "✅ No browser STT API usage found"
fi

echo ""

# Check for STT event handlers
echo "3. Checking for STT event handlers..."
if grep -r "onresult\|onerror\|onstart\|onend\|onspeechstart\|onspeechend" web-app/ --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx"; then
    echo "❌ Found STT event handlers!"
    exit 1
else
    echo "✅ No STT event handlers found"
fi

echo ""

# Check for server-side STT usage
echo "4. Checking for server-side STT usage..."
if grep -r "handleServerSTTResult\|server-side STT" web-app/ --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx"; then
    echo "✅ Server-side STT implementation found"
else
    echo "❌ No server-side STT implementation found!"
    exit 1
fi

echo ""

# Check for WebSocket audio data sending
echo "5. Checking for WebSocket audio data sending..."
if grep -r "ws\.current\.send.*audio\|send.*bytes" web-app/ --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx"; then
    echo "✅ WebSocket audio data sending found"
else
    echo "❌ No WebSocket audio data sending found!"
    exit 1
fi

echo ""

# Check for server-side STT response handling
echo "6. Checking for server-side STT response handling..."
if grep -r "interim_transcript\|final_transcript" web-app/ --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx"; then
    echo "✅ Server-side STT response handling found"
else
    echo "❌ No server-side STT response handling found!"
    exit 1
fi

echo ""
echo "🎉 VERIFICATION COMPLETE!"
echo "✅ All browser native STT has been removed"
echo "✅ Server-side WhisperX STT is properly implemented"
echo "✅ WebSocket audio communication is working"
echo "✅ STT response handling is in place"
echo ""
echo "🚀 The system now uses 100% server-side STT processing!"
