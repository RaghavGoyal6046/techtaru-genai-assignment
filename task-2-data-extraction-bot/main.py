import time
import logging
from typing import Dict, Any
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from web_ui import DASHBOARD_HTML
from extractor_config import ExtractorConfig
from schemas import (
    ExtractionRequest,
    ExtractionResponse,
    ErrorResponse
)
from extractor import DocumentExtractor, ExtractionExecutionError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ExtractionAPI")

app = FastAPI(
    title="Data Extraction Bot API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)")
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "Validation error")
        error_details.append({"field": field, "message": msg})

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            success=False,
            error_code="VALIDATION_ERROR",
            message="Request body failed schema validation.",
            details=error_details
        ).model_dump()
    )


@app.exception_handler(ExtractionExecutionError)
async def extraction_error_handler(request: Request, exc: ExtractionExecutionError):
    logger.error(f"Extraction error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ErrorResponse(
            success=False,
            error_code="EXTRACTION_FAILED",
            message=str(exc)
        ).model_dump()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred."
        ).model_dump()
    )


@app.get("/", tags=["General"])
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if accept.startswith("text/html"):
        return HTMLResponse(content=DASHBOARD_HTML)
    return {
        "service": "TechTaru Data Extraction Bot",
        "status": "online",
        "documentation": "/docs",
        "supported_documents": ["resume", "invoice"],
        "active_provider": ExtractorConfig.get_active_provider()
    }


@app.get("/app", response_class=HTMLResponse, tags=["General"])
@app.get("/dashboard", response_class=HTMLResponse, tags=["General"])
async def interactive_dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get("/health", tags=["Health"])
async def health_check():
    provider = ExtractorConfig.get_active_provider()
    return {
        "status": "healthy",
        "active_provider": provider,
        "gemini_configured": bool(ExtractorConfig.GEMINI_API_KEY)
    }


@app.post(
    "/extract",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Extraction"],
    responses={
        200: {"description": "Successful extraction"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        502: {"model": ErrorResponse, "description": "Extraction failure"}
    }
)
async def extract_document(request: ExtractionRequest):
    extractor = DocumentExtractor()
    validated_data, warnings, provider_used = extractor.extract(
        text=request.text,
        doc_type=request.document_type
    )

    return ExtractionResponse(
        success=True,
        document_type=request.document_type.value,
        provider_used=provider_used,
        data=validated_data,
        warnings=warnings
    )
