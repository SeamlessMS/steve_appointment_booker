import openai
from config import get_config

config = get_config()
api_key = config.get('LLM_API_KEY')

client = openai.OpenAI(api_key=api_key)

try:
    # Test listing models
    print("Testing API key by listing models...")
    models = client.models.list()
    print("Success! Available models:")
    for model in models.data:
        print(f"- {model.id}")
except Exception as e:
    print(f"Error: {str(e)}") 