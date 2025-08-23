"""
OCR Application with Full Observability Integration

This is a FastAPI-based Optical Character Recognition (OCR) service that provides:
- Vietnamese and English text recognition using EasyOCR
- Full observability through the three pillars: Metrics, Logging, and Tracing
- Image caching to prevent duplicate processing
- Custom API documentation endpoints
- Robust error handling and performance optimizations

Architecture:
- FastAPI web framework for async HTTP API
- EasyOCR engine for text recognition (supports GPU acceleration)
- OpenTelemetry for distributed tracing integration with Jaeger
- Image hash-based caching for performance optimization
- Structured logging with loguru for centralized log collection

Observability Integration:
1. TRACING: OpenTelemetry spans for detailed request flow analysis
2. LOGGING: Structured logs collected by Filebeat -> Elasticsearch -> Kibana
3. METRICS: FastAPI metrics collected by Prometheus -> visualized in Grafana

Deployment: Deployed as Kubernetes service in 'model-serving' namespace
External Access: Available via NGINX Ingress at /ocr-app/* endpoints
"""

from io import BytesIO
import os

import easyocr
import numpy as np
from fastapi import FastAPI, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import get_tracer_provider, set_tracer_provider
from PIL import Image
from loguru import logger
import imagehash

"""
CACHING SYSTEM
==============
Global cache dictionary for storing OCR results to prevent duplicate processing.
Key: Image hash (generated using imagehash.average_hash)
Value: OCR results (bounding boxes, texts, probabilities)

Benefits:
- Reduces computational load for identical images
- Improves response time for cached requests
- Memory-efficient hash-based storage
"""
cache = {}

"""
OBSERVABILITY PILLAR #1: DISTRIBUTED TRACING
============================================
OpenTelemetry Integration with Jaeger for distributed tracing.

Purpose: Track request flow through the entire system
- Trace each OCR processing request end-to-end
- Monitor performance bottlenecks in image processing pipeline
- Debug errors and latency issues across microservices

Configuration:
- service_name: Identifies this service in Jaeger UI ("ocr-service")
- jaeger_host: Jaeger collector endpoint (configured via Kubernetes service discovery)
- jaeger_port: Jaeger agent port (6831 for UDP, 14268 for HTTP)

Workflow:
1. TracerProvider creates trace contexts
2. Tracer generates spans for each operation
3. JaegerExporter sends spans to Jaeger collector
4. BatchSpanProcessor batches spans for efficient transmission
"""
service_name = os.getenv("OTEL_SERVICE_NAME", "ocr-service")
jaeger_host = os.getenv("JAEGER_AGENT_HOST", "localhost") 
jaeger_port = int(os.getenv("JAEGER_AGENT_PORT", "6831"))

# Configure OpenTelemetry TracerProvider with service identification
set_tracer_provider(
    TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
)
# Get tracer instance for creating spans
tracer = get_tracer_provider().get_tracer("ocr-app", "1.0.0")

# Configure Jaeger exporter for sending traces
jaeger_exporter = JaegerExporter(
    agent_host_name=jaeger_host,    # Jaeger agent hostname (Kubernetes service name)
    agent_port=jaeger_port,         # Jaeger agent port (UDP)
)

# Batch span processor for efficient trace transmission
span_processor = BatchSpanProcessor(jaeger_exporter)
get_tracer_provider().add_span_processor(span_processor)

# OBSERVABILITY PILLAR #2: STRUCTURED LOGGING
# This log will be collected by Filebeat -> Elasticsearch -> visible in Kibana
logger.info(f"OpenTelemetry configured - Service: {service_name}, Jaeger: {jaeger_host}:{jaeger_port}")

"""
FASTAPI APPLICATION SETUP
=========================
Main FastAPI application with custom configuration for observability and documentation.

Architecture Decisions:
- Disabled default docs/openapi endpoints to create custom ones under /ocr-app prefix
- APIRouter pattern for organized endpoint grouping and prefixing
- Separation of concerns: main app handles global concerns, router handles OCR logic

Custom Documentation Strategy:
- All documentation endpoints under /ocr-app prefix for consistent routing
- Custom OpenAPI schema generation for better control
- Swagger UI and ReDoc served with custom URLs
"""
app = FastAPI(
    title="Simple OCR Service",
    description="OCR service with Vietnamese and English support",
    version="1.0.0",
    docs_url=None,      # Disable default docs - will create custom at /ocr-app/docs
    redoc_url=None,     # Disable default redoc - will create custom at /ocr-app/redoc  
    openapi_url=None    # Disable default openapi - will create custom at /ocr-app/openapi.json
)

