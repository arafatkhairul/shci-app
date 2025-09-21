#!/usr/bin/env python3
"""
Test Enhanced Memory Functionality
"""
import asyncio
import json
from app.models.session_memory import SessionMemory, MemoryStore

async def test_enhanced_memory():
    """Test the enhanced memory functionality"""
    print("🧠 Testing Enhanced Memory Functionality")
    print("=" * 50)
    
    # Create a test memory instance
    memory = SessionMemory(language="en")
    memory.client_id = "test_user_123"
    memory.user_name = "John Doe"
    
    print(f"✅ Created memory for user: {memory.user_name}")
    
    # Simulate a conversation
    conversation_turns = [
        ("user", "Hello, my name is John. I'm interested in learning about Python programming."),
        ("assistant", "Hello John! I'd be happy to help you learn Python programming. What specific aspect would you like to start with?"),
        ("user", "I want to learn about data structures like lists and dictionaries."),
        ("assistant", "Great choice! Lists and dictionaries are fundamental data structures in Python. Lists are ordered collections, while dictionaries store key-value pairs."),
        ("user", "Can you explain how to create a dictionary?"),
        ("assistant", "Sure! You can create a dictionary using curly braces {} or the dict() function. For example: my_dict = {'name': 'John', 'age': 30}"),
        ("user", "What about lists? How do I add items to a list?"),
        ("assistant", "Lists are created with square brackets []. You can add items using append() method or extend() for multiple items. Example: my_list = [1, 2, 3]; my_list.append(4)"),
        ("user", "I also want to learn about machine learning. Is Python good for that?"),
        ("assistant", "Absolutely! Python is excellent for machine learning. Libraries like scikit-learn, TensorFlow, and PyTorch make it very popular in the ML community.")
    ]
    
    # Add conversation turns to memory
    for role, content in conversation_turns:
        memory.add_history(role, content)
        print(f"📝 Added {role}: {content[:50]}...")
    
    print(f"\n📊 Memory Statistics:")
    print(f"   Total Interactions: {memory.total_interactions}")
    print(f"   Conversation Length: {len(memory.conversation_context)}")
    print(f"   Topics Discussed: {memory.conversation_topics}")
    print(f"   Session Duration: {memory.last_interaction_time - memory.session_start_time:.1f} seconds")
    
    # Test conversation summary
    summary = memory.get_conversation_summary()
    print(f"\n📋 Conversation Summary:")
    print(json.dumps(summary, indent=2, default=str))
    
    # Test context for LLM
    llm_context = memory.get_context_for_llm(max_length=500)
    print(f"\n🤖 LLM Context ({len(llm_context)} turns):")
    for i, turn in enumerate(llm_context):
        print(f"   {i+1}. {turn['role']}: {turn['content'][:100]}...")
    
    # Test memory persistence
    print(f"\n💾 Testing Memory Persistence:")
    memory_store = MemoryStore("test_user_123")
    memory_store.save(memory)
    print("   ✅ Memory saved to database")
    
    # Load memory back
    loaded_data = memory_store.load()
    if loaded_data:
        new_memory = SessionMemory()
        new_memory.load_from_dict(loaded_data)
        print("   ✅ Memory loaded from database")
        print(f"   📊 Loaded - Interactions: {new_memory.total_interactions}, Topics: {len(new_memory.conversation_topics)}")
    else:
        print("   ❌ Failed to load memory from database")
    
    # Test enhanced context
    enhanced_context = memory.get_enhanced_context(max_turns=5)
    print(f"\n🔍 Enhanced Context (last 5 turns):")
    for i, turn in enumerate(enhanced_context):
        print(f"   {i+1}. {turn['role']} (ID: {turn['interaction_id']}): {turn['content'][:80]}...")
        print(f"      Timestamp: {turn['timestamp']}, Duration: {turn['session_duration']:.1f}s")
    
    print(f"\n✅ Enhanced Memory Test Completed Successfully!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_enhanced_memory())

