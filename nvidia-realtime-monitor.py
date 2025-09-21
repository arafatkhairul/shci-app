#!/usr/bin/env python3
"""
Nvidia GPU Real-time Monitor
"""
import time
import os
import sys
from datetime import datetime

try:
    import pynvml
except ImportError:
    print("Installing pynvml...")
    os.system("pip install pynvml")
    import pynvml

class NvidiaMonitor:
    def __init__(self):
        pynvml.nvmlInit()
        self.device_count = pynvml.nvmlDeviceGetCount()
        print(f"Found {self.device_count} GPU(s)")
        
    def get_gpu_info(self, device_id=0):
        """Get comprehensive GPU information"""
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(device_id)
            
            # Basic info
            name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
            
            # Temperature
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            # Utilization
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_util = util.gpu
            memory_util = util.memory
            
            # Memory info
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            mem_used = mem_info.used / 1024**3  # Convert to GB
            mem_total = mem_info.total / 1024**3  # Convert to GB
            mem_free = mem_info.free / 1024**3  # Convert to GB
            
            # Power
            power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000  # Convert to W
            
            # Clock speeds
            graphics_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS)
            memory_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_MEM)
            
            # Fan speed
            fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)
            
            return {
                'name': name,
                'temperature': temp,
                'gpu_util': gpu_util,
                'memory_util': memory_util,
                'memory_used': mem_used,
                'memory_total': mem_total,
                'memory_free': mem_free,
                'power': power,
                'graphics_clock': graphics_clock,
                'memory_clock': memory_clock,
                'fan_speed': fan_speed
            }
        except Exception as e:
            return {'error': str(e)}
    
    def display_info(self, gpu_info, device_id=0):
        """Display GPU information in a formatted way"""
        if 'error' in gpu_info:
            print(f"❌ GPU {device_id}: Error - {gpu_info['error']}")
            return
            
        print(f"\n🎮 GPU {device_id}: {gpu_info['name']}")
        print(f"🌡️  Temperature: {gpu_info['temperature']}°C")
        print(f"⚡ GPU Utilization: {gpu_info['gpu_util']}%")
        print(f"💾 Memory Utilization: {gpu_info['memory_util']}%")
        print(f"🧠 Memory: {gpu_info['memory_used']:.2f}GB / {gpu_info['memory_total']:.2f}GB ({gpu_info['memory_free']:.2f}GB free)")
        print(f"🔋 Power: {gpu_info['power']:.1f}W")
        print(f"⏰ Graphics Clock: {gpu_info['graphics_clock']} MHz")
        print(f"⏰ Memory Clock: {gpu_info['memory_clock']} MHz")
        print(f"🌀 Fan Speed: {gpu_info['fan_speed']}%")
    
    def monitor_all_gpus(self, interval=1):
        """Monitor all GPUs in real-time"""
        print("🚀 Starting Nvidia GPU Real-time Monitor")
        print("Press Ctrl+C to stop")
        print("=" * 80)
        
        try:
            while True:
                # Clear screen
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Display timestamp
                print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 80)
                
                # Monitor each GPU
                for i in range(self.device_count):
                    gpu_info = self.get_gpu_info(i)
                    self.display_info(gpu_info, i)
                    if i < self.device_count - 1:
                        print("-" * 80)
                
                print("=" * 80)
                print(f"⏱️  Refresh interval: {interval} second(s)")
                print("Press Ctrl+C to stop")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        finally:
            pynvml.nvmlShutdown()

def main():
    if len(sys.argv) > 1:
        try:
            interval = float(sys.argv[1])
        except ValueError:
            print("Invalid interval. Using default 1 second.")
            interval = 1
    else:
        interval = 1
    
    monitor = NvidiaMonitor()
    monitor.monitor_all_gpus(interval)

if __name__ == "__main__":
    main()
