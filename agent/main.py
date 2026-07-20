"""
Entry point for the LangChain agent
"""
import sys
import os
from pathlib import Path

# Add agent directory to path
agent_dir = Path(__file__).parent
sys.path.insert(0, str(agent_dir))

from agent import MultiProviderAgent
from config import AGNES_CONFIG, OPENROUTER_CONFIG


def main():
    """Main entry point"""
    print("=" * 70)
    print("🐦 Sparrow — AI Expense Reduction Agent")
    print("=" * 70)
    print()
    print("Configuration:")
    print(f"  Primary Provider: Agnes AI")
    print(f"    Model: {AGNES_CONFIG['model']}")
    print(f"    Base URL: {AGNES_CONFIG['base_url']}")
    print(f"  Fallback Provider: OpenRouter")
    print(f"    Model: {OPENROUTER_CONFIG['model']}")
    print(f"    Base URL: {OPENROUTER_CONFIG['base_url']}")
    print(f"  Search: Brave Search API {'✓ configured' if os.getenv('BRAVE_SEARCH_API_KEY') else '⚠ stub mode'}")
    print()
    print("=" * 70)
    print()
    
    # Initialize agent
    print("Initializing agent...")
    agent = MultiProviderAgent(use_fallback=False)
    
    try:
        agent.initialize_agent()
        print("✓ Agent ready!\n")
    except Exception as e:
        print(f"✗ Failed to initialize agent: {e}")
        print("\nAttempting to use fallback provider (OpenRouter)...")
        agent = MultiProviderAgent(use_fallback=True)
        try:
            agent.initialize_agent()
            print("✓ Fallback agent ready!\n")
        except Exception as e2:
            print(f"✗ Fallback also failed: {e2}")
            sys.exit(1)
    
    # Interactive loop
    print("Type your messages below (or 'quit' to exit):\n")
    print("Example: \"Find the best deal on HP 64A toner cartridge\"\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!\n")
                break
            
            if not user_input:
                continue
            
            print("\n🤖 Processing...\n")
            result = agent.run(user_input)
            
            print(f"Status: {result['status'].upper()}")
            print(f"Provider: {result['provider']}")
            print(f"Response: {result['output']}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()
