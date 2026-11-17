# PARTS GARAGE API

FastAPI backend for the PARTS GARAGE GitHub Pages storefront.

## Endpoints

- GET /api/health — service and integration status.
- POST /api/v1/vehicles/identify — VIN to TecDoc KType/NType and vehicle attributes.
- GET /api/v1/vehicles/{ktype}/articles — TecDoc parts linked to a selected passenger-car KType.

## Local start

1. Copy .env.example to .env.
2. Fill in the TecAlliance credentials and the exact licensed TecDoc Web Service endpoint/request template.
3. Install dependencies: pip install -r requirements.txt
4. Start: uvicorn app.main:app --reload --port 8000
5. Open http://localhost:8000/docs

## TecAlliance configuration

The VIN adapter uses the documented global Vehicle Identification Service route:

GET {TECDOC_VIN_BASE_URL}/api/v1/vin/{country}/{vin}

The route returns the TecDoc vehicle matches and KType/NType data. A VIN may return multiple variants; the storefront asks the customer to select the correct one.

The parts adapter deliberately takes TECDOC_PARTS_URL and TECDOC_PARTS_REQUEST_TEMPLATE from environment variables. TecDoc Web Service contracts can differ by product, region and licence, and may use REST/JSON or SOAP. Do not guess an endpoint or reuse the China-only OneDB endpoint for a different market. Obtain the Web Service endpoint, authentication rules and request/response schema from your TecAlliance account manager, then set the environment values. The JSON template supports {ktype}, {country}, {language}, {page} and {per_page} placeholders.

Optional TECDOC_PRODUCT_GROUP_MAP is a JSON object mapping the storefront categories (engine, brakes, suspension, electrics, body, consumables) to the product-group IDs included in your licensed catalogue.

## Secrets

Never commit API keys to GitHub or put them in frontend JavaScript. Set them in the backend host's environment/secrets settings.

## Deployment

The repository includes a root render.yaml Blueprint. In Render, choose New + → Blueprint, connect this repository and review the service. Set the secret values in the Render dashboard, then deploy. The expected service URL is https://parts-garage-api.onrender.com; if Render assigns a different URL, update PG_API_BASE_URL in the root config.js.

## Important limitations

- TecAlliance access requires an active licence/API credentials. A backend scaffold does not grant catalogue access.
- TecDoc catalogue data provides reference parts and fitment, not necessarily the shop's selling price or live stock. Retail prices/availability require a separate supplier/ERP feed.
- The API key stays on the backend and is never sent to the browser.
