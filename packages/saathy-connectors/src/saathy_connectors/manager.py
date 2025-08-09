"""Connector manager for coordinating multiple connectors."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from saathy_core import ConnectorStatus
from .base import BaseConnector

logger = logging.getLogger(__name__)


class ConnectorManager:
    """Manages the lifecycle of multiple connectors."""
    
    def __init__(self):
        self.connectors: Dict[str, BaseConnector] = {}
        self._lock = asyncio.Lock()
        self._running = False
    
    async def register(self, connector: BaseConnector) -> None:
        """Register a connector with the manager."""
        async with self._lock:
            name = connector.name
            if name in self.connectors:
                logger.warning(f"Connector {name} already registered, replacing")
                # Stop existing connector if running
                existing = self.connectors[name]
                if existing.status == ConnectorStatus.ACTIVE:
                    await existing.stop()
            
            self.connectors[name] = connector
            logger.info(f"Registered connector: {name}")
    
    async def unregister(self, name: str) -> bool:
        """Unregister a connector."""
        async with self._lock:
            if name not in self.connectors:
                logger.warning(f"Connector {name} not found")
                return False
            
            connector = self.connectors[name]
            if connector.status == ConnectorStatus.ACTIVE:
                await connector.stop()
            
            del self.connectors[name]
            logger.info(f"Unregistered connector: {name}")
            return True
    
    async def start(self, name: str) -> bool:
        """Start a specific connector."""
        connector = self.connectors.get(name)
        if not connector:
            logger.error(f"Connector {name} not found")
            return False
        
        if connector.status == ConnectorStatus.ACTIVE:
            logger.info(f"Connector {name} already running")
            return True
        
        try:
            await connector.start()
            return True
        except Exception as e:
            logger.error(f"Failed to start connector {name}: {e}")
            return False
    
    async def stop(self, name: str) -> bool:
        """Stop a specific connector."""
        connector = self.connectors.get(name)
        if not connector:
            logger.error(f"Connector {name} not found")
            return False
        
        if connector.status != ConnectorStatus.ACTIVE:
            logger.info(f"Connector {name} not running")
            return True
        
        try:
            await connector.stop()
            return True
        except Exception as e:
            logger.error(f"Failed to stop connector {name}: {e}")
            return False
    
    async def start_all(self) -> Dict[str, bool]:
        """Start all registered connectors."""
        self._running = True
        results = {}
        
        tasks = []
        for name, connector in self.connectors.items():
            if connector.status != ConnectorStatus.ACTIVE:
                task = asyncio.create_task(self.start(name))
                tasks.append((name, task))
        
        for name, task in tasks:
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"Failed to start connector {name}: {e}")
                results[name] = False
        
        return results
    
    async def stop_all(self) -> Dict[str, bool]:
        """Stop all running connectors."""
        self._running = False
        results = {}
        
        tasks = []
        for name, connector in self.connectors.items():
            if connector.status == ConnectorStatus.ACTIVE:
                task = asyncio.create_task(self.stop(name))
                tasks.append((name, task))
        
        for name, task in tasks:
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"Failed to stop connector {name}: {e}")
                results[name] = False
        
        return results
    
    def get(self, name: str) -> Optional[BaseConnector]:
        """Get a connector by name."""
        return self.connectors.get(name)
    
    def list(self) -> List[str]:
        """List all registered connector names."""
        return list(self.connectors.keys())
    
    def get_status(self, name: str) -> Optional[ConnectorStatus]:
        """Get the status of a specific connector."""
        connector = self.connectors.get(name)
        return connector.status if connector else None
    
    async def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all connectors."""
        status = {}
        for name, connector in self.connectors.items():
            status[name] = await connector.get_status()
        return status
    
    def get_active_connectors(self) -> List[str]:
        """Get list of active connector names."""
        return [
            name for name, connector in self.connectors.items()
            if connector.status == ConnectorStatus.ACTIVE
        ]
    
    async def restart(self, name: str) -> bool:
        """Restart a connector."""
        if await self.stop(name):
            return await self.start(name)
        return False
    
    async def process_event(self, name: str, event_data: Dict[str, Any]) -> Any:
        """Process an event through a specific connector."""
        connector = self.connectors.get(name)
        if not connector:
            raise ValueError(f"Connector {name} not found")
        
        if connector.status != ConnectorStatus.ACTIVE:
            raise RuntimeError(f"Connector {name} is not active")
        
        return await connector.process_event(event_data)
    
    def is_running(self) -> bool:
        """Check if the manager is running."""
        return self._running
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all connectors."""
        results = {}
        for name, connector in self.connectors.items():
            try:
                # Simple check - connector is healthy if it's active
                results[name] = connector.status == ConnectorStatus.ACTIVE
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = False
        
        return results