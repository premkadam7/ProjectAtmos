from fastapi import HTTPException

SUPPORTED_CITIES = {"delhi"}


def supported_city(city: str) -> str:
    """Path dependency: reject cities we have no data for instead of serving Delhi's."""
    if city.lower() not in SUPPORTED_CITIES:
        raise HTTPException(
            status_code=404,
            detail=f"Unsupported city '{city}'. Supported: {', '.join(sorted(SUPPORTED_CITIES))}",
        )
    return city
