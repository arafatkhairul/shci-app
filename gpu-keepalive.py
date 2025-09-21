#!/usr/bin/env python3
"""
GPU Keep-Alive Script
Keeps GPU active to prevent idle shutdown and reduce first-time load delays
"""
import time
import os
import sys
import threading
import signal
from datetime import datetime

try:
    import torch
    import pynvml
    TORCH_AVAILABLE = True
    PYNVML_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    PYNVML_AVAILABLE = False
    print("Installing required packages...")
    os.system("pip install torch pynvml")
    import torch
    import pynvml

class GPUKeepAlive:
    def __init__(self, interval=30, gpu_id=0):
        self.interval = interval
        self.gpu_id = gpu_id
        self.running = True
        self.thread = None
        
        # Initialize NVML
        if PYNVML_AVAILABLE:
            pynvml.nvmlInit()
            self.device_count = pynvml.nvmlDeviceGetCount()
            print(f"Found {self.device_count} GPU(s)")
        else:
            print("pynvml not available")
            
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.running = False
        sys.exit(0)
    
    def keep_gpu_active(self):
        """Keep GPU active with small operations"""
        try:
            if TORCH_AVAILABLE and torch.cuda.is_available():
                # Small tensor operation to keep GPU active
                device = torch.device(f'cuda:{self.gpu_id}')
                x = torch.randn(10, 10, device=device)
                y = torch.randn(10, 10, device=device)
                z = torch.mm(x, y)
                del x, y, z
                torch.cuda.empty_cache()
                return True
            else:
                print("❌ CUDA not available")
                return False
        except Exception as e:
            print(f"❌ GPU operation failed: {e}")
            return False
    
    def get_gpu_status(self):
        """Get GPU status information"""
        try:
            if PYNVML_AVAILABLE and self.device_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(self.gpu_id)
                
                # Get utilization
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                
                # Get memory info
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                mem_used = mem_info.used / 1024**3
                mem_total = mem_info.total / 1024**3
                
                # Get temperature
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                
                # Get power
                power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000
                
                return {
                    'gpu_util': util.gpu,
                    'memory_util': util.memory,
                    'memory_used': mem_used,
                    'memory_total': mem_total,
                    'temperature': temp,
                    'power': power
                }
            else:
                return None
        except Exception as e:
            print(f"❌ Failed to get GPU status: {e}")
            return None
    
    def keepalive_worker(self):
        """Background worker to keep GPU active"""
        print(f"🔄 Starting GPU keep-alive worker (interval: {self.interval}s)")
        
        while self.running:
            try:
                # Keep GPU active
                if self.keep_gpu_active():
                    status = self.get_gpu_status()
                    if status:
                        print(f"✅ GPU {self.gpu_id} active - "
                              f"Util: {status['gpu_util']}% | "
                              f"Mem: {status['memory_used']:.1f}GB/{status['memory_total']:.1f}GB | "
                              f"Temp: {status['temperature']}°C | "
                              f"Power: {status['power']:.1f}W")
                    else:
                        print(f"✅ GPU {self.gpu_id} active (status unavailable)")
                else:
                    print(f"❌ Failed to keep GPU {self.gpu_id} active")
                
                # Wait for next interval
                for _ in range(self.interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                print(f"❌ Keep-alive error: {e}")
                time.sleep(5)
    
    def start(self):
        """Start the keep-alive service"""
        print("🚀 Starting GPU Keep-Alive Service")
        print(f"📊 GPU ID: {self.gpu_id}")
        print(f"⏱️  Interval: {self.interval} seconds")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        # Start background thread
        self.thread = threading.Thread(target=self.keepalive_worker, daemon=True)
        self.thread.start()
        
        # Main loop
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping GPU keep-alive service...")
            self.running = False
            if self.thread:
                self.thread.join()
            print("✅ GPU keep-alive service stopped")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='GPU Keep-Alive Service')
    parser.add_argument('--interval', type=int, default=30, 
                       help='Keep-alive interval in seconds (default: 30)')
    parser.add_argument('--gpu-id', type=int, default=0, 
                       help='GPU ID to keep alive (default: 0)')
    
    args = parser.parse_args()
    
    # Validate GPU ID
    if TORCH_AVAILABLE and torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        if args.gpu_id >= gpu_count:
            print(f"❌ GPU ID {args.gpu_id} not available. Found {gpu_count} GPU(s)")
            sys.exit(1)
    else:
        print("❌ CUDA not available")
        sys.exit(1)
    
    # Start keep-alive service
    keepalive = GPUKeepAlive(interval=args.interval, gpu_id=args.gpu_id)
    keepalive.start()

if __name__ == "__main__":
    main()
