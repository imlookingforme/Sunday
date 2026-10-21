from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        pass
        
    @property
    @abstractmethod
    def risk_level(self):
        pass
        
    @property
    @abstractmethod
    def persona(self) -> str:
        pass
        
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        pass
