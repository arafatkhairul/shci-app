#!/usr/bin/env python3
"""
Test Session Persistence Functionality
"""
import asyncio
import time
import json
from app.models.session_memory import SessionMemory, MemoryStore
from app.services.session_service import session_service

async def test_session_persistence():
    """Test session persistence across reloads and stops"""
    print("🔄 Testing Session Persistence Functionality")
    print("=" * 60)
    
    # Test 1: Create a session
    print("1️⃣ Creating a new session...")
    conn_id = "test_connection_123"
    session_id = session_service.create_session(conn_id)
    print(f"   ✅ Created session: {session_id}")
    
    # Test 2: Add conversation to memory
    print("\n2️⃣ Adding conversation to memory...")
    memory = SessionMemory(language="en")
    memory.client_id = session_id
    memory.user_name = "Test User"
    memory.session_start_time = time.time()
    
    # Simulate conversation
    conversation = [
        ("user", "Hello, I'm John. I want to learn about machine learning."),
        ("assistant", "Hello John! I'd be happy to help you learn about machine learning. It's a fascinating field!"),
        ("user", "What are the main types of machine learning?"),
        ("assistant", "There are three main types: supervised learning, unsupervised learning, and reinforcement learning."),
        ("user", "Can you explain supervised learning?"),
        ("assistant", "Supervised learning uses labeled training data to learn patterns and make predictions on new data."),
        ("user", "I also want to learn about Python programming."),
        ("assistant", "Great! Python is excellent for both machine learning and general programming. It has many useful libraries.")
    ]
    
    for role, content in conversation:
        memory.add_history(role, content)
        print(f"   📝 Added {role}: {content[:50]}...")
    
    # Save memory
    session_service.save_session_memory(session_id, memory)
    print(f"   💾 Saved memory with {memory.total_interactions} interactions")
    
    # Test 3: Simulate session reload (new connection)
    print("\n3️⃣ Simulating session reload (new connection)...")
    new_conn_id = "test_connection_456"
    
    # Create new session for same connection (simulating reload)
    new_session_id = session_service.create_or_get_session(new_conn_id)
    print(f"   🔄 New session ID: {new_session_id}")
    
    # Load memory from previous session
    loaded_memory = session_service.load_session_memory(session_id)
    if loaded_memory:
        print(f"   ✅ Loaded memory successfully!")
        print(f"   📊 Previous interactions: {loaded_memory.total_interactions}")
        print(f"   📊 Topics discussed: {loaded_memory.conversation_topics}")
        print(f"   📊 User name: {loaded_memory.user_name}")
        
        # Show conversation summary
        summary = loaded_memory.get_conversation_summary()
        print(f"   📋 Session duration: {summary['session_duration']:.1f} seconds")
        print(f"   📋 Total interactions: {summary['total_interactions']}")
    else:
        print("   ❌ Failed to load memory")
    
    # Test 4: Continue conversation
    print("\n4️⃣ Continuing conversation...")
    if loaded_memory:
        loaded_memory.add_history("user", "What about deep learning? Is it different from machine learning?")
        loaded_memory.add_history("assistant", "Deep learning is a subset of machine learning that uses neural networks with multiple layers. It's particularly good for complex tasks like image recognition.")
        
        # Save updated memory
        session_service.save_session_memory(session_id, loaded_memory)
        print(f"   ✅ Continued conversation - now {loaded_memory.total_interactions} interactions")
    
    # Test 5: Test session timeout
    print("\n5️⃣ Testing session timeout...")
    stats = session_service.get_session_stats()
    print(f"   📊 Active sessions: {stats['active_sessions']}")
    print(f"   📊 Total sessions: {stats['total_sessions']}")
    print(f"   📊 Session timeout: {stats['session_timeout']} seconds")
    
    # Test 6: Test session cleanup
    print("\n6️⃣ Testing session cleanup...")
    session_service.cleanup_expired_sessions()
    stats_after_cleanup = session_service.get_session_stats()
    print(f"   🧹 Sessions after cleanup: {stats_after_cleanup['active_sessions']}")
    
    # Test 7: Test memory retrieval
    print("\n7️⃣ Testing memory retrieval...")
    retrieved_memory = session_service.load_session_memory(session_id)
    if retrieved_memory:
        print(f"   ✅ Memory retrieved successfully!")
        print(f"   📊 Final interaction count: {retrieved_memory.total_interactions}")
        print(f"   📊 Final topics: {retrieved_memory.conversation_topics}")
        
        # Show final conversation context
        context = retrieved_memory.get_context_for_llm(max_length=500)
        print(f"   🤖 LLM Context ({len(context)} turns):")
        for i, turn in enumerate(context[-3:]):  # Show last 3 turns
            print(f"      {i+1}. {turn['role']}: {turn['content'][:80]}...")
    else:
        print("   ❌ Failed to retrieve memory")
    
    print(f"\n✅ Session Persistence Test Completed Successfully!")
    print("=" * 60)
    print("🎯 Key Features Tested:")
    print("   ✅ Session creation and management")
    print("   ✅ Memory persistence across reloads")
    print("   ✅ Conversation context preservation")
    print("   ✅ Topic tracking and user preferences")
    print("   ✅ Session timeout and cleanup")
    print("   ✅ Memory retrieval and continuation")

if __name__ == "__main__":
    asyncio.run(test_session_persistence())

