from fastapi import APIRouter, Request
from backend.middleware.rate_limit import limiter
from backend.models import FacilitySearchRequest, FacilityListResponse, WasteCategory
from backend.tools.sql_tool import find_nearby_facilities

router = APIRouter(tags=["facilities"])

WASTE_CATEGORIES = [
    WasteCategory(
        key="wet_waste",
        label="Wet Waste",
        bin_color="green",
        description="Biodegradable organic waste that can be composted.",
        examples=["Food scraps", "Vegetable peels", "Cooked food", "Garden trimmings", "Tea leaves"],
    ),
    WasteCategory(
        key="dry_waste",
        label="Dry Recyclable Waste",
        bin_color="blue",
        description="Clean, dry materials that can be recycled.",
        examples=["Newspapers", "Cardboard", "PET bottles", "Aluminium cans", "Glass bottles"],
    ),
    WasteCategory(
        key="hazardous",
        label="Hazardous Waste",
        bin_color="red",
        description="Waste requiring special handling due to toxicity or chemical risk.",
        examples=["Batteries", "Paint cans", "Pesticides", "Expired medicines", "Fluorescent bulbs"],
    ),
    WasteCategory(
        key="e_waste",
        label="E-Waste",
        bin_color="red",
        description="Electronic and electrical waste — must go to authorized e-waste recyclers.",
        examples=["Old phones", "Laptops", "Chargers", "Cables", "PCBs"],
    ),
    WasteCategory(
        key="sanitary",
        label="Sanitary Waste",
        bin_color="black",
        description="Hygiene and medical waste — must be wrapped before disposal.",
        examples=["Sanitary pads", "Diapers", "Bandages", "Masks", "Syringes (in sharps container)"],
    ),
    WasteCategory(
        key="construction",
        label="Construction & Demolition Waste",
        bin_color="grey",
        description="Debris from construction, renovation, or demolition activities.",
        examples=["Bricks", "Cement chunks", "Tiles", "Wood offcuts", "Metal rods"],
    ),
    WasteCategory(
        key="non_recyclable",
        label="Non-Recyclable Reject Waste",
        bin_color="grey",
        description="Items that cannot be recycled or composted — goes to landfill.",
        examples=["Soiled food wrappers", "Broken crockery", "Composite packaging", "Thermocol"],
    ),
]


@router.get("/categories", response_model=list[WasteCategory])
async def get_categories():
    """
    Get all supported waste categories with bin colors, descriptions, and examples.

    Use this to populate category filters in the UI.
    """
    return WASTE_CATEGORIES


@router.post("/facilities", response_model=FacilityListResponse)
@limiter.limit("30/minute")
async def search_facilities(request: Request, body: FacilitySearchRequest):
    """
    Search for nearby recycling/disposal facilities.

    - **city**: City name (e.g., "Mumbai", "Bengaluru")
    - **pincode**: 6-digit Indian pincode
    - **category**: Filter by waste category key (e.g., "e_waste", "hazardous")
    - **limit**: Max results (1–20, default 5)

    At least one of city or pincode is recommended.
    """
    results = find_nearby_facilities(
        location=body.city or body.pincode,
        category=body.category,
        limit=body.limit,
    )
    return FacilityListResponse(
        facilities=results,
        total=len(results),
        city=body.city,
        category=body.category,
    )
