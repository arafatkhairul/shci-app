#!/bin/bash
# ===================================================================
# Basic GPU Keep-Alive Script (No Python dependencies)
# ===================================================================

# Configuration
INTERVAL=30
GPU_ID=0

echo "🚀 Starting Basic GPU Keep-Alive Service"
echo "⏱️  Interval: $INTERVAL seconds"
echo "Press Ctrl+C to stop"
echo "=" * 60

# Function to keep GPU active
keep_gpu_active() {
    # Use nvidia-smi to keep GPU active
    nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ GPU $GPU_ID active - $(date)"
    else
        echo "❌ GPU $GPU_ID not responding - $(date)"
    fi
}

# Main loop
while true; do
    keep_gpu_active
    sleep $INTERVAL
done
