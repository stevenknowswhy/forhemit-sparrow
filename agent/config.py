"""
Agent configuration for Agnes AI + OpenRouter fallback
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Agnes AI Configuration (Primary Provider)
# Note: Base URL should end with /v1, not /v1/chat/completions
# The /chat/completions path is added automatically by the OpenAI SDK
AGNES_CONFIG = {
    'api_key': os.getenv('AGNES_API_KEY'),
    'base_url': os.getenv('AGNES_BASE_URL', 'https://apihub.agnes-ai.com/v1'),
    'model': os.getenv('PRIMARY_MODEL', 'agnes-2.0-flash'),
}

# OpenRouter Configuration (Fallback Provider)
OPENROUTER_CONFIG = {
    'api_key': os.getenv('OPENROUTER_API_KEY'),
    'base_url': os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
    'model': os.getenv('FALLBACK_MODEL', 'openrouter/free'),
}

# Validate API keys
def validate_config():
    """Ensure all required configuration is present"""
    errors = []
    
    if not AGNES_CONFIG['api_key']:
        errors.append("Missing AGNES_API_KEY in .env file")
    
    if not OPENROUTER_CONFIG['api_key']:
        errors.append("Missing OPENROUTER_API_KEY in .env file")
    
    if errors:
        raise ValueError("\n".join(errors))
    
    return True

# Initialize configuration
try:
    validate_config()
    print("✓ Configuration validated successfully")
except ValueError as e:
    print(f"✗ Configuration error: {e}")
    raise
