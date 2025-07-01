#!/usr/bin/env python3
"""
Token Manager for MCP Client Authentication
Handles Azure AD client credentials flow for MCP server authentication.
"""

import os
import time
import httpx
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class TokenManager:
    def __init__(self):
        self.tenant_id = os.getenv("MCP_TENANT_ID")
        self.client_id = os.getenv("MCP_CLIENT_ID")
        self.client_secret = os.getenv("MCP_CLIENT_SECRET")
        self._token_cache: Dict[str, Dict] = {}
        
        if self.tenant_id and self.client_id and self.client_secret:
            logger.info("🔐 Token manager initialized with Azure AD credentials")
        else:
            logger.info("🔓 Token manager initialized without credentials (auth disabled)")
    
    async def get_token(self, scope: str) -> Optional[str]:
        """Get bearer token for scope with caching"""
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            logger.debug("Missing Azure AD credentials, skipping token acquisition")
            return None
            
        # Check cache
        if scope in self._token_cache:
            token_data = self._token_cache[scope]
            if time.time() < token_data['expires_at']:
                logger.debug(f"Using cached token for scope: {scope}")
                return token_data['access_token']
        
        # Get new token
        logger.info(f"Acquiring new token for scope: {scope}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "scope": scope,
                        "grant_type": "client_credentials"
                    }
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    self._token_cache[scope] = {
                        "access_token": token_data["access_token"],
                        "expires_at": time.time() + token_data["expires_in"] - 60  # 1min buffer
                    }
                    logger.info(f"✅ Token acquired successfully for scope: {scope}")
                    return token_data["access_token"]
                else:
                    logger.error(f"❌ Token acquisition failed: {response.status_code} - {response.text}")
                    return None
        
        except Exception as e:
            logger.error(f"❌ Token acquisition error: {e}")
            return None
