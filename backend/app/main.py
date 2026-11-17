from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .schemas import VinIdentifyRequest
from .tecdoc import ProviderNotConfigured, TecDocClient, TecDocProviderError

settings = get_settings()
app = FastAPI(
    title="PARTS GARAGE API",
    version="1.0.0",
    description="Backend proxy for TecAlliance Vehicle Identification and TecDoc Web Service.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


def get_client() -> TecDocClient:
    return TecDocClient(settings)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "PARTS GARAGE API",
        "integrations": {
            "vin_configured": bool(settings.tecdoc_vin_api_key),
            "parts_configured": bool(
                settings.tecdoc_parts_url
                and settings.tecdoc_parts_api_key
                and settings.tecdoc_parts_request_template
            ),
        },
    }


@app.post("/api/v1/vehicles/identify")
async def identify_vehicle(request: VinIdentifyRequest):
    country = (request.country or settings.tecdoc_vin_country).upper()
    extra = {
        "make": request.make,
        "model": request.model,
        "dateFirstReg": request.date_first_reg,
        "body": request.body,
        "doors": request.doors,
        "fuel": request.fuel,
        "gearboxType": request.gearbox_type,
        "gearboxCode": request.gearbox_code,
        "cc": request.cc,
        "kw": request.kw,
        "engineCode": request.engine_code,
    }
    try:
        vehicles = await get_client().identify_vin(request.vin, country, extra)
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TecDocProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not vehicles:
        raise HTTPException(
            status_code=404,
            detail="TecDoc не нашёл автомобиль по этому VIN. Проверь VIN или уточни комплектацию.",
        )
    return {
        "vin": request.vin,
        "country": country,
        "vehicle_count": len(vehicles),
        "vehicles": vehicles,
        "source": "TecAlliance Vehicle Identification Service",
    }


@app.get("/api/v1/vehicles/{ktype}/articles")
async def vehicle_articles(
    ktype: str,
    country: str = Query(default=settings.tecdoc_catalog_country, min_length=2, max_length=2),
    language: str = Query(default=settings.tecdoc_catalog_language, min_length=2, max_length=2),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=24, ge=1, le=100),
    category: str | None = None,
):
    if not ktype.isdigit():
        raise HTTPException(status_code=400, detail="Некорректный TecDoc KType.")
    try:
        result = await get_client().search_vehicle_parts(
            ktype=ktype,
            country=country.upper(),
            language=language.upper(),
            page=page,
            per_page=per_page,
            category=category,
        )
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TecDocProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return result


@app.get("/")
async def root():
    return {"service": "PARTS GARAGE API", "health": "/api/health", "docs": "/docs"}
