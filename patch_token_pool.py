with open('/app/sunday/core/broker/token_pool.py', 'r') as f:
    content = f.read()

patch = """    def __init__(self):
        # provider -> list of CredentialEntry
        self._pools: Dict[str, List[CredentialEntry]] = defaultdict(list)
        # provider -> current active index
        self._current_index: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
        self._load_from_env()

    def _load_from_env(self):
        \"\"\"Load known API keys from environment variables or .env.\"\"\"
        import os
        from dotenv import load_dotenv
        
        # Load from .env if it exists
        dotenv_path = os.environ.get("DOTENV_PATH", ".env")
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
        
        # Load OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            self.add_key("openai", openai_key, "env_openai")
            
        # Load Anthropic
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.add_key("anthropic", anthropic_key, "env_anthropic")
            
        # Load SerpAPI
        serp_key = os.environ.get("SERPAPI_API_KEY")
        if serp_key:
            self.add_key("serpapi", serp_key, "env_serpapi")"""

content = content.replace("""    def __init__(self):
        # provider -> list of CredentialEntry
        self._pools: Dict[str, List[CredentialEntry]] = defaultdict(list)
        # provider -> current active index
        self._current_index: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()""", patch)

with open('/app/sunday/core/broker/token_pool.py', 'w') as f:
    f.write(content)
