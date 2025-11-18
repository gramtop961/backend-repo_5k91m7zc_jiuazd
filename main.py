import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import re
import requests
from urllib.parse import urlparse

from database import db, create_document, get_documents
from schemas import DSProduct

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    url: HttpUrl

class SearchRequest(BaseModel):
    query: str
    limit: int = 12

@app.get("/")
def read_root():
    return {"message": "Dropship Finder API"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# Basic HTML parser helpers
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
META_TITLE_RE = re.compile(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\'](.*?)["\']', re.IGNORECASE)
META_IMG_RE = re.compile(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\'](.*?)["\']', re.IGNORECASE)
PRICE_RE = re.compile(r"(?:price|amount)\"?[:=]\"?\s*([0-9]+(?:\.[0-9]{2})?)", re.IGNORECASE)

COMMON_SHOP_PLATFORMS = ["shopify", "woocommerce", "magento", "bigcommerce", "aliexpress", "amazon"]


@app.post("/analyze", response_model=DSProduct)
def analyze_product(req: AnalyzeRequest):
    """Fetch basic signals from a product URL and score it heuristically."""
    url = str(req.url)
    try:
        resp = requests.get(url, timeout=8, headers={
            "User-Agent": "Mozilla/5.0 (compatible; DropshipFinder/1.0)"
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")

    if resp.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"Bad response: {resp.status_code}")

    html = resp.text

    # Title
    title = None
    m = META_TITLE_RE.search(html) or TITLE_RE.search(html)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:180]

    # Image
    images: Optional[List[str]] = None
    mimg = META_IMG_RE.findall(html)
    if mimg:
        images = list(dict.fromkeys(mimg))[:5]

    # Price
    price = None
    mprice = PRICE_RE.search(html)
    if mprice:
        try:
            price = float(mprice.group(1))
        except:
            price = None

    # Currency heuristic
    currency = None
    if "$" in html:
        currency = "USD"
    elif "€" in html:
        currency = "EUR"
    elif "£" in html:
        currency = "GBP"

    # Source/platform
    domain = urlparse(url).netloc
    source = domain
    for p in COMMON_SHOP_PLATFORMS:
        if p in html.lower() or p in domain.lower():
            source = p
            break

    # Simple niche tags
    tags: List[str] = []
    kw = html.lower()
    for t in ["pet", "cat", "dog", "fitness", "gym", "beauty", "home", "kitchen", "outdoor", "camp", "tech", "gadget", "baby", "kids"]:
        if t in kw:
            tags.append(t)
    tags = list(dict.fromkeys(tags))[:6]

    # Heuristic scoring
    estimated_demand = len(re.findall(r"add to cart|buy now|bestseller|sold", kw)) * 10
    supplier_count = len(re.findall(r"aliexpress|amazon|etsy|ebay", kw))
    score = max(10.0, min(95.0, 50 + (estimated_demand * 0.2) - (supplier_count * 5)))

    data = DSProduct(
        url=url,
        title=title,
        price=price,
        currency=currency,
        images=images,
        source=source,
        niche_tags=tags or None,
        score=round(score, 1),
        estimated_demand=estimated_demand,
        supplier_count=supplier_count,
    )

    try:
        create_document("dsproduct", data)
    except Exception:
        pass

    return data


@app.get("/discover", response_model=List[DSProduct])
def discover_products(q: str = Query("pet", max_length=40), limit: int = Query(8, ge=1, le=24)):
    """Return recently analyzed items matching a simple tag or domain filter."""
    flt = {}
    if q:
        flt = {"$or": [
            {"niche_tags": {"$regex": q, "$options": "i"}},
            {"source": {"$regex": q, "$options": "i"}},
            {"title": {"$regex": q, "$options": "i"}},
        ]}
    try:
        docs = get_documents("dsproduct", flt, limit)
    except Exception:
        docs = []
    out: List[DSProduct] = []
    for d in docs:
        out.append(DSProduct(
            url=d.get("url"),
            title=d.get("title"),
            price=d.get("price"),
            currency=d.get("currency"),
            images=d.get("images"),
            source=d.get("source"),
            niche_tags=d.get("niche_tags"),
            score=d.get("score"),
            estimated_demand=d.get("estimated_demand"),
            supplier_count=d.get("supplier_count"),
        ))
    return out


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