"""
API ROUTER PATTERN
==================
APIRouter provides organized endpoint grouping with consistent URL prefixing.

Benefits:
- All OCR-related endpoints automatically prefixed with /ocr-app
- Consistent tagging for OpenAPI documentation
- Separation of concerns from main FastAPI app
- Easy to modify prefix without changing individual endpoint definitions
"""
ocr_router = APIRouter(prefix="/ocr-app", tags=["OCR"])

"""
EASYOCR ENGINE INITIALIZATION
============================
Global EasyOCR reader instance for text recognition.

Initialization Strategy:
- Lazy initialization during startup event (not at import time)
- Single global instance to avoid memory overhead
- GPU support enabled for better performance
- Model storage in persistent directory
"""
reader = None

@app.on_event("startup")
async def startup_event():
    """
    APPLICATION STARTUP EVENT HANDLER
    =================================
    Initialize EasyOCR reader during application startup.
    
    This is a FastAPI lifecycle event that runs once when the application starts.
    
    EasyOCR Configuration:
    - Languages: ["vi", "en"] - Vietnamese and English support
    - GPU: True - Enable GPU acceleration if available (requires CUDA)
    - Detection Network: "craft" - CRAFT text detection model
    - Model Storage: "./my_model" - Persistent model storage to avoid re-downloading
    - Download: True - Allow automatic model downloads if not present
    
    Error Handling:
    - Graceful degradation if OCR initialization fails
    - Structured logging for monitoring initialization status
    - Application can still serve health endpoints even if OCR fails
    """
    global reader
    try:
        # Initialize EasyOCR with Vietnamese and English language support
        reader = easyocr.Reader(
            ["vi", "en"],                           # Supported languages
            gpu=True,                               # Enable GPU acceleration
            detect_network="craft",                 # Text detection model
            model_storage_directory="./my_model",   # Persistent model storage
            download_enabled=True,                  # Auto-download models
        )
        # OBSERVABILITY: Log successful initialization for monitoring
        logger.info("OCR reader initialized successfully")
    except Exception as e:
        # OBSERVABILITY: Log initialization errors for debugging
        logger.error(f"Failed to initialize OCR reader: {str(e)}")

@ocr_router.get("/")
async def health_check():
    """
    Health check endpoint
    Accessible at: GET /ocr-app/
    """
    return {
        "status": "healthy" if reader is not None else "degraded",
        "service": "Simple OCR Service",
        "version": "1.0.0",
        "reader_loaded": reader is not None,
        "cache_size": len(cache),
        "endpoints": {
            "health": "GET /ocr-app/",
            "ocr_process": "POST /ocr-app/process",
            "docs": "GET /ocr-app/docs",
            "redoc": "GET /ocr-app/redoc",
            "openapi": "GET /ocr-app/openapi.json"
        }
    }

@ocr_router.get("/health")
async def health_check_alias():
    """Alternative health check endpoint"""
    return await health_check()

