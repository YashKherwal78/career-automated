import json
import mimetypes
from typing import Optional

from src.system.logger import setup_logger
from src.utils.llm_router import LLMRouter
from src.ingestion.job_lead import JobLead

logger = setup_logger("screenshot_extractor")

_PROMPT = """You are looking at a screenshot of a social/job-board post \
advertising a job opening. Extract the following as strict JSON, no \
markdown fences, no commentary:

{
  "company": "<company name, or empty string if not visible>",
  "role": "<job title/role, or empty string if not visible>",
  "apply_link": "<the URL to apply, or empty string if none is visible>",
  "location": "<location if mentioned, else null>",
  "jd_excerpt": "<any job description text visible in the image (caption, bullet points), else null>",
  "confidence": <float 0.0-1.0, your confidence that company/role/apply_link are all correct>
}"""


def extract_from_image(image_path: str, llm_router: Optional[LLMRouter] = None) -> Optional[JobLead]:
    router = llm_router or LLMRouter()
    mime_type, _ = mimetypes.guess_type(image_path)
    mime_type = mime_type or "image/png"

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    try:
        response = router.chat_completion_vision(
            image_bytes=image_bytes,
            mime_type=mime_type,
            prompt=_PROMPT,
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.info(f"[screenshot_extractor] extraction failed for {image_path}: {e}")
        return None

    if payload.get("confidence", 0) < 0.5:
        logger.info(f"[screenshot_extractor] low confidence ({payload.get('confidence')}) for {image_path}, skipping")
        return None

    lead = JobLead(
        company=payload.get("company") or "",
        role=payload.get("role") or "",
        apply_link=payload.get("apply_link") or "",
        location=payload.get("location") or None,
        jd_excerpt=payload.get("jd_excerpt") or None,
        source="screenshot",
        source_ref=image_path,
    )

    if not lead.is_valid():
        logger.info(f"[screenshot_extractor] incomplete extraction for {image_path}: {payload}")
        return None

    return lead
