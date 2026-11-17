import json
from typing import Any
from urllib.parse import quote

import httpx

from .config import Settings


class ProviderNotConfigured(Exception):
    pass


class TecDocProviderError(Exception):
    pass


def _auth_headers(key: str, header_name: str, prefix: str) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if key:
        headers[header_name or "Authorization"] = f"{prefix or ''}{key}"
    return headers


def _first(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _vehicle_from_raw(raw: dict[str, Any]) -> dict[str, Any]:
    info = raw.get("vehicleInformation") if isinstance(raw.get("vehicleInformation"), dict) else {}
    engines = raw.get("engines") if isinstance(raw.get("engines"), list) else []
    engine = engines[0] if engines and isinstance(engines[0], dict) else {}
    ktype_data = raw.get("ktype") if isinstance(raw.get("ktype"), dict) else {}

    ktype = _first(
        raw.get("kType"), raw.get("ktypeId"), raw.get("ktypeId"),
        ktype_data.get("kType"), ktype_data.get("ktype"), ktype_data.get("id"), raw.get("ktype"), raw.get("typeId")
    )
    ntype = _first(raw.get("nType"), raw.get("ntypeId"))
    make = _first(raw.get("make"), raw.get("manufacturer"), info.get("make"), info.get("manufacturer"))
    model = _first(raw.get("model"), info.get("model"), raw.get("modelName"), ktype_data.get("modelName"))
    year_from = _first(raw.get("yearFrom"), raw.get("constructionFrom"), info.get("yearFrom"), info.get("constructionStart"))
    year_to = _first(raw.get("yearTo"), raw.get("constructionTo"), info.get("yearTo"), info.get("constructionEnd"))
    engine_code = _first(raw.get("engineCode"), engine.get("engineCode"), engine.get("code"))
    fuel = _first(raw.get("fuel"), raw.get("fuelType"), engine.get("fuelType"))
    capacity = _first(raw.get("cc"), raw.get("cylinderCapacityCcm"), engine.get("cylinderCapacityCcm"), engine.get("displacement"))
    power = _first(raw.get("kw"), raw.get("powerKW"), engine.get("powerKW"), engine.get("powerKw"))
    body = _first(raw.get("body"), raw.get("bodyType"), info.get("bodyType"))

    title_parts = [str(x) for x in (year_from, make, model) if x]
    title = " ".join(title_parts) or str(_first(raw.get("description"), raw.get("name"), "Автомобиль TecDoc"))
    fields = []
    for label, value in [
        ("Марка", make), ("Модель", model), ("Год от", year_from),
        ("Год до", year_to), ("Двигатель", engine_code),
        ("Объём, см³", capacity), ("Мощность, кВт", power),
        ("Топливо", fuel), ("Кузов", body),
    ]:
        if value not in (None, ""):
            fields.append({"label": label, "value": str(value)})

    return {
        "ktype": str(ktype) if ktype else None,
        "ntype": str(ntype) if ntype else None,
        "make": make,
        "model": model,
        "title": title,
        "year_from": year_from,
        "year_to": year_to,
        "engine_code": engine_code,
        "fuel": fuel,
        "capacity_cc": capacity,
        "power_kw": power,
        "body": body,
        "fields": fields,
        "raw": raw,
    }


def _extract_vehicles(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        source = payload
    elif isinstance(payload, dict):
        source = payload.get("vehicles") or payload.get("data") or payload.get("results") or []
        if isinstance(source, dict):
            source = source.get("vehicles") or source.get("results") or [source]
    else:
        source = []

    result = []
    for item in source:
        if not isinstance(item, dict):
            continue
        normalized = _vehicle_from_raw(item)
        if normalized["ktype"] or normalized["ntype"]:
            result.append(normalized)
    return result


def _render_template(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _render_template(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [_render_template(item, context) for item in value]
    if isinstance(value, str):
        try:
            return value.format(**context)
        except (KeyError, ValueError):
            return value
    return value


def _extract_articles(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("articles", "parts", "results", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("articles", "parts", "results", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


def _normalize_article(raw: dict[str, Any]) -> dict[str, Any]:
    generic = raw.get("genericArticles") or raw.get("genericArticle") or []
    if isinstance(generic, dict):
        generic = [generic]
    generic_names = [
        str(item.get("genericArticleDescription") or item.get("description") or item.get("name"))
        for item in generic if isinstance(item, dict)
    ]
    article_text = raw.get("articleText")
    if isinstance(article_text, list):
        descriptions = [
            str(item.get("text") or item.get("description") or "")
            for item in article_text if isinstance(item, dict)
        ]
        description = " ".join(x for x in descriptions if x)
    elif isinstance(article_text, dict):
        description = str(article_text.get("text") or article_text.get("description") or "")
    else:
        description = str(article_text or raw.get("description") or "")

    images_raw = raw.get("images") or raw.get("image") or []
    if isinstance(images_raw, dict):
        images_raw = [images_raw]
    images = []
    for image in images_raw:
        if isinstance(image, str) and image.startswith("https://"):
            images.append(image)
        elif isinstance(image, dict):
            url = image.get("url") or image.get("imageUrl")
            if isinstance(url, str) and url.startswith("https://"):
                images.append(url)

    oe_raw = raw.get("oemNumbers") or raw.get("oeNumbers") or []
    if isinstance(oe_raw, dict):
        oe_raw = [oe_raw]
    oe_numbers = []
    for item in oe_raw:
        if isinstance(item, str):
            oe_numbers.append(item)
        elif isinstance(item, dict):
            number = item.get("articleNumber") or item.get("number") or item.get("oeNumber")
            if number:
                oe_numbers.append(str(number))

    criteria_raw = raw.get("articleCriteria") or raw.get("criteria") or []
    criteria = []
    for item in criteria_raw:
        if isinstance(item, dict):
            name = item.get("criteriaDescription") or item.get("name")
            value = item.get("formatedVal") or item.get("formattedValue") or item.get("rawValue") or item.get("value")
            if name and value not in (None, ""):
                criteria.append({"name": str(name), "value": str(value)})

    misc = raw.get("misc") if isinstance(raw.get("misc"), dict) else {}
    price = _first(raw.get("price"), raw.get("retailPrice"), raw.get("salesPrice"), misc.get("price"))
    uid = _first(raw.get("uid"), raw.get("id"), raw.get("articleId"))
    article_number = _first(raw.get("articleNumber"), raw.get("partNumber"), raw.get("number"))
    brand = _first(raw.get("mfrName"), raw.get("manufacturerName"), raw.get("brand"), raw.get("supplierName"))
    name = _first(raw.get("name"), raw.get("title"), raw.get("description"), generic_names[0] if generic_names else None, article_number)

    return {
        "uid": str(uid) if uid is not None else None,
        "article_number": str(article_number) if article_number is not None else "",
        "brand": str(brand) if brand is not None else "Производитель не указан",
        "name": str(name) if name is not None else "Запчасть TecDoc",
        "description": description,
        "generic_article": generic_names[0] if generic_names else "",
        "oe_numbers": oe_numbers,
        "images": images,
        "criteria": criteria,
        "price": float(price) if isinstance(price, (int, float)) else None,
        "raw": raw,
    }


class TecDocClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def identify_vin(self, vin: str, country: str, extra: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not self.settings.tecdoc_vin_api_key:
            raise ProviderNotConfigured("Не заданы реквизиты TecAlliance Vehicle Identification Service.")
        base = self.settings.tecdoc_vin_base_url.rstrip("/")
        url = f"{base}/api/v1/vin/{quote(country.lower())}/{quote(vin)}"
        headers = _auth_headers(
            self.settings.tecdoc_vin_api_key,
            self.settings.tecdoc_vin_auth_header,
            self.settings.tecdoc_vin_auth_prefix,
        )
        params = {key: value for key, value in (extra or {}).items() if value not in (None, "")}
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(url, headers=headers, params=params)
            except httpx.HTTPError as exc:
                raise TecDocProviderError("Не удалось связаться с TecAlliance VIN Service.") from exc
        if response.status_code == 404:
            return []
        if response.status_code in (401, 403):
            raise TecDocProviderError("TecAlliance отклонила доступ к VIN Service. Проверь API-ключ и права лицензии.")
        if response.status_code == 429:
            raise TecDocProviderError("TecAlliance временно ограничила частоту запросов. Попробуй позже.")
        if response.status_code >= 400:
            raise TecDocProviderError(f"TecAlliance VIN Service вернула HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise TecDocProviderError("TecAlliance VIN Service вернула ответ не в JSON.") from exc
        vehicles = _extract_vehicles(payload)
        if not vehicles and isinstance(payload, dict) and payload.get("error"):
            raise TecDocProviderError(str(payload["error"]))
        return vehicles

    async def search_vehicle_parts(
        self, ktype: str, country: str, language: str, page: int, per_page: int, category: str | None = None
    ) -> dict[str, Any]:
        if not self.settings.tecdoc_parts_url or not self.settings.tecdoc_parts_api_key:
            raise ProviderNotConfigured("Не настроен TecDoc Web Service: нужны URL каталога и API-реквизиты.")
        if not self.settings.tecdoc_parts_request_template:
            raise ProviderNotConfigured("Не задан формат запроса TecDoc Web Service. Нужен шаблон из документации к вашей лицензии.")

        try:
            template = json.loads(self.settings.tecdoc_parts_request_template)
        except json.JSONDecodeError as exc:
            raise ProviderNotConfigured("TECDOC_PARTS_REQUEST_TEMPLATE должен содержать корректный JSON.") from exc

        context = {
            "ktype": str(ktype),
            "country": country,
            "language": language,
            "page": page,
            "per_page": per_page,
            "provider_id": self.settings.tecdoc_provider_id,
        }
        payload = _render_template(template, context)
        if not isinstance(payload, dict):
            raise ProviderNotConfigured("TECDOC_PARTS_REQUEST_TEMPLATE должен быть JSON-объектом.")
        warnings = []
        group_map = self.settings.product_group_map
        if category:
            group_ids = group_map.get(category)
            if group_ids:
                payload["productGroups"] = group_ids if isinstance(group_ids, list) else [group_ids]
            else:
                warnings.append("Для этой группы не настроены ID TecDoc product groups; показаны все найденные детали автомобиля.")

        headers = _auth_headers(
            self.settings.tecdoc_parts_api_key,
            self.settings.tecdoc_parts_auth_header,
            self.settings.tecdoc_parts_auth_prefix,
        )
        headers["Content-Type"] = "application/json"
        method = self.settings.tecdoc_parts_method.upper()
        async with httpx.AsyncClient(timeout=45) as client:
            try:
                if method == "GET":
                    response = await client.get(self.settings.tecdoc_parts_url, headers=headers, params=payload)
                else:
                    response = await client.request(method, self.settings.tecdoc_parts_url, headers=headers, json=payload)
            except httpx.HTTPError as exc:
                raise TecDocProviderError("Не удалось связаться с TecDoc Web Service.") from exc

        if response.status_code in (401, 403):
            raise TecDocProviderError("TecDoc Web Service отклонил доступ. Проверь ключ, Provider ID и лицензию.")
        if response.status_code == 429:
            raise TecDocProviderError("TecDoc Web Service ограничил частоту запросов. Попробуй позже.")
        if response.status_code >= 400:
            raise TecDocProviderError(f"TecDoc Web Service вернул HTTP {response.status_code}.")
        try:
            data = response.json()
        except ValueError as exc:
            raise TecDocProviderError("TecDoc Web Service вернул ответ не в JSON. Возможно, для лицензии нужен SOAP-адаптер.") from exc

        articles = _extract_articles(data)
        normalized = [_normalize_article(item) for item in articles if isinstance(item, dict)]
        return {
            "total": data.get("totalMatching", len(normalized)) if isinstance(data, dict) else len(normalized),
            "page": page,
            "per_page": per_page,
            "parts": normalized,
            "warnings": warnings,
            "source": "TecDoc Web Service",
        }
