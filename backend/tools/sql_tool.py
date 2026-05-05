from backend.db.sqlite_db import get_bin_info, search_facilities


def lookup_bin(category: str) -> dict:
    """Return bin_color and bin_label for a category."""
    return get_bin_info(category)


def find_nearby_facilities(
    location: str | None,
    category: str | None = None,
    limit: int = 3,
) -> list[dict]:
    """
    Search facilities by location string (city name or pincode).
    Tries pincode first (all digits), then city name.
    """
    if not location:
        return []

    location = location.strip()
    city = None
    pincode = None

    if location.isdigit() and len(location) == 6:
        pincode = location
    else:
        city = location

    return search_facilities(city=city, pincode=pincode, category=category, limit=limit)
