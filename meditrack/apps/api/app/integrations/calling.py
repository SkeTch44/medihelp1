"""Calling provider seam. No outbound calls are made until a provider is deliberately implemented."""
from app.core.config import settings

class CallingProvider:
    async def call(self, to_e164: str, message: str) -> dict:
        if settings.call_provider == "stub" or not settings.call_provider_api_key:
            return {"mode":"stub", "accepted":False, "reason":"Calling provider not configured"}
        # Implement provider-specific authenticated API here, after reviewing account/recipient eligibility.
        raise NotImplementedError("Calling provider adapter is not implemented. Do not enable escalation until implemented and tested.")
