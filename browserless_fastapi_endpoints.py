"""
Browserless.io FastAPI Endpoints
Add these endpoints to your app_fastapi.py

Usage:
    1. Import this module in app_fastapi.py
    2. Call register_browserless_routes(app) to add endpoints
    
    OR
    
    Copy these endpoints directly into app_fastapi.py
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import base64
import os
from datetime import datetime

# Import the browserless integration
try:
    from browserless_integration import UnifiedScraperService, get_scraper_service
except ImportError:
    print("⚠️  browserless_integration.py not found. Make sure it's in the same directory.")
    UnifiedScraperService = None
    get_scraper_service = None


# ============================================
# REQUEST MODELS
# ============================================

class JobSearchRequest(BaseModel):
    """Job search request parameters"""
    keywords: str = Field(..., description="Search keywords (e.g., 'AI automation specialist')")
    location: str = Field(default="", description="Location filter (e.g., 'remote', 'Austin TX')")
    sources: List[str] = Field(
        default=["indeed", "wellfound"],
        description="Job sources: indeed, wellfound, remote_co, linkedin, flexjobs"
    )
    remote_only: bool = Field(default=False, description="Filter for remote jobs only")

class PropertySearchRequest(BaseModel):
    """Property search request parameters"""
    address: str = Field(..., description="Street address")
    city: str = Field(..., description="City name")
    state: str = Field(default="TX", description="State abbreviation")
    zipcode: Optional[str] = Field(default=None, description="ZIP code")

class PersonSearchRequest(BaseModel):
    """Person search request parameters"""
    name: str = Field(..., description="Full name to search")
    city: Optional[str] = Field(default=None, description="City to narrow search")
    state: str = Field(default="TX", description="State abbreviation")

class InstagramRequest(BaseModel):
    """Instagram profile request"""
    username: str = Field(..., description="Instagram username (without @)")

class PageContentRequest(BaseModel):
    """Page content/screenshot request"""
    url: str = Field(..., description="URL to fetch/capture")
    wait_for: Optional[str] = Field(default=None, description="CSS selector to wait for")
    full_page: bool = Field(default=False, description="Capture full page (for screenshots)")

class ClosedClinicsRequest(BaseModel):
    """Closed clinics search request"""
    cities: List[str] = Field(
        default=["Austin", "San Antonio", "Houston"],
        description="Cities to search"
    )
    state: str = Field(default="TX", description="State abbreviation")


# ============================================
# RESPONSE MODELS
# ============================================

class JobSearchResponse(BaseModel):
    """Job search response"""
    status: str
    data: Dict[str, List[Dict]]
    total: int
    timestamp: str

class PropertySearchResponse(BaseModel):
    """Property search response"""
    status: str
    data: Dict
    timestamp: str

class ScreenshotResponse(BaseModel):
    """Screenshot response"""
    status: str
    image: str  # Base64 encoded
    content_type: str
    timestamp: str


# ============================================
# SINGLETON SERVICE INSTANCE
# ============================================

_scraper_service = None

def get_service() -> UnifiedScraperService:
    """Get or create scraper service singleton"""
    global _scraper_service
    if _scraper_service is None:
        api_key = os.environ.get('BROWSERLESS_API_KEY', '')
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="BROWSERLESS_API_KEY not configured. Set environment variable."
            )
        _scraper_service = get_scraper_service(api_key)
    return _scraper_service


# ============================================
# ROUTE REGISTRATION
# ============================================

def register_browserless_routes(app: FastAPI):
    """
    Register all Browserless.io scraping endpoints with the FastAPI app
    
    Usage:
        from browserless_fastapi_endpoints import register_browserless_routes
        register_browserless_routes(app)
    """
    
    # ============================================
    # JOB SCRAPING ENDPOINTS
    # ============================================
    
    @app.post("/api/scrape/jobs", response_model=JobSearchResponse, tags=["Browserless Scrapers"])
    async def scrape_jobs(request: JobSearchRequest):
        """
        Scrape jobs from multiple platforms using Browserless.io
        
        Supported sources:
        - indeed: Indeed.com job listings
        - wellfound: Wellfound (AngelList) startup jobs
        - remote_co: Remote.co remote jobs
        - linkedin: LinkedIn profiles (public)
        - flexjobs: FlexJobs listings
        """
        try:
            service = get_service()
            results = service.scrape_jobs(
                keywords=request.keywords,
                location=request.location,
                sources=request.sources,
                remote_only=request.remote_only
            )
            return {
                'status': 'success',
                'data': results,
                'total': sum(len(v) for v in results.values()),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/scrape/jobs/ai-automation", tags=["Browserless Scrapers"])
    async def scrape_ai_automation_jobs():
        """
        Quick endpoint to scrape AI Automation jobs from all sources
        """
        try:
            service = get_service()
            results = service.scrape_jobs(
                keywords="AI automation specialist",
                location="remote",
                sources=['indeed', 'wellfound', 'remote_co']
            )
            return {
                'status': 'success',
                'data': results,
                'total': sum(len(v) for v in results.values()),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/scrape/jobs/healthcare-liaison", tags=["Browserless Scrapers"])
    async def scrape_healthcare_liaison_jobs():
        """
        Quick endpoint to scrape Healthcare Liaison jobs
        """
        try:
            service = get_service()
            results = service.scrape_jobs(
                keywords="healthcare liaison remote",
                location="remote",
                sources=['indeed', 'flexjobs']
            )
            return {
                'status': 'success',
                'data': results,
                'total': sum(len(v) for v in results.values()),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ============================================
    # PROPERTY SCRAPING ENDPOINTS
    # ============================================
    
    @app.post("/api/scrape/property", response_model=PropertySearchResponse, tags=["Browserless Scrapers"])
    async def scrape_property(request: PropertySearchRequest):
        """
        Scrape property information using Browserless.io + Spokeo
        
        Returns owner name, phone, email, and property details
        """
        try:
            service = get_service()
            results = service.scrape_property(
                address=request.address,
                city=request.city,
                state=request.state,
                zipcode=request.zipcode
            )
            return {
                'status': 'success',
                'data': results,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/scrape/person", tags=["Browserless Scrapers"])
    async def scrape_person(request: PersonSearchRequest):
        """
        Search for person information using Browserless.io
        """
        try:
            service = get_service()
            results = service.scrape_person(
                name=request.name,
                city=request.city,
                state=request.state
            )
            return {
                'status': 'success',
                'data': results,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ============================================
    # INSTAGRAM SCRAPING
    # ============================================
    
    @app.get("/api/scrape/instagram/{username}", tags=["Browserless Scrapers"])
    async def scrape_instagram(username: str):
        """
        Scrape Instagram profile using Browserless.io
        
        Returns profile info, follower counts, bio, etc.
        """
        try:
            service = get_service()
            profile = service.scrape_instagram(username)
            return {
                'status': 'success',
                'data': profile,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/scrape/instagram", tags=["Browserless Scrapers"])
    async def scrape_instagram_post(request: InstagramRequest):
        """
        Scrape Instagram profile (POST version)
        """
        try:
            service = get_service()
            profile = service.scrape_instagram(request.username)
            return {
                'status': 'success',
                'data': profile,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ============================================
    # STEM CELL / PRP CLINIC SCRAPING
    # ============================================
    
    @app.post("/api/scrape/closed-clinics", tags=["Browserless Scrapers"])
    async def scrape_closed_clinics(request: ClosedClinicsRequest):
        """
        Search for closed stem cell/PRP treatment centers
        
        Searches Google for clinics that went out of business
        """
        try:
            service = get_service()
            results = service.scrape_closed_clinics(
                cities=request.cities,
                state=request.state
            )
            return {
                'status': 'success',
                'data': results,
                'total': sum(len(v) for v in results.values()),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/scrape/closed-clinics/texas", tags=["Browserless Scrapers"])
    async def scrape_texas_closed_clinics():
        """
        Quick endpoint to search for closed clinics in Austin, San Antonio, Houston
        """
        try:
            service = get_service()
            results = service.scrape_closed_clinics(
                cities=['Austin', 'San Antonio', 'Houston'],
                state='TX'
            )
            return {
                'status': 'success',
                'data': results,
                'total': sum(len(v) for v in results.values()),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ============================================
    # PAGE CONTENT & SCREENSHOT ENDPOINTS
    # ============================================
    
    @app.post("/api/scrape/content", tags=["Browserless Scrapers"])
    async def get_page_content(request: PageContentRequest):
        """
        Get rendered page content using Browserless.io
        
        Renders JavaScript and returns HTML content
        """
        try:
            service = get_service()
            content = service.get_page_content(request.url, request.wait_for)
            return {
                'status': 'success',
                'content': content[:50000] if content else None,  # Limit response size
                'full_length': len(content) if content else 0,
                'truncated': len(content) > 50000 if content else False,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/scrape/screenshot", tags=["Browserless Scrapers"])
    async def take_screenshot(request: PageContentRequest):
        """
        Take screenshot of a URL using Browserless.io
        
        Returns base64 encoded PNG image
        """
        try:
            service = get_service()
            screenshot = service.take_screenshot(request.url, request.full_page)
            if screenshot:
                return {
                    'status': 'success',
                    'image': base64.b64encode(screenshot).decode('utf-8'),
                    'content_type': 'image/png',
                    'size_bytes': len(screenshot),
                    'timestamp': datetime.now().isoformat()
                }
            raise HTTPException(status_code=500, detail="Failed to capture screenshot")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/scrape/screenshot/raw", tags=["Browserless Scrapers"])
    async def take_screenshot_raw(request: PageContentRequest):
        """
        Take screenshot and return as raw PNG image
        """
        try:
            service = get_service()
            screenshot = service.take_screenshot(request.url, request.full_page)
            if screenshot:
                return Response(
                    content=screenshot,
                    media_type="image/png",
                    headers={"Content-Disposition": f"attachment; filename=screenshot.png"}
                )
            raise HTTPException(status_code=500, detail="Failed to capture screenshot")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/scrape/pdf", tags=["Browserless Scrapers"])
    async def generate_pdf(request: PageContentRequest):
        """
        Generate PDF from URL using Browserless.io
        """
        try:
            service = get_service()
            pdf = service.generate_pdf(request.url)
            if pdf:
                return Response(
                    content=pdf,
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=page.pdf"}
                )
            raise HTTPException(status_code=500, detail="Failed to generate PDF")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ============================================
    # HEALTH & STATUS
    # ============================================
    
    @app.get("/api/scrape/health", tags=["Browserless Scrapers"])
    async def browserless_health():
        """
        Check Browserless.io connection status
        """
        api_key = os.environ.get('BROWSERLESS_API_KEY', '')
        return {
            'status': 'ok' if api_key else 'not_configured',
            'api_key_set': bool(api_key),
            'api_key_preview': f"{api_key[:8]}..." if api_key else None,
            'timestamp': datetime.now().isoformat()
        }
    
    print("✓ Browserless.io endpoints registered:")
    print("  POST /api/scrape/jobs")
    print("  GET  /api/scrape/jobs/ai-automation")
    print("  GET  /api/scrape/jobs/healthcare-liaison")
    print("  POST /api/scrape/property")
    print("  POST /api/scrape/person")
    print("  GET  /api/scrape/instagram/{username}")
    print("  POST /api/scrape/closed-clinics")
    print("  GET  /api/scrape/closed-clinics/texas")
    print("  POST /api/scrape/content")
    print("  POST /api/scrape/screenshot")
    print("  POST /api/scrape/pdf")
    print("  GET  /api/scrape/health")


# ============================================
# STANDALONE APP (for testing)
# ============================================

def create_standalone_app() -> FastAPI:
    """Create standalone FastAPI app with browserless endpoints"""
    app = FastAPI(
        title="StormBuster Browserless Scraper API",
        description="Unified scraping service using Browserless.io",
        version="1.0.0"
    )
    
    register_browserless_routes(app)
    
    @app.get("/")
    async def root():
        return {
            "service": "StormBuster Browserless Scraper API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/scrape/health"
        }
    
    return app


# For running standalone
if __name__ == "__main__":
    import uvicorn
    
    print("=" * 50)
    print("STARTING BROWSERLESS SCRAPER API")
    print("=" * 50)
    
    app = create_standalone_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)