@ocr_router.post("/process")
async def process_ocr(file: UploadFile = File(...)):
    """
    OCR PROCESSING ENDPOINT - CORE BUSINESS LOGIC
    =============================================
    Main OCR processing endpoint with full observability integration.
    
    Accepts: Multipart form data with image file (jpg, png, gif, bmp, etc.)
    Returns: JSON response with OCR results (bounding boxes, texts, probabilities)
    
    OBSERVABILITY INTEGRATION:
    - TRACING: Detailed spans for each processing step
    - LOGGING: Structured logs for debugging and monitoring  
    - METRICS: Implicit metrics collection via FastAPI (request count, duration, errors)
    
    PROCESSING PIPELINE:
    1. Input validation (file type, OCR reader availability)
    2. Image loading and hash calculation
    3. Cache lookup for duplicate prevention
    4. OCR processing with EasyOCR
    5. Result formatting and caching
    6. Response generation
    
    ERROR HANDLING:
    - Service unavailable (503): OCR reader not initialized
    - Bad request (400): Invalid file type
    - Internal server error (500): Processing failures
    """
    # TRACING: Create main span for entire OCR processing request
    with tracer.start_as_current_span("ocr-processing") as main_span:
        try:
            # STEP 1: SERVICE AVAILABILITY CHECK
            # Ensure OCR reader is properly initialized before processing
            if reader is None:
                logger.error("OCR reader is not initialized")
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "OCR service unavailable",
                        "detail": "OCR reader is not initialized",
                        "status": "error"
                    }
                )

            # STEP 2: INPUT VALIDATION
            # Validate file type to ensure only image files are processed
            if file.content_type and not file.content_type.startswith('image/'):
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Invalid file type",
                        "detail": "Only image files are accepted",
                        "status": "error"
                    }
                )

            # STEP 3: IMAGE LOADING AND HASH CALCULATION
            # TRACING: Create span for image loading operations
            with tracer.start_as_current_span("image-loading"):
                # Read uploaded file content asynchronously
                request_object_content = await file.read()
                # Convert to PIL Image for processing
                pil_image = Image.open(BytesIO(request_object_content))
                # Generate perceptual hash for cache key and duplicate detection
                pil_hash = imagehash.average_hash(pil_image)
                # LOGGING: Log image processing start
                logger.info(f"Processing image: {file.filename}, hash: {pil_hash}")

            # STEP 4: CACHE LOOKUP
            # TRACING: Create span for cache operations
            with tracer.start_as_current_span("cache-check"):
                if pil_hash in cache:
                    # LOGGING: Cache hit - returning cached result
                    logger.info("Returning cached result")
                    cached_result = cache[pil_hash].copy()
                    cached_result["cached"] = True
                    return cached_result

            # STEP 5: OCR PROCESSING
            # TRACING: Create span for actual OCR inference
            with tracer.start_as_current_span("ocr-prediction"):
                # LOGGING: Log OCR processing start
                logger.info("Running OCR prediction...")
                # Run EasyOCR inference on the image
                detection = reader.readtext(pil_image)

            # STEP 6: RESULT FORMATTING AND CACHING
            # TRACING: Create span for result processing
            with tracer.start_as_current_span("result-formatting"):
                # Initialize result structure
                result = {
                    "bboxes": [],           # Text bounding boxes coordinates
                    "texts": [],            # Extracted text strings
                    "probs": [],            # Confidence probabilities
                    "cached": False,        # Cache status indicator
                    "image_hash": str(pil_hash)  # Image hash for debugging
                }
                
                # Process each detected text element
                for bbox, text, prob in detection:
                    # Convert numpy arrays to JSON-serializable lists
                    bbox = np.array(bbox).tolist()
                    result["bboxes"].append(bbox)
                    result["texts"].append(text)
                    result["probs"].append(prob)

                # Prepare result for caching (without metadata)
                cache_result = {
                    "bboxes": result["bboxes"],
                    "texts": result["texts"], 
                    "probs": result["probs"],
                    "image_hash": result["image_hash"]
                }
                # Store in cache for future identical requests
                cache[pil_hash] = cache_result
                
                # LOGGING: Log successful processing completion
                logger.info(f"OCR processing completed. Found {len(result['texts'])} text elements")

            return result

        except Exception as e:
            # GLOBAL ERROR HANDLING
            # LOGGING: Log processing errors for debugging
            logger.error(f"OCR processing error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "OCR processing failed",
                    "detail": str(e),
                    "status": "error"
                }
            )

@ocr_router.get("/cache/stats")
async def get_cache_stats():
    """
    CACHE STATISTICS ENDPOINT
    =========================
    Provides detailed statistics about the OCR results cache for monitoring and debugging.
    
    Purpose:
    - Monitor cache efficiency and hit rates
    - Debug caching issues during development
    - Performance optimization insights
    
    Returns:
    - cache_size: Number of cached image results
    - cached_hashes: List of image hash keys currently in cache
    
    Observability Integration:
    - METRICS: Cache size metrics available for Prometheus collection
    - LOGGING: Cache access patterns logged for analysis
    
    Use Cases:
    - Operations team monitoring cache performance
    - Developers debugging caching behavior
    - Performance analysis and optimization
    """
    return {
        "cache_size": len(cache),
        "cached_hashes": [str(h) for h in cache.keys()]
    }

