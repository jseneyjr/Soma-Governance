"""Inference provider abstraction layer for Soma."""
import os
import sys
from abc import ABC, abstractmethod

def read_config_key(workspace, key):
    if not workspace:
        return None
    
    # Check soma.conf
    conf_path = os.path.join(workspace, 'soma.conf')
    if os.path.exists(conf_path):
        with open(conf_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}=") and not line.startswith('#'):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    
    # Check .soma/credentials.conf
    creds_path = os.path.join(workspace, '.soma', 'credentials.conf')
    if os.path.exists(creds_path):
        with open(creds_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}=") and not line.startswith('#'):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    
    return None

def resolve_key(workspace, env_keys):
    for key in env_keys:
        val = os.environ.get(key)
        if val:
            return val
        val = read_config_key(workspace, key)
        if val:
            return val
    return None

class InferenceProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, model: str = None) -> str:
        pass
        
    @abstractmethod
    def count_tokens(self, text: str, model: str = None) -> int:
        pass

class GeminiProvider(InferenceProvider):
    def __init__(self, api_key=None):
        try:
            from google import genai
            if api_key:
                self.client = genai.Client(api_key=api_key)
            else:
                self.client = genai.Client()
        except ImportError:
            raise ImportError("google-genai package required. Install with: pip install google-genai")

    def generate(self, prompt: str, model: str = None) -> str:
        model_name = model or "gemini-2.0-flash"
        response = self.client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text

    def count_tokens(self, text: str, model: str = None) -> int:
        model_name = model or "gemini-2.0-flash"
        response = self.client.models.count_tokens(model=model_name, contents=text)
        return response.total_tokens

class AnthropicProvider(InferenceProvider):
    def __init__(self, api_key=None):
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")

    def generate(self, prompt: str, model: str = None) -> str:
        model_name = model or "claude-3-5-sonnet-latest"
        response = self.client.messages.create(
            model=model_name,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
        
    def count_tokens(self, text: str, model: str = None) -> int:
        return int(len(text.split()) * 1.35)

class OpenAIProvider(InferenceProvider):
    def __init__(self, api_key=None, base_url=None):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")

    def generate(self, prompt: str, model: str = None) -> str:
        model_name = model or "gpt-4o"
        response = self.client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
        
    def count_tokens(self, text: str, model: str = None) -> int:
        return int(len(text.split()) * 1.35)

class PromptOnlyProvider(InferenceProvider):
    def generate(self, prompt: str, model: str = None) -> str:
        print("\n--- PROMPT TO MANUALLY PASTE ---")
        print(prompt)
        print("--------------------------------\n")
        print("Please paste the response below (end with EOF / Ctrl+D):")
        return sys.stdin.read().strip()
        
    def count_tokens(self, text: str, model: str = None) -> int:
        return int(len(text.split()) * 1.35)

def resolve_provider(workspace=None, provider_name=None):
    """Resolve the appropriate inference provider."""
    # Explicit override
    explicit_provider = provider_name or resolve_key(workspace, ["SOMA_INFERENCE_PROVIDER"])
    
    if explicit_provider == "gemini":
        key = resolve_key(workspace, ["GEMINI_API_KEY", "GOOGLE_API_KEY"])
        return GeminiProvider(api_key=key)
    elif explicit_provider == "anthropic":
        key = resolve_key(workspace, ["ANTHROPIC_API_KEY"])
        return AnthropicProvider(api_key=key)
    elif explicit_provider == "openai":
        key = resolve_key(workspace, ["OPENAI_API_KEY"])
        base_url = resolve_key(workspace, ["OPENAI_BASE_URL"])
        return OpenAIProvider(api_key=key, base_url=base_url)
    elif explicit_provider == "prompt-only":
        return PromptOnlyProvider()
        
    # Auto-resolve
    gemini_key = resolve_key(workspace, ["GEMINI_API_KEY", "GOOGLE_API_KEY"])
    if gemini_key:
        return GeminiProvider(api_key=gemini_key)
        
    anthropic_key = resolve_key(workspace, ["ANTHROPIC_API_KEY"])
    if anthropic_key:
        return AnthropicProvider(api_key=anthropic_key)
        
    openai_key = resolve_key(workspace, ["OPENAI_API_KEY"])
    if openai_key:
        base_url = resolve_key(workspace, ["OPENAI_BASE_URL"])
        return OpenAIProvider(api_key=openai_key, base_url=base_url)
        
    # Try Gemini ADC
    try:
        return GeminiProvider(api_key=None)
    except Exception:
        pass
        
    return PromptOnlyProvider()
