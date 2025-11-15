#import username search function
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from heatmap.services.trends import get_country_search_density
from username_tracker.routers.maigret_router import router as maigret_router
from socialmediatracer.tikspyder_wrapper import fetch_tiktok_by_query
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx
import trio
import importlib
import pkgutil
import re
import asyncio
from functools import partial


app = FastAPI()
app.include_router(maigret_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

# CORS so your frontend can call it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to ["http://localhost:3000", ...]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#heatmap endpoint
@app.get("/search")
def search_keyword(keyword: str):
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword is required")
    
    result = get_country_search_density(keyword)
    return {
        "keyword": keyword,
        "results": result
    }

@app.get("/tiktok/search")
def tiktok_search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(25, ge=1, le=200),
    use_apify: bool = Query(False, description="Use Apify to enrich results"),
):
    """
    Run TikSpyder for the given query and return JSON
    (search_results + related_content from CSVs).
    """
    try:
        data = fetch_tiktok_by_query(
            query=q,
            use_apify=use_apify,
            number_of_results=limit,
        )
        return data
    except Exception as e:
        # in production, log this properly
        raise HTTPException(status_code=500, detail=str(e))
    
"""
FastAPI Backend for Holehe Email Checker
Simple, production-ready implementation
"""



# Email validation regex
EMAIL_FORMAT = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# Domain mapping for services
DOMAIN_MAP = {
    'aboutme': 'about.me', 'adobe': 'adobe.com', 'amazon': 'amazon.com', 
    'anydo': 'any.do', 'archive': 'archive.org', 'armurerieauxerre': 'armurerie-auxerre.com',
    'atlassian': 'atlassian.com', 'instagram': 'instagram.com', 'twitter': 'twitter.com', 
    'github': 'github.com', 'google': 'google.com', 'spotify': 'spotify.com',
    'discord': 'discord.com', 'tumblr': 'tumblr.com', 'pinterest': 'pinterest.com',
    'facebook': 'facebook.com', 'linkedin': 'linkedin.com', 'snapchat': 'snapchat.com',
    'reddit': 'reddit.com', 'tiktok': 'tiktok.com', 'netflix': 'netflix.com'
}

# Pydantic Models
class EmailCheckRequest(BaseModel):
    email: EmailStr
    exclude_password_recovery: Optional[bool] = True
    only_found: Optional[bool] = False

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "exclude_password_recovery": True,
                "only_found": False
            }
        }


class PlatformInfo(BaseModel):
    platform: str
    name: str
    exists: bool
    email_recovery: Optional[str] = None
    phone_number: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None


class EmailCheckResponse(BaseModel):
    success: bool
    email: str
    total_checked: int
    found_count: int
    platforms_found: List[str]
    detailed_results: Optional[List[PlatformInfo]] = None
    checked_at: str


# Core Holehe Functions
def import_holehe_modules(package_name: str = "holehe.modules"):
    """Import all holehe submodules"""
    try:
        package = importlib.import_module(package_name)
    except ImportError:
        raise ImportError(
            "Holehe package not found. Install it with: pip install holehe"
        )
    
    results = {}
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + '.' + name
        try:
            results[full_name] = importlib.import_module(full_name)
            if is_pkg:
                results.update(import_holehe_modules(full_name))
        except Exception as e:
            print(f"Warning: Could not import {full_name}: {e}")
    return results


def get_check_functions(modules: Dict, exclude_password_recovery: bool = True):
    """Extract check functions from modules"""
    websites = []
    exclude_list = ["adobe", "mail_ru", "odnoklassniki", "samsung"]
    
    for module_name, module in modules.items():
        if len(module_name.split(".")) > 3:
            site = module_name.split(".")[-1]
            if site in module.__dict__:
                if exclude_password_recovery:
                    if not any(excluded in str(module.__dict__[site]) for excluded in exclude_list):
                        websites.append(module.__dict__[site])
                else:
                    websites.append(module.__dict__[site])
    return websites


def is_valid_email(email: str) -> bool:
    """Validate email format"""
    return bool(re.fullmatch(EMAIL_FORMAT, email))


async def launch_module_check(module, email: str, client: httpx.AsyncClient, results: List):
    """Execute a single module check"""
    try:
        await module(email, client, results)
    except Exception as e:
        name = str(module).split('<function ')[1].split(' ')[0] if '<function' in str(module) else 'unknown'
        domain = DOMAIN_MAP.get(name, "unknown")
        results.append({
            "name": name,
            "domain": domain,
            "rateLimit": False,
            "error": True,
            "exists": False,
            "emailrecovery": None,
            "phoneNumber": None,
            "others": None
        })


async def check_email_trio(email: str, exclude_password_recovery: bool = True, timeout: int = 15):
    """Main function to check email across all platforms using Trio"""
    if not is_valid_email(email):
        raise ValueError(f"Invalid email format: {email}")
    
    # Import modules
    modules = import_holehe_modules()
    websites = get_check_functions(modules, exclude_password_recovery)
    
    results = []
    
    # Run checks
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with trio.open_nursery() as nursery:
            for website in websites:
                nursery.start_soon(launch_module_check, website, email, client, results)
    
    # Sort results
    results.sort(key=lambda x: x.get('name', ''))
    return results


