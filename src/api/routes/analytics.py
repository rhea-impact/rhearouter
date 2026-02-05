"""Analytics endpoints for request statistics"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.core.persistence import get_request_logger
from src.observability.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])


@router.get("/stats")
async def get_stats(days: int = 7):
    """
    Get usage statistics for the last N days.

    Args:
        days: Number of days to analyze (default: 7)

    Returns:
        Statistics including request counts, model usage, token usage
    """
    if days < 1 or days > 365:
        raise HTTPException(400, "Days must be between 1 and 365")

    request_logger = get_request_logger()
    stats = request_logger.get_stats(days)

    logger.debug(f"Analytics stats requested for {days} days")

    return JSONResponse(content=stats)


@router.get("/errors")
async def get_errors(days: int = 7):
    """
    Get error summary for the last N days.

    Args:
        days: Number of days to analyze (default: 7)

    Returns:
        List of error summaries with counts
    """
    if days < 1 or days > 365:
        raise HTTPException(400, "Days must be between 1 and 365")

    request_logger = get_request_logger()
    errors = request_logger.get_error_summary(days)

    logger.debug(f"Error summary requested for {days} days")

    return JSONResponse(content={"errors": errors})


@router.get("/models/{model}")
async def get_model_performance(model: str, days: int = 7):
    """
    Get performance metrics for a specific model.

    Args:
        model: Model name
        days: Number of days to analyze (default: 7)

    Returns:
        Performance metrics for the model
    """
    if days < 1 or days > 365:
        raise HTTPException(400, "Days must be between 1 and 365")

    request_logger = get_request_logger()
    performance = request_logger.get_model_performance(model, days)

    if performance["total_requests"] == 0:
        raise HTTPException(404, f"No data found for model: {model}")

    logger.debug(f"Model performance requested for {model} ({days} days)")

    return JSONResponse(content=performance)


@router.get("/recent")
async def get_recent_requests(limit: int = 100):
    """
    Get recent requests.

    Args:
        limit: Max number of requests to return (default: 100)

    Returns:
        List of recent requests, newest first
    """
    if limit < 1 or limit > 1000:
        raise HTTPException(400, "Limit must be between 1 and 1000")

    request_logger = get_request_logger()
    requests = request_logger.get_recent_requests(limit)

    logger.debug(f"Recent requests requested (limit: {limit})")

    return JSONResponse(content={"requests": requests})


@router.post("/cleanup")
async def cleanup_old_data(days: int = 30):
    """
    Delete requests older than N days.

    Args:
        days: Number of days to keep (default: 30)

    Returns:
        Number of deleted requests
    """
    if days < 1:
        raise HTTPException(400, "Days must be positive")

    request_logger = get_request_logger()
    deleted = request_logger.cleanup_old_requests(days)

    logger.info(f"Cleanup completed: {deleted} requests deleted (>{days} days)")

    return JSONResponse(content={
        "deleted_count": deleted,
        "retention_days": days
    })
