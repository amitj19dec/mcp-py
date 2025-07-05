"""
Azure AD Token Verifier for MCP Server
Refactored to use the official MCP SDK authentication framework
"""

import os
import jwt
import logging
from typing import Dict, List, Optional
import requests
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from mcp.server.auth.provider import TokenVerifier, TokenInfo

logger = logging.getLogger(__name__)


class AzureTokenVerifier(TokenVerifier):
    """
    Azure AD token verifier that validates JWT tokens and extracts app roles.
    Uses the official MCP SDK TokenVerifier protocol for seamless integration.
    """
    
    def __init__(self, tenant_id: str = None, client_id: str = None, enable_auth: bool = True):
        """
        Initialize Azure AD token verifier.
        
        Args:
            tenant_id: Azure AD tenant ID. If None, reads from AZURE_TENANT_ID env var
            client_id: Azure AD application client ID. If None, reads from AZURE_CLIENT_ID env var
            enable_auth: Whether to enable authentication. If False, returns mock admin role
        """
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        self.enable_auth = enable_auth and os.getenv("ENABLE_AUTH", "true").lower() == "true"
        self._jwks_cache = {}
        
        # Validate required configuration
        if self.enable_auth and (not self.tenant_id or not self.client_id):
            raise ValueError(
                "Azure AD configuration missing. Set AZURE_TENANT_ID and AZURE_CLIENT_ID "
                "environment variables or pass them to constructor."
            )
        
        if not self.enable_auth:
            logger.warning("Authentication is disabled - using mock admin role for all requests")
    
    async def verify_token(self, token: str) -> TokenInfo:
        """
        Verify JWT token and extract user information.
        
        Args:
            token: JWT access token from Authorization header
            
        Returns:
            TokenInfo containing subject, scopes (app roles), and claims
            
        Raises:
            jwt.InvalidTokenError: If token validation fails
            ValueError: If token format is invalid or required claims are missing
        """
        if not self.enable_auth:
            # Return mock admin role for development/testing
            return TokenInfo(
                subject="mock_user",
                scopes=["MCP.Admin"],
                claims={"roles": ["MCP.Admin"], "preferred_username": "mock_user"}
            )
        
        try:
            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get('kid')
            
            if not kid:
                raise ValueError("Token header missing 'kid' (key ID)")
            
            # Get signing key from Azure AD JWKS endpoint
            signing_key = await self._get_signing_key(kid)
            
            # Decode and verify the token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0",
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iat": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iss": True,
                }
            )
            
            # Extract user information
            subject = payload.get('sub') or payload.get('oid') or payload.get('preferred_username')
            if not subject:
                raise ValueError("Token missing required subject identifier (sub, oid, or preferred_username)")
            
            # Extract app roles (these become scopes in MCP context)
            app_roles = payload.get('roles', [])
            if not isinstance(app_roles, list):
                app_roles = []
            
            # Additional claims for context
            claims = {
                "roles": app_roles,
                "preferred_username": payload.get('preferred_username'),
                "name": payload.get('name'),
                "email": payload.get('email'),
                "tenant_id": payload.get('tid'),
                "app_id": payload.get('appid'),
                "auth_time": payload.get('auth_time'),
                "iat": payload.get('iat'),
                "exp": payload.get('exp'),
            }
            
            # Remove None values from claims
            claims = {k: v for k, v in claims.items() if v is not None}
            
            logger.info(f"Successfully validated token for user: {subject}, roles: {app_roles}")
            
            return TokenInfo(
                subject=subject,
                scopes=app_roles,  # App roles become scopes in MCP
                claims=claims
            )
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise jwt.InvalidTokenError("Token has expired")
        except jwt.InvalidAudienceError:
            logger.warning(f"Token audience mismatch. Expected: {self.client_id}")
            raise jwt.InvalidTokenError("Token audience mismatch")
        except jwt.InvalidIssuerError:
            logger.warning(f"Token issuer mismatch. Expected issuer: https://login.microsoftonline.com/{self.tenant_id}/v2.0")
            raise jwt.InvalidTokenError("Token issuer mismatch")
        except jwt.InvalidSignatureError:
            logger.warning("Token signature verification failed")
            raise jwt.InvalidTokenError("Token signature verification failed")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}")
            raise jwt.InvalidTokenError(f"Token validation error: {str(e)}")
    
    async def _get_signing_key(self, kid: str) -> bytes:
        """
        Get JWT signing key from Azure AD JWKS endpoint with caching.
        
        Args:
            kid: Key ID from JWT header
            
        Returns:
            PEM-encoded public key bytes
            
        Raises:
            ValueError: If key not found or JWKS request fails
        """
        # Check cache first
        if kid in self._jwks_cache:
            return self._jwks_cache[kid]
        
        try:
            # Fetch JWKS from Azure AD
            jwks_url = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
            
            response = requests.get(jwks_url, timeout=10)
            response.raise_for_status()
            
            jwks = response.json()
            
            # Find the key with matching kid
            for key in jwks.get('keys', []):
                if key.get('kid') == kid and key.get('kty') == 'RSA':
                    # Convert JWK to PEM format
                    public_key_pem = self._jwk_to_pem(key)
                    
                    # Cache the key for future use
                    self._jwks_cache[kid] = public_key_pem
                    
                    logger.debug(f"Cached new signing key with kid: {kid}")
                    return public_key_pem
            
            raise ValueError(f"Signing key with kid '{kid}' not found in Azure AD JWKS")
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch JWKS from Azure AD: {e}")
            raise ValueError(f"JWKS request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing JWKS response: {e}")
            raise ValueError(f"JWKS processing error: {str(e)}")
    
    def _jwk_to_pem(self, jwk: Dict) -> bytes:
        """
        Convert JWK (JSON Web Key) to PEM format.
        
        Args:
            jwk: JWK dictionary containing RSA key components
            
        Returns:
            PEM-encoded public key bytes
            
        Raises:
            ValueError: If JWK format is invalid or conversion fails
        """
        try:
            # Validate required JWK fields
            if jwk.get('kty') != 'RSA':
                raise ValueError(f"Unsupported key type: {jwk.get('kty')}")
            
            if 'n' not in jwk or 'e' not in jwk:
                raise ValueError("JWK missing required RSA components (n, e)")
            
            # Extract and decode modulus (n) and exponent (e)
            # Add padding to handle base64url encoding
            n_b64 = jwk['n']
            e_b64 = jwk['e']
            
            # Add padding if needed for base64 decoding
            n_b64 += '=' * (4 - len(n_b64) % 4) % 4
            e_b64 += '=' * (4 - len(e_b64) % 4) % 4
            
            n_bytes = base64.urlsafe_b64decode(n_b64)
            e_bytes = base64.urlsafe_b64decode(e_b64)
            
            # Convert to integers
            n_int = int.from_bytes(n_bytes, 'big')
            e_int = int.from_bytes(e_bytes, 'big')
            
            # Create RSA public key
            public_numbers = rsa.RSAPublicNumbers(e_int, n_int)
            public_key = public_numbers.public_key()
            
            # Convert to PEM format
            pem_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return pem_bytes
            
        except Exception as e:
            logger.error(f"Failed to convert JWK to PEM: {e}")
            raise ValueError(f"JWK conversion error: {str(e)}")
    
    def clear_cache(self):
        """Clear the JWKS cache. Useful for testing or key rotation scenarios."""
        self._jwks_cache.clear()
        logger.info("JWKS cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring purposes."""
        return {
            "cached_keys": len(self._jwks_cache),
            "key_ids": list(self._jwks_cache.keys())
        }
