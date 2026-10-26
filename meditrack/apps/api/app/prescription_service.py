"""Prescription file validation and OCR. OCR output is untrusted and must be reviewed."""
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageOps
import pytesseract
from pypdf import PdfReader
import json
import httpx

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


def extract_text(content: bytes, mime_type: str) -> str:
    if mime_type == "application/pdf":
        reader = PdfReader(BytesIO(content))
        if len(reader.pages) > 10:
            raise ValueError("PDF must contain 10 pages or fewer")
        chunks = [(page.extract_text() or "") for page in reader.pages]
        # OCR image-only PDF pages are not automatically processed; tell the user to upload clear images.
        text = "\n".join(chunks).strip()
        return text[:30000]
    with Image.open(BytesIO(content)) as image:
        if image.width * image.height > 25_000_000:
            raise ValueError("Image resolution is too large")
        image = ImageOps.exif_transpose(image).convert("RGB")
        return pytesseract.image_to_string(image, config="--psm 6")[:30000]


def safe_store(upload_dir: str, file_id: str, suffix: str, content: bytes) -> str:
    root = Path(upload_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = (root / f"{file_id}{suffix}").resolve()
    if root not in target.parents:
        raise ValueError("Invalid upload path")
    target.write_bytes(content)
    return str(target)


async def extract_medicine_candidates_with_gemini(text: str, api_key: str, model: str) -> list[dict]:
    """Draft structured transcription from OCR text. It must never be used as a verified prescription."""
    if not text.strip():
        return []
    prompt = (
        "Transcribe possible medicine entries from the supplied OCR text. This is a transcription task, not medical advice. "
        "Do not infer a dose, route, duration, frequency, food instruction, or missing characters. If uncertain, use null or an empty list. "
        "Only include information explicitly present in the source. Return ONLY JSON with key medicines, an array of objects with fields: "
        "medicine_name (string or null), strength (string or null), instructions_as_written (string or null), "
        "schedule_times (array of HH:MM only when explicit times appear, otherwise []), repeat_days (array of weekday integers only if explicitly clear, otherwise [0,1,2,3,4,5,6]), "
        "source_excerpt (exact short excerpt), needs_human_review (always true). Do not add medical explanations.\n\nOCR TEXT:\n" + text[:18000]
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.post(url, params={"key": api_key}, json={"contents":[{"parts":[{"text":prompt}]}], "generationConfig":{"temperature":0, "responseMimeType":"application/json"}})
        response.raise_for_status()
        payload = response.json()
    result_text = payload["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(result_text)
    items = parsed.get("medicines", [])
    if not isinstance(items, list):
        return []
    clean = []
    for item in items[:50]:
        if not isinstance(item, dict):
            continue
        name = item.get("medicine_name")
        if not isinstance(name, str) or not name.strip():
            continue
        times = item.get("schedule_times", [])
        if not isinstance(times, list): times = []
        times = [t for t in times if isinstance(t, str) and __import__('re').fullmatch(r'([01]\d|2[0-3]):[0-5]\d', t)]
        clean.append({
            "medicine_name": name[:160],
            "strength": item.get("strength")[:120] if isinstance(item.get("strength"), str) else None,
            "instructions_as_written": item.get("instructions_as_written")[:1000] if isinstance(item.get("instructions_as_written"), str) else None,
            "schedule_times": times,
            "repeat_days": [0,1,2,3,4,5,6],
            "source_excerpt": item.get("source_excerpt")[:500] if isinstance(item.get("source_excerpt"), str) else "",
            "needs_human_review": True
        })
    return clean
