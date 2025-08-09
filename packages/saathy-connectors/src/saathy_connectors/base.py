"""Base connector interface and implementation."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from saathy_core import (
    BaseConnector as CoreBaseConnector,
    ConnectorStatus,
    ProcessedContent,
)


class BaseConnector(CoreBaseConnector):
    """Enhanced base connector with common functionality."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self._start_time: Optional[datetime] = None
        self._processed_count = 0
        self._error_count = 0
        self._last_error: Optional[str] = None
    
    async def start(self) -> None:
        """Start the connector."""
        self.logger.info(f"Starting {self.name} connector...")
        self._start_time = datetime.utcnow()
        self.status = ConnectorStatus.STARTING
        
        try:
            # Validate configuration
            if not await self.validate_config():
                raise ValueError("Invalid configuration")
            
            # Perform connector-specific startup
            await self._start_connector()
            
            self.status = ConnectorStatus.ACTIVE
            self.logger.info(f"{self.name} connector started successfully")
        except Exception as e:
            self.status = ConnectorStatus.ERROR
            self._last_error = str(e)
            self.logger.error(f"Failed to start {self.name} connector: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the connector."""
        self.logger.info(f"Stopping {self.name} connector...")
        self.status = ConnectorStatus.STOPPING
        
        try:
            # Perform connector-specific shutdown
            await self._stop_connector()
            
            self.status = ConnectorStatus.INACTIVE
            self.logger.info(f"{self.name} connector stopped successfully")
        except Exception as e:
            self.status = ConnectorStatus.ERROR
            self._last_error = str(e)
            self.logger.error(f"Error stopping {self.name} connector: {e}")
            raise
    
    async def get_status(self) -> Dict[str, Any]:
        """Get the current status of the connector."""
        uptime = None
        if self._start_time and self.status == ConnectorStatus.ACTIVE:
            uptime = (datetime.utcnow() - self._start_time).total_seconds()
        
        return {
            "name": self.name,
            "status": self.status.value,
            "uptime_seconds": uptime,
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "last_error": self._last_error,
            "config": self._get_safe_config(),
        }
    
    async def process_event(self, event_data: Dict[str, Any]) -> List[ProcessedContent]:
        """Process an event and return processed content."""
        try:
            # Validate event
            if not self._validate_event(event_data):
                self.logger.warning(f"Invalid event data: {event_data}")
                return []
            
            # Process the event
            contents = await self._process_event(event_data)
            
            # Update metrics
            self._processed_count += len(contents)
            
            return contents
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            self.logger.error(f"Error processing event: {e}")
            raise
    
    @abstractmethod
    async def _start_connector(self) -> None:
        """Connector-specific startup logic."""
        pass
    
    @abstractmethod
    async def _stop_connector(self) -> None:
        """Connector-specific shutdown logic."""
        pass
    
    @abstractmethod
    async def _process_event(self, event_data: Dict[str, Any]) -> List[ProcessedContent]:
        """Connector-specific event processing."""
        pass
    
    def _validate_event(self, event_data: Dict[str, Any]) -> bool:
        """Validate event data. Override for connector-specific validation."""
        return event_data is not None and isinstance(event_data, dict)
    
    def _get_safe_config(self) -> Dict[str, Any]:
        """Get configuration with sensitive values masked."""
        safe_config = {}
        for key, value in self.config.items():
            if any(sensitive in key.lower() for sensitive in ['token', 'secret', 'key', 'password']):
                safe_config[key] = "***" if value else None
            else:
                safe_config[key] = value
        return safe_config