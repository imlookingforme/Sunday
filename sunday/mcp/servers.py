"""MCP server registry for Sunday."""

from typing import Dict, Any


class MCPServerRegistry:
    """Registry for MCP server configurations."""
    
    def __init__(self):
        """Initialize MCP server registry with default servers."""
        self.servers: Dict[str, Dict[str, Any]] = {
            "filesystem": {
                "name": "filesystem",
                "description": "Extended file operations",
                "url": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "sunday/data"]
            },
            "github": {
                "name": "github",
                "description": "GitHub issues, PRs, repos",
                "url": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_TOKEN": "{{secret:github_token}"}
            },
            "notion": {
                "name": "notion",
                "description": "Notion API integration",
                "url": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-notion"],
                "env": {"NOTION_API_KEY": "{{secret:notion_api_key}"}
            },
            "google-workspace": {
                "name": "google-workspace",
                "description": "Gmail, Calendar, Docs",
                "url": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-gmail"],
                "env": {
                    "GMAIL_ACCESS_TOKEN": "{{secret:gmail_access_token}}",
                    "GMAIL_REFRESH_TOKEN": "{{secret:gmail_refresh_token}}"
                }
            },
            "microsoft-graph": {
                "name": "microsoft-graph",
                "description": "Outlook, Teams, OneDrive",
                "url": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-microsoft-graph"],
                "env": {
                    "MICROSOFT_CLIENT_ID": "{{secret:microsoft_client_id}}",
                    "MICROSOFT_CLIENT_SECRET": "{{secret:microsoft_client_secret}}"
                }
            },
            "brave-search": {
                "name": "brave-search",
                "description": "Brave web search",
                "url": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                "env": {"BRAVE_API_KEY": "{{secret:brave_api_key}"}
            },
            "postgres": {
                "name": "postgres",
                "description": "PostgreSQL database",
                "url": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-postgres"],
                "env": {
                    "POSTGRES_CONNECTION_STRING": "{{secret:postgres_connection_string}}"
                }
            }
        }
    
    def register_server(self, name: str, config: Dict[str, Any]) -> None:
        """Register a custom MCP server.
        
        Args:
            name: Server name
            config: Server configuration
        """
        self.servers[name] = config
    
    def get_server(self, name: str) -> Dict[str, Any]:
        """Get server configuration.
        
        Args:
            name: Server name
            
        Returns:
            Server configuration
        """
        return self.servers.get(name, {})
    
    def list_servers(self) -> Dict[str, Dict[str, Any]]:
        """List all registered servers.
        
        Returns:
            Dictionary of all servers
        """
        return self.servers
    
    def remove_server(self, name: str) -> bool:
        """Remove a server.
        
        Args:
            name: Server name
            
        Returns:
            True if removed, False if not found
        """
        if name in self.servers:
            del self.servers[name]
            return True
        return False
