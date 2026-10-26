"""WhatsApp Cloud API adapter. Stub mode intentionally avoids sending real messages."""
import httpx
from app.core.config import settings

class WhatsAppProvider:
    async def send_text(self, to_e164: str, body: str) -> dict:
        if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
            return {"mode": "stub", "accepted": False, "reason": "WhatsApp credentials not configured"}
        url = f"https://graph.facebook.com/{settings.whatsapp_api_version}/{settings.whatsapp_phone_number_id}/messages"
        payload = {"messaging_product":"whatsapp", "recipient_type":"individual", "to":to_e164,
                   "type":"text", "text":{"preview_url":False,"body":body}}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload, headers={"Authorization":f"Bearer {settings.whatsapp_access_token}"})
            response.raise_for_status()
            return response.json()

    async def send_template(self, to_e164: str, template_name: str, language: str = "en_US", components: list | None = None) -> dict:
        if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
            return {"mode":"stub", "accepted":False, "reason":"WhatsApp credentials not configured"}
        url = f"https://graph.facebook.com/{settings.whatsapp_api_version}/{settings.whatsapp_phone_number_id}/messages"
        payload = {"messaging_product":"whatsapp", "to":to_e164, "type":"template", "template":{"name":template_name,"language":{"code":language},"components":components or []}}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload, headers={"Authorization":f"Bearer {settings.whatsapp_access_token}"})
            response.raise_for_status()
            return response.json()
