import re
from pydantic import BaseModel, Field, field_validator


class VinIdentifyRequest(BaseModel):
    vin: str = Field(min_length=17, max_length=17)
    country: str | None = None
    make: str | None = None
    model: str | None = None
    date_first_reg: str | None = None
    body: str | None = None
    doors: str | None = None
    fuel: str | None = None
    gearbox_type: str | None = None
    gearbox_code: str | None = None
    cc: str | None = None
    kw: str | None = None
    engine_code: str | None = None

    @field_validator("vin")
    @classmethod
    def validate_vin(cls, value: str) -> str:
        value = re.sub(r"\s+", "", value).upper()
        if not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", value):
            raise ValueError("VIN должен содержать 17 символов; буквы I, O и Q не используются.")
        return value

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str | None) -> str | None:
        return value.upper() if value else value


