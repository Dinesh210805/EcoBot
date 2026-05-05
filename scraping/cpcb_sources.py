"""
CPCB (Central Pollution Control Board) source list for Indian waste regulations.
Used by crawl_cpcb.py to fetch and save official government documents.
"""

CPCB_SOURCES: list[dict] = [
    {
        "name": "swm_rules_2016",
        "url": "https://cpcb.nic.in/uploads/Projects/Bio-Medical-Waste/SWM-2016.pdf",
        "type": "pdf",
        "description": "Solid Waste Management Rules 2016",
    },
    {
        "name": "ewaste_rules_2022",
        "url": "https://cpcb.nic.in/uploads/hwmd/E-Waste_Management_Rules_2022.pdf",
        "type": "pdf",
        "description": "E-Waste (Management) Rules 2022",
    },
    {
        "name": "hazardous_waste_rules_2016",
        "url": "https://cpcb.nic.in/uploads/hwmd/Hazardous-Waste-Management-Rules-2016.pdf",
        "type": "pdf",
        "description": "Hazardous and Other Wastes (Management and Transboundary Movement) Rules 2016",
    },
    {
        "name": "bmw_rules_2016",
        "url": "https://cpcb.nic.in/uploads/Projects/Bio-Medical-Waste/BMW-Rules-2016.pdf",
        "type": "pdf",
        "description": "Bio-Medical Waste Management Rules 2016",
    },
    {
        "name": "plastic_waste_rules_2022",
        "url": "https://cpcb.nic.in/uploads/plastic-waste/PWM-Amended-Rules-2022.pdf",
        "type": "pdf",
        "description": "Plastic Waste Management (Amendment) Rules 2022",
    },
    {
        "name": "cpcb_waste_segregation_guide",
        "url": "https://cpcb.nic.in/openpdffile.php?id=TGFzdE5ld3MvMjAxX18xNTIxNjM3NTc1LnBkZg==",
        "type": "pdf",
        "description": "CPCB Waste Segregation at Source Guidelines",
    },
    {
        "name": "swachh_bharat_guidelines",
        "url": "https://sbm.gov.in/sbmReport/home.aspx",
        "type": "html",
        "description": "Swachh Bharat Mission waste management guidelines",
    },
    {
        "name": "cpcb_wet_dry_guide",
        "url": "https://cpcb.nic.in/displaypdf.php?id=aG93LXRvLXNlZ3JlZ2F0ZS13YXN0ZS5wZGY=",
        "type": "pdf",
        "description": "CPCB How to Segregate Wet and Dry Waste",
    },
]
