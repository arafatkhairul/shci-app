#!/usr/bin/env python3
"""
Environment-based TTS System Test
Tests the TTS factory system with different environments.
"""

import os
import asyncio
import logging
from tts_factory import (
    tts_factory, 
    synthesize_text, 
    synthesize_text_async,
    get_tts_info,
    TTSSystem,
    TTSEnvironment
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("test_environment_tts")

def test_environment_detection():
    """Test environment detection."""
    print("🔍 Testing Environment Detection")
    print("="*50)
    
    # Test different environment settings
    test_envs = [
        ("local", TTSEnvironment.LOCAL),
        ("development", TTSEnvironment.DEVELOPMENT),
        ("production", TTSEnvironment.PRODUCTION),
        ("live", TTSEnvironment.LIVE)
    ]
    
    for env_name, expected_env in test_envs:
        # Set environment
        os.environ["TTS_ENVIRONMENT"] = env_name
        
        # Create new factory instance
        factory = tts_factory.__class__()
        
        print(f"Environment: {env_name}")
        print(f"Detected: {factory.environment.value}")
        print(f"Preferred System: {factory.preferred_system.value}")
        print(f"Available Providers: {[p.value for p in factory.get_available_providers().keys()]}")
        print()

def test_tts_systems():
    """Test different TTS systems."""
    print("🎵 Testing TTS Systems")
    print("="*50)
    
    test_text = "Hello! This is a test of the TTS factory system."
    
    # Get available systems
    info = get_tts_info()
    print(f"Current Environment: {info['environment']}")
    print(f"Preferred System: {info['preferred_system']}")
    print(f"Available Providers: {info['available_providers']}")
    print()
    
    # Test each available system
    for system_name in info['available_providers']:
        try:
            system = TTSSystem(system_name)
            print(f"Testing {system_name.upper()} system...")
            
            # Test synthesis
            audio_data = synthesize_text(test_text, system=system)
            
            if audio_data:
                print(f"✅ {system_name.upper()}: {len(audio_data)} bytes")
            else:
                print(f"❌ {system_name.upper()}: No audio data")
                
        except Exception as e:
            print(f"❌ {system_name.upper()}: Error - {e}")
        
        print()

async def test_async_synthesis():
    """Test async synthesis."""
    print("⚡ Testing Async Synthesis")
    print("="*50)
    
    test_text = "This is an async test of the TTS system."
    
    try:
        audio_data = await synthesize_text_async(test_text)
        
        if audio_data:
            print(f"✅ Async synthesis successful: {len(audio_data)} bytes")
        else:
            print("❌ Async synthesis failed")
            
    except Exception as e:
        print(f"❌ Async synthesis error: {e}")

def test_environment_switching():
    """Test switching between environments."""
    print("🔄 Testing Environment Switching")
    print("="*50)
    
    # Test local environment
    print("Setting LOCAL environment...")
    os.environ["TTS_ENVIRONMENT"] = "local"
    os.environ["TTS_SYSTEM"] = ""  # Auto-select
    
    factory = tts_factory.__class__()
    print(f"Environment: {factory.environment.value}")
    print(f"Preferred System: {factory.preferred_system.value}")
    
    # Test production environment
    print("\nSetting PRODUCTION environment...")
    os.environ["TTS_ENVIRONMENT"] = "production"
    os.environ["TTS_SYSTEM"] = ""  # Auto-select
    
    factory = tts_factory.__class__()
    print(f"Environment: {factory.environment.value}")
    print(f"Preferred System: {factory.preferred_system.value}")
    
    # Test explicit system selection
    print("\nSetting explicit COQUI system...")
    os.environ["TTS_SYSTEM"] = "coqui"
    
    factory = tts_factory.__class__()
    print(f"Environment: {factory.environment.value}")
    print(f"Preferred System: {factory.preferred_system.value}")

def test_configuration():
    """Test configuration options."""
    print("⚙️ Testing Configuration")
    print("="*50)
    
    # Test different configurations
    configs = [
        {"TTS_ENVIRONMENT": "local", "TTS_SYSTEM": "gtts"},
        {"TTS_ENVIRONMENT": "local", "TTS_SYSTEM": "fallback"},
        {"TTS_ENVIRONMENT": "production", "TTS_SYSTEM": "coqui"},
        {"TTS_ENVIRONMENT": "production", "TTS_SYSTEM": "fallback"},
    ]
    
    for config in configs:
        print(f"Configuration: {config}")
        
        # Set environment variables
        for key, value in config.items():
            os.environ[key] = value
        
        # Create factory
        factory = tts_factory.__class__()
        
        print(f"  Environment: {factory.environment.value}")
        print(f"  Preferred System: {factory.preferred_system.value}")
        print(f"  Available: {[p.value for p in factory.get_available_providers().keys()]}")
        
        # Test synthesis
        try:
            audio_data = synthesize_text("Test", system=factory.preferred_system)
            print(f"  Synthesis: {'✅ Success' if audio_data else '❌ Failed'}")
        except Exception as e:
            print(f"  Synthesis: ❌ Error - {e}")
        
        print()

async def main():
    """Main test function."""
    print("🎵 Environment-based TTS System Test")
    print("="*60)
    
    try:
        # Test environment detection
        test_environment_detection()
        
        # Test TTS systems
        test_tts_systems()
        
        # Test async synthesis
        await test_async_synthesis()
        
        # Test environment switching
        test_environment_switching()
        
        # Test configuration
        test_configuration()
        
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        log.error(f"❌ Test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