async def check_email_on_platforms(email: str, exclude_password_recovery: bool = True, timeout: int = 15):
    """Wrapper to run Trio code from asyncio"""
    # Run the trio coroutine in a thread pool to avoid event loop conflicts
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        partial(trio.run, check_email_trio, email, exclude_password_recovery, timeout)
    )


def format_results(raw_results: List[Dict], email: str, only_found: bool = False):
    """Format raw results into API response"""
    platforms_found = []
    detailed_results = []
    
    for result in raw_results:
        if result.get('exists'):
            platform_name = result.get('domain', 'unknown')
            platforms_found.append(platform_name)
            
            detailed_results.append(PlatformInfo(
                platform=platform_name,
                name=result.get('name', ''),
                exists=True,
                email_recovery=result.get('emailrecovery'),
                phone_number=result.get('phoneNumber'),
                additional_info=result.get('others')
            ))
        elif not only_found:
            detailed_results.append(PlatformInfo(
                platform=result.get('domain', 'unknown'),
                name=result.get('name', ''),
                exists=False
            ))
    
    return EmailCheckResponse(
        success=True,
        email=email,
        total_checked=len(raw_results),
        found_count=len(platforms_found),
        platforms_found=platforms_found,
        detailed_results=detailed_results if not only_found else None,
        checked_at=datetime.utcnow().isoformat()
    )


# API Endpoints
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Email Platform Checker",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.post("/api/check-email", response_model=EmailCheckResponse, tags=["Email Check"])
async def check_email_post(request: EmailCheckRequest):
    """
    Check which platforms an email is registered on (POST)
    
    - **email**: Email address to check
    - **exclude_password_recovery**: Skip modules that trigger password recovery emails
    - **only_found**: Return only platforms where email exists (simplified response)
    
    Returns detailed information about where the email is registered.
    """
    try:
        # Run the check
        raw_results = await check_email_on_platforms(
            email=request.email,
            exclude_password_recovery=request.exclude_password_recovery
        )
        
        # Format and return results
        formatted_response = format_results(
            raw_results=raw_results,
            email=request.email,
            only_found=request.only_found
        )
        
        return formatted_response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Holehe module error: {str(e)}. Make sure holehe is installed."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/api/check-email", tags=["Email Check"])
async def check_email_get(
    email: str = Query(..., description="Email address to check", example="user@example.com"),
    only_found: bool = Query(True, description="Return only platforms where email exists")
):
    """
    Quick email check via GET request with query parameter
    
    - **email**: Email address to check (query parameter)
    - **only_found**: Return only found platforms (default: true)
    
    Example: /api/check-email?email=user@example.com
    
    Returns a simplified list of platforms where the email is registered.
    """
    try:
        # Validate email
        if not is_valid_email(email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        # Run the check
        raw_results = await check_email_on_platforms(email=email)
        
        # Get only platforms where email exists
        platforms_found = [
            r.get('domain', 'unknown') 
            for r in raw_results 
            if r.get('exists', False)
        ]
        
        return {
            "success": True,
            "email": email,
            "platforms_found": platforms_found,
            "count": len(platforms_found),
            "checked_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/api/batch-check", tags=["Email Check"])
async def batch_check_emails(emails: List[EmailStr]):
    """
    Check multiple emails in one request
    
    - **emails**: List of email addresses to check (max 5)
    
    Returns results for each email address.
    """
    if len(emails) > 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 emails per batch request"
        )
    
    results = {}
    
    for email in emails:
        try:
            raw_results = await check_email_on_platforms(email=email)
            platforms_found = [
                r.get('domain', 'unknown') 
                for r in raw_results 
                if r.get('exists', False)
            ]
            
            results[email] = {
                "success": True,
                "platforms_found": platforms_found,
                "count": len(platforms_found)
            }
        except Exception as e:
            results[email] = {
                "success": False,
                "error": str(e),
                "platforms_found": [],
                "count": 0
            }
    
    return {
        "success": True,
        "total_emails": len(emails),
        "results": results,
        "checked_at": datetime.utcnow().isoformat()
    }


@app.get("/api/supported-platforms", tags=["Info"])
async def get_supported_platforms():
    """
    Get list of all supported platforms
    
    Returns a list of all platforms that can be checked.
    """
    try:
        modules = import_holehe_modules()
        websites = get_check_functions(modules)
        
        platform_names = []
        for website in websites:
            name = str(website).split('<function ')[1].split(' ')[0] if '<function' in str(website) else 'unknown'
            domain = DOMAIN_MAP.get(name, name)
            if domain not in platform_names:
                platform_names.append(domain)
        
        return {
            "success": True,
            "total_platforms": len(platform_names),
            "platforms": sorted(platform_names)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading platforms: {str(e)}")

