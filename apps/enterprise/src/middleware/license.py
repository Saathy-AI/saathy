"""License validation middleware for enterprise features."""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from saathy_core import Feature, FeatureTier


class LicenseMiddleware:
    """Middleware to validate enterprise licenses and feature access."""
    
    def __init__(
        self,
        license_key: Optional[str] = None,
        feature_flags: Optional[Dict[str, bool]] = None,
    ):
        self.license_key = license_key
        self.feature_flags = feature_flags or {}
        self._license_info: Optional[Dict[str, Any]] = None
        
        # Validate license on initialization
        if license_key:
            self._license_info = self._validate_license(license_key)
    
    def _validate_license(self, license_key: str) -> Dict[str, Any]:
        """Validate license key and return license info."""
        # In production, this would check against a license server
        # For now, use a simple hash-based validation
        
        # Example license format: SAATHY-TIER-EXPIRY-CHECKSUM
        parts = license_key.split("-")
        if len(parts) != 4 or parts[0] != "SAATHY":
            raise ValueError("Invalid license format")
        
        tier = parts[1]
        expiry = parts[2]
        checksum = parts[3]
        
        # Verify checksum
        data = f"{parts[0]}-{parts[1]}-{parts[2]}"
        expected_checksum = hashlib.sha256(data.encode()).hexdigest()[:8]
        
        if checksum != expected_checksum:
            raise ValueError("Invalid license checksum")
        
        # Check expiry
        try:
            expiry_date = datetime.fromisoformat(expiry)
            if expiry_date < datetime.utcnow():
                raise ValueError("License expired")
        except ValueError:
            raise ValueError("Invalid license expiry date")
        
        return {
            "tier": tier.lower(),
            "expiry": expiry_date,
            "features": self._get_tier_features(tier.lower()),
            "limits": self._get_tier_limits(tier.lower()),
        }
    
    def _get_tier_features(self, tier: str) -> Dict[str, bool]:
        """Get enabled features for a tier."""
        features = {
            "basic": {
                "connectors": True,
                "embeddings": True,
                "search": True,
                "webhooks": True,
            },
            "professional": {
                "connectors": True,
                "embeddings": True,
                "search": True,
                "webhooks": True,
                "ai_recommendations": True,
                "event_correlation": True,
                "advanced_analytics": True,
                "api_priority": True,
            },
            "enterprise": {
                "connectors": True,
                "embeddings": True,
                "search": True,
                "webhooks": True,
                "ai_recommendations": True,
                "event_correlation": True,
                "advanced_analytics": True,
                "api_priority": True,
                "custom_models": True,
                "white_label": True,
                "sla_support": True,
                "audit_logs": True,
                "data_export": True,
                "multi_tenant": True,
            },
        }
        
        return features.get(tier, features["basic"])
    
    def _get_tier_limits(self, tier: str) -> Dict[str, int]:
        """Get usage limits for a tier."""
        limits = {
            "basic": {
                "connectors": 3,
                "users": 5,
                "events_per_day": 10000,
                "storage_gb": 10,
                "api_calls_per_minute": 60,
            },
            "professional": {
                "connectors": 10,
                "users": 50,
                "events_per_day": 100000,
                "storage_gb": 100,
                "api_calls_per_minute": 300,
            },
            "enterprise": {
                "connectors": -1,  # Unlimited
                "users": -1,
                "events_per_day": -1,
                "storage_gb": -1,
                "api_calls_per_minute": -1,
            },
        }
        
        return limits.get(tier, limits["basic"])
    
    def check_feature(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        if not self._license_info:
            # No license, only basic features
            return feature in ["connectors", "embeddings", "search", "webhooks"]
        
        # Check feature flags override
        if feature in self.feature_flags:
            return self.feature_flags[feature]
        
        # Check license features
        return self._license_info["features"].get(feature, False)
    
    def check_limit(self, resource: str, current_usage: int) -> bool:
        """Check if usage is within limits."""
        if not self._license_info:
            # No license, use basic limits
            limits = self._get_tier_limits("basic")
        else:
            limits = self._license_info["limits"]
        
        limit = limits.get(resource, 0)
        if limit == -1:  # Unlimited
            return True
        
        return current_usage < limit
    
    async def __call__(self, request: Request, call_next):
        """Middleware to check license for protected endpoints."""
        # Skip license check for public endpoints
        public_paths = ["/health", "/ready", "/live", "/docs", "/openapi.json"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)
        
        # Check if endpoint requires enterprise features
        enterprise_paths = [
            "/api/v1/intelligence/",
            "/api/v1/analytics/",
            "/api/v1/admin/",
        ]
        
        requires_enterprise = any(
            request.url.path.startswith(path) for path in enterprise_paths
        )
        
        if requires_enterprise:
            # Extract feature from path
            feature = None
            if "/intelligence/" in request.url.path:
                feature = "ai_recommendations"
            elif "/analytics/" in request.url.path:
                feature = "advanced_analytics"
            elif "/admin/" in request.url.path:
                feature = "audit_logs"
            
            if feature and not self.check_feature(feature):
                return JSONResponse(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    content={
                        "error": "Feature not available",
                        "message": f"The '{feature}' feature requires an enterprise license",
                        "required_tier": "professional" if feature in ["ai_recommendations", "event_correlation"] else "enterprise",
                    }
                )
        
        # Add license info to request state
        if self._license_info:
            request.state.license_info = self._license_info
        
        return await call_next(request)


def create_license_key(tier: str, expiry: datetime) -> str:
    """Create a license key for testing."""
    expiry_str = expiry.isoformat()
    data = f"SAATHY-{tier.upper()}-{expiry_str}"
    checksum = hashlib.sha256(data.encode()).hexdigest()[:8]
    return f"{data}-{checksum}"