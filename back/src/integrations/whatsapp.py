"""
WhatsApp integration helpers with secure token handling and webhook verification
"""

import os
from typing import Optional, Dict, Any, List
import httpx
from ..utils.encryption import encrypt_key, decrypt_key
from ..utils.webhook_verification import verify_webhook_signature, WebhookProvider
from ..utils.retry import retry_with_backoff, RetryConfig


class WhatsAppIntegration:
    """WhatsApp integration service with secure token management"""
    
    def __init__(self, access_token: Optional[str] = None, phone_number_id: Optional[str] = None):
        """
        Initialize WhatsApp integration
        
        Args:
            access_token: WhatsApp access token (optional, uses env if not provided)
            phone_number_id: WhatsApp phone number ID (optional, uses env if not provided)
        """
        self.access_token = access_token or os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = phone_number_id or os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.base_url = "https://graph.facebook.com/v19.0"
        
        # Default retry configuration for WhatsApp API calls
        self.retry_config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,  # Longer base delay for WhatsApp rate limits
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True
        )
    
    def encrypt_access_token(self, access_token: str) -> str:
        """
        Encrypt WhatsApp access token for secure storage
        
        Args:
            access_token: Plaintext WhatsApp access token
            
        Returns:
            Encrypted access token
        """
        result = encrypt_key(access_token)
        return result.encrypted_data
    
    def decrypt_access_token(self, encrypted_token: str) -> str:
        """
        Decrypt WhatsApp access token for API calls
        
        Args:
            encrypted_token: Encrypted WhatsApp access token
            
        Returns:
            Decrypted plaintext access token
        """
        return decrypt_key(encrypted_token)
    
    @retry_with_backoff()
    async def make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to WhatsApp API with retry logic
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            
        Returns:
            API response data
        """
        if not self.access_token:
            raise ValueError("WhatsApp access token not configured")
        if not self.phone_number_id:
            raise ValueError("WhatsApp phone number ID not configured")
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            return response.json()
    
    async def send_message(
        self, 
        to: str, 
        message: str, 
        message_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Send WhatsApp message
        
        Args:
            to: Recipient phone number in E.164 format
            message: Message content
            message_type: Message type (text, template, etc.)
            
        Returns:
            Message sending response
        """
        endpoint = f"/{self.phone_number_id}/messages"
        
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": message_type
        }
        
        if message_type == "text":
            data["text"] = {"body": message}
        elif message_type == "template":
            # For template messages, structure differs
            data["template"] = {
                "name": message,
                "language": {"code": "en"}
            }
        
        return await self.make_request("POST", endpoint, data=data)
    
    async def send_template_message(
        self, 
        to: str, 
        template_name: str, 
        parameters: Optional[List[Dict[str, str]]] = None,
        language_code: str = "en"
    ) -> Dict[str, Any]:
        """
        Send WhatsApp template message
        
        Args:
            to: Recipient phone number in E.164 format
            template_name: Template name
            parameters: Template parameters
            language_code: Language code
            
        Returns:
            Template message sending response
        """
        endpoint = f"/{self.phone_number_id}/messages"
        
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code}
            }
        }
        
        if parameters:
            data["template"]["components"] = [
                {
                    "type": "body",
                    "parameters": parameters
                }
            ]
        
        return await self.make_request("POST", endpoint, data=data)
    
    async def get_business_profile(self) -> Dict[str, Any]:
        """
        Get WhatsApp business profile
        
        Returns:
            Business profile information
        """
        endpoint = f"/{self.phone_number_id}/whatsapp_business_profile"
        return await self.make_request("GET", endpoint)
    
    async def upload_media(self, file_path: str, media_type: str) -> Dict[str, Any]:
        """
        Upload media to WhatsApp
        
        Args:
            file_path: Path to media file
            media_type: Media type (image, audio, video, document)
            
        Returns:
            Media upload response
        """
        endpoint = f"/{self.phone_number_id}/media"
        
        # For actual file upload, we'd use multipart form data
        # This is a simplified version
        data = {
            "type": media_type,
            "messaging_product": "whatsapp"
        }
        
        return await self.make_request("POST", endpoint, data=data)
    
    def verify_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Verify WhatsApp webhook signature
        
        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value
            
        Returns:
            Webhook verification result
        """
        result = verify_webhook_signature(WebhookProvider.WHATSAPP, payload, signature)
        return {
            "is_valid": result.is_valid,
            "payload": result.payload if result.is_valid else {},
            "error": result.error
        }


def get_whatsapp_integration() -> WhatsAppIntegration:
    """
    Get or create global WhatsApp integration instance
    
    Returns:
        WhatsAppIntegration instance
    """
    return WhatsAppIntegration()