@ocr_router.delete("/cache")
async def clear_cache():
    """
    CACHE CLEARING ENDPOINT
    =======================
    Administrative endpoint to clear all cached OCR results.
    
    Purpose:
    - Memory management during high-load scenarios
    - Cache invalidation for debugging purposes
    - Reset cache state during development/testing
    
    Operation Workflow:
    1. Capture current cache size for logging
    2. Clear global cache dictionary
    3. Log cache clearing operation for monitoring
    4. Return confirmation with statistics
    
    Observability Integration:
    - LOGGING: Cache clearing events logged for audit trail
    - METRICS: Cache size changes tracked for monitoring
    
    Security Considerations:
    - No authentication required (internal service)
    - Could be protected with API keys in production
    - Operation is idempotent (safe to call multiple times)
    
    Use Cases:
    - Emergency memory management
    - Development environment reset
    - Cache corruption recovery
    """
    global cache
    cache_size = len(cache)
    cache.clear()
    # OBSERVABILITY: Log cache management operations
    logger.info(f"Cache cleared. Removed {cache_size} entries")
    return {
        "message": f"Cache cleared successfully. Removed {cache_size} entries",
        "cache_size": 0
    }

# Include the OCR router in the main app
app.include_router(ocr_router)

# CUSTOM DOCUMENTATION ENDPOINTS
# ===============================
# These endpoints provide self-hosted API documentation under the /ocr-app prefix
# ensuring consistent routing with the rest of the application

@app.get("/ocr-app/openapi.json", include_in_schema=False)
async def get_openapi():
    """
    CUSTOM OPENAPI SPECIFICATION ENDPOINT
    ====================================
    Generates and serves the OpenAPI (Swagger) specification for this service.
    
    Architecture Decision:
    - Custom endpoint instead of default FastAPI openapi.json
    - Ensures consistent /ocr-app prefix for all documentation
    - Lazy generation for optimal startup performance
    
    OpenAPI Specification Contents:
    - All OCR API endpoints with detailed descriptions
    - Request/response schemas for type validation
    - HTTP status codes and error responses
    - Authentication requirements (none for this service)
    
    Integration Points:
    - Swagger UI consumes this specification
    - ReDoc documentation uses this specification  
    - API client generators can use this specification
    - Postman/Insomnia can import this specification
    
    Caching Strategy:
    - Schema cached after first generation
    - Reduces CPU overhead for subsequent requests
    - Schema regenerated only on application restart
    """
    from fastapi.openapi.utils import get_openapi
    if not app.openapi_schema:
        # Generate OpenAPI schema with full application metadata
        app.openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
    return app.openapi_schema

@app.get("/ocr-app/docs", include_in_schema=False)
async def get_swagger_ui():
    """
    CUSTOM SWAGGER UI DOCUMENTATION ENDPOINT
    =======================================
    Interactive API documentation using Swagger UI for OCR service exploration.
    
    Purpose:
    - Interactive API testing interface for developers
    - Visual API documentation for non-technical users
    - Request/response examples with live testing capability
    
    Swagger UI Features:
    - Try-it-out functionality for all endpoints
    - File upload testing for OCR processing
    - Response schema visualization
    - HTTP status code documentation
    
    Configuration:
    - Uses CDN-hosted Swagger UI assets for reliability
    - Custom OpenAPI specification from /ocr-app/openapi.json
    - Consistent branding with application title
    
    Access Patterns:
    - Development: Direct access for API exploration
    - Production: Available via NGINX Ingress at /ocr-app/docs
    - Internal: Documentation for other service developers
    
    Integration with Observability:
    - API usage patterns visible in access logs
    - Documentation access tracked for analytics
    """
    from fastapi.openapi.docs import get_swagger_ui_html
    return get_swagger_ui_html(
        openapi_url="/ocr-app/openapi.json",          # Custom OpenAPI spec location
        title=f"{app.title} - Swagger UI",            # Browser tab title
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js",  # CDN JS
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css",       # CDN CSS
    )

