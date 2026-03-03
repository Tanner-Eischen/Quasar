"""Health check endpoint."""

from fastapi import APIRouter

from legacylens.core.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns basic status information about the API.
    """
    # TODO: Actually check database connection
    # TODO: Actually check embedding service availability

    return HealthResponse(
        status="ok",
        version="0.1.0",
        database="connected",  # Placeholder
        embedding_service="available",  # Placeholder
    )
