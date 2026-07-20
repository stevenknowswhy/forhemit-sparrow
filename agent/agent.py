"""
LangChain-based agent with Agnes AI (primary) and OpenRouter (fallback)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.tools import tool
import logging

# Import configuration
from config import AGNES_CONFIG, OPENROUTER_CONFIG
from tools import search_and_summarize

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiProviderAgent:
    """Agent that uses Agnes AI as primary and OpenRouter as fallback"""
    
    def __init__(self, use_fallback=False):
        """
        Initialize the agent
        
        Args:
            use_fallback: If True, use OpenRouter instead of Agnes AI
        """
        self.use_fallback = use_fallback
        self.llm = self._initialize_llm()
        self.tools = self._get_tools()
        self.executor = None
    
    def _initialize_llm(self):
        """Initialize LLM with primary or fallback provider"""
        if self.use_fallback:
            logger.info("Using OpenRouter (fallback provider)")
            config = OPENROUTER_CONFIG
            provider_name = "OpenRouter"
        else:
            logger.info("Using Agnes AI (primary provider)")
            config = AGNES_CONFIG
            provider_name = "Agnes AI"
        
        try:
            llm = ChatOpenAI(
                model=config['model'],
                openai_api_key=config['api_key'],
                openai_api_base=config['base_url'],
                temperature=0.7,
                max_tokens=2048,
            )
            logger.info(f"✓ Successfully initialized {provider_name} LLM")
            return llm
        except Exception as e:
            if self.use_fallback:
                logger.error(f"✗ Failed to initialize {provider_name}: {e}")
                raise
            else:
                logger.warning(f"Primary provider failed ({provider_name}), trying fallback...")
                logger.warning(f"Error: {e}")
                # Try fallback
                return ChatOpenAI(
                    model=OPENROUTER_CONFIG['model'],
                    openai_api_key=OPENROUTER_CONFIG['api_key'],
                    openai_api_base=OPENROUTER_CONFIG['base_url'],
                    temperature=0.7,
                    max_tokens=2048,
                )
    
    def _get_tools(self):
        """Define available tools for the agent"""
        
        @tool
        def search_web(query: str) -> str:
            """Search the web for product information, pricing, and vendor details.
            
            Uses Brave Search API to find real-time pricing, availability,
            vendor reputation, and product specifications.
            
            Args:
                query: Search query (e.g., "HP 64A toner cartridge price")
                
            Returns:
                Formatted search results with titles, URLs, and snippets
            """
            return search_and_summarize(query)
        
        @tool
        def calculate(expression: str) -> str:
            """Perform mathematical calculations.
            
            Args:
                expression: Mathematical expression to evaluate
                
            Returns:
                Result of the calculation
            """
            try:
                result = eval(expression, {"__builtins__": {}}, {})
                return str(result)
            except Exception as e:
                return f"Error calculating expression: {e}"
        
        return [search_web, calculate]
    
    def initialize_agent(self):
        """Initialize the LangChain agent executor"""
        try:
            self.executor = create_agent(
                model=self.llm,
                tools=self.tools,
                system_prompt="""You are Sparrow, a professional buying agent that reduces expenses by finding the best products, vendors, and deals.

Your capabilities:
- Search the web for real-time pricing, product specs, and vendor information
- Perform mathematical calculations for cost comparisons
- Analyze products across 8 dimensions: price, quality, shipping speed, sustainability, vendor reputation, warranty, secondhand condition, and preference alignment
- Generate comparison reports with scored recommendations

Available tools:
- search_web: Search for product pricing, vendor info, and specifications online
- calculate: Perform mathematical calculations for cost comparisons

Always be thorough, evidence-based, and focused on finding the best value for the user. When comparing products, consider total cost of ownership, not just sticker price.""",
            )
            
            logger.info("✓ Agent initialized successfully")
            return self.executor
        except Exception as e:
            logger.error(f"✗ Failed to initialize agent: {e}")
            raise
    
    def run(self, query: str) -> dict:
        """Run the agent with a query
        
        Args:
            query: User input query
            
        Returns:
            Dictionary with output and metadata
        """
        if not self.executor:
            self.initialize_agent()
        
        try:
            result = self.executor.invoke({
                "messages": [("human", query)]
            })
            
            # Extract the final response
            output = result["messages"][-1].content if result["messages"] else "No response"
            
            return {
                "output": output,
                "provider": "OpenRouter (fallback)" if self.use_fallback else "Agnes AI (primary)",
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return {
                "output": f"Error: {str(e)}",
                "provider": "Unknown",
                "status": "error"
            }


def main():
    """Main function for interactive agent"""
    print("=" * 60)
    print("LangChain Agent - Agnes AI + OpenRouter Fallback")
    print("=" * 60)
    
    # Initialize agent
    agent = MultiProviderAgent(use_fallback=False)
    agent.initialize_agent()
    
    print("\nAgent is ready! Type 'quit' or 'exit' to stop.\n")
    
    # Interactive loop
    while True:
        try:
            query = input("You: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            if not query:
                continue
            
            print("\nAssistant: Thinking...\n")
            result = agent.run(query)
            
            print(f"Provider: {result['provider']}")
            print(f"Response: {result['output']}\n")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