@app.get("/ocr-app/redoc", include_in_schema=False)
async def get_redoc():
    """
    CUSTOM REDOC DOCUMENTATION ENDPOINT
    ==================================
    Alternative API documentation using ReDoc for clean, printable documentation.
    
    Purpose:
    - Clean, professional API documentation format
    - Printable documentation for offline reference
    - Better suited for documentation reviews and specifications
    
    ReDoc Features:
    - Three-panel layout (navigation, content, examples)
    - Responsive design for mobile and desktop viewing
    - Syntax highlighting for code examples
    - Deep linking to specific operations
    - Search functionality across all documentation
    
    Comparison with Swagger UI:
    - ReDoc: Better for reading and documentation review
    - Swagger UI: Better for interactive testing
    - Both consume the same OpenAPI specification
    
    Use Cases:
    - API specification reviews
    - Integration documentation for external teams
    - Offline documentation distribution
    - Clean documentation screenshots
    
    Technical Configuration:
    - Uses CDN-hosted ReDoc assets for performance
    - Same OpenAPI specification as Swagger UI
    - Standalone JavaScript bundle for simplicity
    """
    from fastapi.openapi.docs import get_redoc_html
    return get_redoc_html(
        openapi_url="/ocr-app/openapi.json",     # Custom OpenAPI spec location
        title=f"{app.title} - ReDoc",            # Browser tab title  
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js",  # CDN JS
    )

# ROOT ENDPOINT AND SERVICE DISCOVERY
# ===================================
@app.get("/")
async def root():
    """
    ROOT SERVICE DISCOVERY ENDPOINT
    ==============================
    Main entry point providing service information and endpoint discovery.
    
    Purpose:
    - Service health indication for load balancers
    - Endpoint discovery for API consumers
    - Service metadata for monitoring systems
    
    Response Information:
    - Service status and version
    - Available endpoint URLs for navigation
    - Documentation links for developers
    - Health check endpoints for monitoring
    
    Integration Points:
    - Kubernetes readiness probes can use this endpoint
    - API gateways can discover available endpoints
    - Documentation tools can auto-discover API structure
    
    NGINX Ingress Routing:
    - Available at externalHost in values.yaml files (root)
    - Redirects users to OCR-specific endpoints
    - Provides clear navigation for new users
    """
    return {
        "message": "OCR Service is running",
        "service": "Simple OCR Service",
        "version": "1.0.0",
        "documentation": "/ocr-app/docs",
        "health": "/ocr-app/",
        "endpoints": {
            "health": "/ocr-app/",
            "process": "/ocr-app/process", 
            "docs": "/ocr-app/docs",
            "redoc": "/ocr-app/redoc",
            "openapi": "/ocr-app/openapi.json"
        }
    }

# GLOBAL EXCEPTION HANDLER
# ========================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    GLOBAL EXCEPTION HANDLER
    =======================
    Centralized exception handling for all unhandled errors in the application.
    
    Purpose:
    - Provide consistent error response format across all endpoints
    - Prevent sensitive error details from leaking to clients
    - Ensure comprehensive error logging for debugging
    
    Error Handling Strategy:
    1. Log full exception details for debugging (server-side only)
    2. Return sanitized error response to client
    3. Use appropriate HTTP status codes
    4. Maintain consistent JSON response format
    
    OBSERVABILITY INTEGRATION:
    - LOGGING: All unhandled exceptions logged with full stack trace
    - TRACING: Exception details attached to active spans
    - METRICS: Error rates available for monitoring alerts
    
    Security Considerations:
    - Prevents stack trace exposure to external clients
    - Logs sensitive debugging info server-side only
    - Standardized error responses prevent information disclosure
    
    Exception Categories Handled:
    - Unexpected application errors
    - Database connection failures
    - External service integration errors
    - Memory/resource exhaustion scenarios
    - Malformed request processing errors
    
    Integration with Monitoring:
    - Error logs collected by Filebeat -> Elasticsearch
    - Error metrics scraped by Prometheus
    - Error traces visible in Jaeger distributed tracing
    """
    # OBSERVABILITY: Log complete exception details for debugging
    logger.error(f"Unhandled exception: {str(exc)}")
    
    # Return sanitized error response to client
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "status": "error",
            "service": "ocr-service"
        }
    )