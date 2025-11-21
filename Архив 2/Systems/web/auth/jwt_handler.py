"""
JWT Token Handler for SwiftDevBot Web Dashboard
Handles creation and validation of JWT tokens for web authentication.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import jwt
    from jwt import PyJWTError
except ImportError:
    jwt = None
    PyJWTError = Exception


class JWTHandler:
    """JWT token handler for web authentication."""
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize JWT handler.
        
        Args:
            secret_key: Secret key for JWT signing. If None, will be generated/loaded.
        """
        self.secret_key = secret_key or self._get_or_create_secret_key()
        self.algorithm = "HS256"
    
    def _get_or_create_secret_key(self) -> str:
        """
        Get or create JWT secret key.
        
        Returns:
            Secret key string
        """
        # Try to get from environment
        env_key = os.environ.get("SDB_JWT_SECRET_KEY")
        if env_key:
            return env_key
        
        # Try to load from config file
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "security_keys.json"
        if config_path.exists():
            try:
                import json
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if 'jwt_secret' in config:
                        return config['jwt_secret']
            except Exception:
                pass
        
        # Generate new key (for development only - should be set in production)
        new_key = secrets.token_urlsafe(32)
        
        # Try to save to config file
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            import json
            config = {'jwt_secret': new_key}
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass
        
        return new_key
    
    async def create_access_token(
        self,
        user_id: int,
        username: str,
        role: str = "User",
        expires_in: timedelta = timedelta(minutes=5)
    ) -> str:
        """
        Create JWT access token.
        
        Args:
            user_id: Telegram user ID
            username: Username
            role: User role (Admin, Moderator, User)
            expires_in: Token expiration time
            
        Returns:
            JWT token string
        """
        if jwt is None:
            raise ImportError("PyJWT is required. Install it with: pip install PyJWT")
        
        now = datetime.utcnow()
        expire = now + expires_in
        
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "username": username,
            "role": role.lower(),  # Normalize role to lowercase
            "iat": now,
            "exp": expire,
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token and return payload.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload if valid, None otherwise
        """
        if jwt is None:
            raise ImportError("PyJWT is required. Install it with: pip install PyJWT")
        
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except PyJWTError:
            return None
    
    def get_user_info(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user info from token payload.
        
        Args:
            payload: JWT token payload
            
        Returns:
            User info dictionary
        """
        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "role": payload.get("role", "user"),
        }


# Singleton instance
_jwt_handler: Optional[JWTHandler] = None


def get_jwt_handler() -> JWTHandler:
    """
    Get or create JWT handler instance.
    
    Returns:
        JWTHandler instance
    """
    global _jwt_handler
    if _jwt_handler is None:
        _jwt_handler = JWTHandler()
    return _jwt_handler
