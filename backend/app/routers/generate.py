import logging

from fastapi import APIRouter, HTTPException

from ..schemas import GenerateRequest, GenerateResponse
from ..services import deepseek

router = APIRouter(prefix="/api/generate", tags=["generate"])
logger = logging.getLogger(__name__)


@router.post("", response_model=GenerateResponse)
async def generate_prompt(req: GenerateRequest) -> GenerateResponse:
    try:
        text = await deepseek.generate(req.system_prompt, req.user_input)
    except RuntimeError as e:
        logger.error("Generate failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    return GenerateResponse(text=text)