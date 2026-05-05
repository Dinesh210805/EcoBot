"""
CPCB (Central Pollution Control Board) source list for Indian waste regulations.
Used by crawl_cpcb.py to fetch and save official government documents.
"""

CPCB_SOURCES: list[dict] = [
    {
        "name": "swm_rules_overview",
        "url": "https://cpcb.nic.in/municipal-solid-waste/",
        "type": "html",
        "description": "CPCB Municipal Solid Waste / Solid Waste Management overview",
    },
    {
        "name": "ewaste_rules_overview",
        "url": "https://cpcb.nic.in/e-waste/",
        "type": "html",
        "description": "CPCB E-Waste management guidelines",
    },
    {
        "name": "hazardous_waste_overview",
        "url": "https://cpcb.nic.in/hazardous-waste/",
        "type": "html",
        "description": "CPCB Hazardous Waste management guidelines",
    },
    {
        "name": "bmw_rules_overview",
        "url": "https://cpcb.nic.in/bio-medical-waste/",
        "type": "html",
        "description": "CPCB Bio-Medical Waste management guidelines",
    },
    {
        "name": "plastic_waste_overview",
        "url": "https://cpcb.nic.in/plastic-waste/",
        "type": "html",
        "description": "CPCB Plastic Waste management guidelines",
    },
    {
        "name": "swachh_bharat_guidelines",
        "url": "https://sbm.gov.in/sbmReport/home.aspx",
        "type": "html",
        "description": "Swachh Bharat Mission waste management guidelines",
    },
    {
        "name": "waste_segregation_at_source",
        "url": "https://nmcg.nic.in/NMCGWasteSegregation.aspx",
        "type": "html",
        "description": "National Mission for Clean Ganga - Waste Segregation at Source",
    },
    {
        "name": "moefcc_waste_rules",
        "url": "https://moef.gov.in/en/division/environment-laboratories-division/waste-management/",
        "type": "html",
        "description": "MoEFCC Waste Management Rules",
    },
]
