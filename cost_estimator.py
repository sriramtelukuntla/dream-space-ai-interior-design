"""
Cost Estimator for Interior Design Projects
============================================
Calculates detailed cost breakdowns in Indian Rupees (₹).

KEY UPGRADE: All output is structured JSON-ready for dynamic UI rendering.
No manual file inspection required — every field maps directly to a
front-end UI element in the "Cost Estimator" tab.

FIX (v3.2):
  • _safe_list() helper converts any type (set, frozenset, tuple, None, str)
    to a plain list before slicing — prevents TypeError: unhashable type 'slice'
  • _determine_tier() now uses _safe_list() for mood, and correctly parses
    combined style strings like "minimalist and contemporary"
  • estimate_cost() normalises furniture / materials / lighting fields up front
  • lighting description line uses _safe_list() before [:2] slice
  • compare_tiers() returns an OrderedDict (basic→standard→premium→luxury)
    so the front-end always renders tier cards in the correct order
"""

from typing import Dict, List, Optional
from datetime import datetime
from collections import OrderedDict


# ── Module-level helper (used by both estimate_cost and helpers) ───────────────
def _safe_list(val) -> list:
    """Safely coerce any value to a plain list for safe iteration / slicing."""
    if not val:
        return []
    if isinstance(val, str):
        return [val]
    if isinstance(val, (list, tuple)):
        return list(val)
    if isinstance(val, (set, frozenset)):
        return sorted(val)   # sorted for deterministic output
    try:
        return list(val)
    except TypeError:
        return []


class CostEstimator:
    """
    Estimates interior design costs and returns fully structured data
    ready for direct front-end rendering.

    Usage
    -----
    estimator = CostEstimator()
    breakdown = estimator.estimate_cost(parsed_data)
    # → pass breakdown directly to jsonify() in Flask; JS renders it

    For tier comparison (returns ordered dict basic→standard→premium→luxury):
    comparisons = estimator.compare_tiers(parsed_data)
    """

    # ── Indian market 2024-2025 base rates (INR per sq ft) ────────────────────
    # Generic fallback rates
    CONSTRUCTION_RATE = {
        "basic":    1_200,
        "standard": 1_800,
        "premium":  2_500,
        "luxury":   3_500,
    }

    # Room-type specific construction rates (wet areas, specialised rooms cost more)
    ROOM_CONSTRUCTION_RATE = {
        "bathroom": {"basic": 2_000, "standard": 3_200, "premium": 5_000, "luxury": 8_000},
        "kitchen":  {"basic": 2_200, "standard": 3_500, "premium": 5_500, "luxury": 9_000},
        "office":   {"basic": 1_400, "standard": 2_200, "premium": 3_200, "luxury": 5_000},
        "bedroom":  {"basic": 1_000, "standard": 1_600, "premium": 2_200, "luxury": 3_200},
        "living room": {"basic": 1_100, "standard": 1_700, "premium": 2_400, "luxury": 3_500},
        "dining room": {"basic": 1_000, "standard": 1_600, "premium": 2_200, "luxury": 3_200},
        "kids room":   {"basic":   900, "standard": 1_400, "premium": 2_000, "luxury": 3_000},
        "gym":         {"basic": 1_200, "standard": 1_800, "premium": 2_800, "luxury": 4_500},
        "home theater":{"basic": 1_500, "standard": 2_500, "premium": 4_000, "luxury": 7_000},
        "hallway":     {"basic":   800, "standard": 1_200, "premium": 1_800, "luxury": 2_800},
        "balcony":     {"basic":   700, "standard": 1_100, "premium": 1_600, "luxury": 2_500},
    }

    # Default area (sq ft) when dimensions not specified — per room type
    ROOM_DEFAULT_AREA = {
        "bathroom":    70.0,
        "kitchen":    120.0,
        "bedroom":    180.0,
        "office":     200.0,
        "living room":250.0,
        "dining room":150.0,
        "kids room":  150.0,
        "gym":        300.0,
        "home theater":200.0,
        "hallway":     80.0,
        "balcony":     60.0,
    }

    # Room-type specific additional fixed costs
    ROOM_ADDITIONAL_FIXED = {
        "bathroom": {"electrical": 10_000, "plumbing": 40_000, "painting_per_sqft": 40,  "flooring_install_per_sqft": 80,  "waterproofing": 15_000},
        "kitchen":  {"electrical": 20_000, "plumbing": 35_000, "painting_per_sqft": 35,  "flooring_install_per_sqft": 70,  "waterproofing": 10_000},
        "office":   {"electrical": 25_000, "plumbing": 0,      "painting_per_sqft": 25,  "flooring_install_per_sqft": 50,  "waterproofing": 0,    "networking": 15_000},
        "bedroom":  {"electrical": 15_000, "plumbing": 0,      "painting_per_sqft": 30,  "flooring_install_per_sqft": 45,  "waterproofing": 0},
        "living room":{"electrical":18_000,"plumbing": 0,      "painting_per_sqft": 30,  "flooring_install_per_sqft": 50,  "waterproofing": 0},
    }

    # Canonical order — always used when iterating tiers
    TIER_ORDER = ["basic", "standard", "premium", "luxury"]

    # ── Furniture catalogue (INR per piece) ───────────────────────────────────
    FURNITURE = {
        # ── Bedroom
        "bed":            dict(basic=15_000, standard=35_000, premium=75_000,  luxury=150_000),
        "king bed":       dict(basic=25_000, standard=50_000, premium=100_000, luxury=200_000),
        "queen bed":      dict(basic=20_000, standard=40_000, premium=80_000,  luxury=160_000),
        "queen-size bed": dict(basic=20_000, standard=40_000, premium=80_000,  luxury=160_000),
        "nightstand":     dict(basic=3_000,  standard=7_000,  premium=15_000,  luxury=30_000),
        "bedside table":  dict(basic=3_000,  standard=7_000,  premium=15_000,  luxury=30_000),
        "wardrobe":       dict(basic=25_000, standard=50_000, premium=100_000, luxury=200_000),
        "closet":         dict(basic=20_000, standard=45_000, premium=90_000,  luxury=180_000),
        "dresser":        dict(basic=15_000, standard=30_000, premium=60_000,  luxury=120_000),
        "chest of drawers": dict(basic=12_000, standard=25_000, premium=50_000, luxury=100_000),
        "study table":    dict(basic=8_000,  standard=15_000, premium=30_000,  luxury=60_000),
        "study table with chair": dict(basic=12_000, standard=22_000, premium=45_000, luxury=90_000),
        "desk":           dict(basic=8_000,  standard=15_000, premium=30_000,  luxury=60_000),
        "bench":          dict(basic=5_000,  standard=10_000, premium=20_000,  luxury=40_000),
        "floor-length curtains": dict(basic=4_000, standard=10_000, premium=22_000, luxury=45_000),
        # ── Living room
        "sofa":           dict(basic=20_000, standard=40_000, premium=80_000,  luxury=150_000),
        "l-shaped sofa":  dict(basic=35_000, standard=70_000, premium=140_000, luxury=250_000),
        "couch":          dict(basic=20_000, standard=40_000, premium=80_000,  luxury=150_000),
        "sectional":      dict(basic=35_000, standard=70_000, premium=140_000, luxury=250_000),
        "loveseat":       dict(basic=15_000, standard=30_000, premium=60_000,  luxury=120_000),
        "coffee table":   dict(basic=5_000,  standard=12_000, premium=25_000,  luxury=50_000),
        "side table":     dict(basic=3_000,  standard=7_000,  premium=14_000,  luxury=28_000),
        "end table":      dict(basic=3_000,  standard=7_000,  premium=14_000,  luxury=28_000),
        "tv stand":       dict(basic=8_000,  standard=15_000, premium=30_000,  luxury=60_000),
        "tv unit":        dict(basic=10_000, standard=20_000, premium=40_000,  luxury=80_000),
        "tv unit with floating shelves": dict(basic=15_000, standard=28_000, premium=55_000, luxury=110_000),
        "entertainment center": dict(basic=18_000, standard=35_000, premium=70_000, luxury=140_000),
        "bookshelf":      dict(basic=10_000, standard=20_000, premium=40_000,  luxury=80_000),
        "bookcase":       dict(basic=12_000, standard=24_000, premium=48_000,  luxury=96_000),
        "ottoman":        dict(basic=5_000,  standard=12_000, premium=25_000,  luxury=50_000),
        "accent chair":   dict(basic=8_000,  standard=18_000, premium=36_000,  luxury=72_000),
        "armchair":       dict(basic=8_000,  standard=18_000, premium=36_000,  luxury=72_000),
        "console table":  dict(basic=6_000,  standard=13_000, premium=26_000,  luxury=52_000),
        "floor lamp":     dict(basic=2_000,  standard=5_000,  premium=10_000,  luxury=20_000),
        "indoor plant":   dict(basic=500,    standard=1_500,  premium=3_000,   luxury=6_000),
        "indoor plants":  dict(basic=1_000,  standard=3_000,  premium=6_000,   luxury=12_000),
        "rug":            dict(basic=3_000,  standard=8_000,  premium=15_000,  luxury=30_000),
        "fireplace":      dict(basic=30_000, standard=60_000, premium=120_000, luxury=240_000),
        # ── Kitchen
        "cabinets":       dict(basic=60_000, standard=100_000, premium=180_000, luxury=300_000),
        "built-in cabinetry": dict(basic=70_000, standard=120_000, premium=200_000, luxury=350_000),
        "countertops":    dict(basic=20_000, standard=40_000,  premium=80_000,  luxury=150_000),
        "kitchen island": dict(basic=25_000, standard=50_000,  premium=100_000, luxury=200_000),
        "island counter": dict(basic=25_000, standard=50_000,  premium=100_000, luxury=200_000),
        "stove":          dict(basic=8_000,  standard=15_000,  premium=30_000,  luxury=60_000),
        "gas hob":        dict(basic=8_000,  standard=15_000,  premium=30_000,  luxury=60_000),
        "chimney":        dict(basic=8_000,  standard=15_000,  premium=30_000,  luxury=60_000),
        "range":          dict(basic=10_000, standard=20_000,  premium=40_000,  luxury=80_000),
        "oven":           dict(basic=12_000, standard=25_000,  premium=50_000,  luxury=100_000),
        "refrigerator":   dict(basic=20_000, standard=35_000,  premium=70_000,  luxury=150_000),
        "fridge":         dict(basic=20_000, standard=35_000,  premium=70_000,  luxury=150_000),
        "sink":           dict(basic=3_000,  standard=7_000,   premium=15_000,  luxury=30_000),
        "dishwasher":     dict(basic=12_000, standard=25_000,  premium=50_000,  luxury=100_000),
        "dining table":   dict(basic=15_000, standard=30_000,  premium=60_000,  luxury=120_000),
        "bar stools":     dict(basic=3_000,  standard=7_000,   premium=14_000,  luxury=28_000),
        "open shelves":   dict(basic=4_000,  standard=9_000,   premium=18_000,  luxury=36_000),
        "pendant lights": dict(basic=3_000,  standard=7_000,   premium=15_000,  luxury=30_000),
        "range hood":     dict(basic=6_000,  standard=12_000,  premium=25_000,  luxury=50_000),
        # ── Bathroom
        "toilet":         dict(basic=5_000,  standard=10_000, premium=20_000,  luxury=40_000),
        "shower":         dict(basic=8_000,  standard=15_000, premium=30_000,  luxury=60_000),
        "walk-in shower": dict(basic=15_000, standard=30_000, premium=60_000,  luxury=120_000),
        "walk-in rainfall shower": dict(basic=20_000, standard=40_000, premium=80_000, luxury=150_000),
        "bathtub":        dict(basic=20_000, standard=40_000, premium=80_000,  luxury=150_000),
        "freestanding tub": dict(basic=30_000, standard=60_000, premium=120_000, luxury=200_000),
        "freestanding bathtub": dict(basic=30_000, standard=60_000, premium=120_000, luxury=200_000),
        "vanity":         dict(basic=10_000, standard=20_000, premium=40_000,  luxury=80_000),
        "double vanity":  dict(basic=20_000, standard=40_000, premium=80_000,  luxury=160_000),
        "double vanity with mirror cabinet": dict(basic=25_000, standard=50_000, premium=100_000, luxury=180_000),
        "mirror":         dict(basic=2_000,  standard=5_000,  premium=10_000,  luxury=20_000),
        "medicine cabinet": dict(basic=4_000, standard=8_000, premium=16_000,  luxury=32_000),
        "mirror cabinet": dict(basic=4_000,  standard=8_000,  premium=16_000,  luxury=32_000),
        "cabinet":        dict(basic=5_000,  standard=10_000, premium=20_000,  luxury=40_000),
        "towel rack":     dict(basic=1_000,  standard=2_500,  premium=5_000,   luxury=10_000),
        "heated towel rail": dict(basic=3_000, standard=7_000, premium=15_000, luxury=30_000),
        # ── Office / Lab / Classroom
        "office chair":   dict(basic=5_000,  standard=12_000, premium=25_000,  luxury=50_000),
        "ergonomic chair": dict(basic=8_000, standard=18_000, premium=35_000,  luxury=70_000),
        "standing desk":  dict(basic=12_000, standard=25_000, premium=50_000,  luxury=100_000),
        "filing cabinet": dict(basic=6_000,  standard=12_000, premium=25_000,  luxury=50_000),
        "whiteboard":     dict(basic=3_000,  standard=6_000,  premium=12_000,  luxury=24_000),
        "printer stand":  dict(basic=2_000,  standard=4_500,  premium=9_000,   luxury=18_000),
        "monitor arm":    dict(basic=2_000,  standard=5_000,  premium=10_000,  luxury=20_000),
        "stainless steel workbench": dict(basic=8_000, standard=18_000, premium=36_000, luxury=72_000),
        "lab stool":      dict(basic=2_000,  standard=4_500,  premium=9_000,   luxury=18_000),
        "student desk":   dict(basic=3_000,  standard=6_000,  premium=12_000,  luxury=24_000),
        "teacher's desk": dict(basic=8_000,  standard=15_000, premium=30_000,  luxury=60_000),
        "projector screen": dict(basic=5_000, standard=12_000, premium=25_000, luxury=50_000),
        "podium":         dict(basic=4_000,  standard=8_000,  premium=16_000,  luxury=32_000),
        "acoustic panel": dict(basic=3_000,  standard=7_000,  premium=14_000,  luxury=28_000),
        "acoustic panels": dict(basic=10_000, standard=22_000, premium=45_000, luxury=90_000),
        "chandelier":     dict(basic=8_000,  standard=20_000, premium=50_000,  luxury=120_000),
        # ── Shared
        "chair":          dict(basic=2_000,  standard=5_000,  premium=10_000,  luxury=20_000),
        "lamp":           dict(basic=1_500,  standard=3_500,  premium=7_500,   luxury=15_000),
        "table lamp":     dict(basic=1_500,  standard=3_500,  premium=7_500,   luxury=15_000),
        "curtains":       dict(basic=4_000,  standard=10_000, premium=22_000,  luxury=45_000),
        "drapes":         dict(basic=4_000,  standard=10_000, premium=22_000,  luxury=45_000),
        "carpet":         dict(basic=8_000,  standard=18_000, premium=36_000,  luxury=72_000),
        "bench with storage": dict(basic=6_000, standard=13_000, premium=26_000, luxury=52_000),
        "coat hooks":     dict(basic=1_000,  standard=2_500,  premium=5_000,   luxury=10_000),
        "umbrella stand": dict(basic=1_500,  standard=3_500,  premium=7_000,   luxury=14_000),
    }

    # ── Material costs (INR per sq ft of coverage) ────────────────────────────
    MATERIALS = {
        "wood":     dict(basic=200,  standard=400,  premium=800,   luxury=1_500),
        "wooden":   dict(basic=200,  standard=400,  premium=800,   luxury=1_500),
        "oak":      dict(basic=400,  standard=700,  premium=1_200, luxury=2_000),
        "walnut":   dict(basic=500,  standard=900,  premium=1_500, luxury=2_500),
        "pine":     dict(basic=180,  standard=360,  premium=700,   luxury=1_400),
        "mahogany": dict(basic=600,  standard=1_000, premium=1_800, luxury=3_000),
        "bamboo":   dict(basic=150,  standard=300,  premium=600,   luxury=1_200),
        "metal":    dict(basic=150,  standard=300,  premium=600,   luxury=1_200),
        "steel":    dict(basic=200,  standard=400,  premium=800,   luxury=1_600),
        "stainless steel": dict(basic=250, standard=500, premium=1_000, luxury=2_000),
        "brass":    dict(basic=400,  standard=800,  premium=1_500, luxury=3_000),
        "copper":   dict(basic=350,  standard=700,  premium=1_400, luxury=2_800),
        "glass":    dict(basic=200,  standard=400,  premium=800,   luxury=1_500),
        "marble":   dict(basic=400,  standard=800,  premium=1_500, luxury=3_000),
        "granite":  dict(basic=300,  standard=600,  premium=1_000, luxury=2_000),
        "stone":    dict(basic=350,  standard=650,  premium=1_200, luxury=2_400),
        "concrete": dict(basic=100,  standard=200,  premium=400,   luxury=800),
        "leather":  dict(basic=300,  standard=600,  premium=1_200, luxury=2_500),
        "fabric":   dict(basic=100,  standard=250,  premium=500,   luxury=1_000),
        "velvet":   dict(basic=200,  standard=450,  premium=900,   luxury=1_800),
        "linen":    dict(basic=120,  standard=280,  premium=560,   luxury=1_120),
        "tile":     dict(basic=50,   standard=100,  premium=200,   luxury=400),
        "ceramic":  dict(basic=60,   standard=120,  premium=250,   luxury=500),
        "porcelain": dict(basic=80,  standard=160,  premium=320,   luxury=640),
        "laminate": dict(basic=80,   standard=150,  premium=300,   luxury=600),
        "vinyl":    dict(basic=80,   standard=150,  premium=300,   luxury=600),
        "hardwood": dict(basic=300,  standard=600,  premium=1_000, luxury=2_000),
        "subway tile": dict(basic=60, standard=120, premium=250,   luxury=500),
        "anti-static tile": dict(basic=80, standard=160, premium=320, luxury=640),
        "chequerboard marble": dict(basic=500, standard=900, premium=1_600, luxury=3_000),
        "wainscoting": dict(basic=200, standard=400, premium=800,  luxury=1_500),
    }

    # ── Lighting packages (INR total for the room) ────────────────────────────
    LIGHTING = {
        "basic":    5_000,
        "standard": 12_000,
        "premium":  25_000,
        "luxury":   50_000,
    }

    # ── Labour as fraction of (furniture + material) cost ─────────────────────
    LABOUR_RATE = dict(basic=0.30, standard=0.40, premium=0.50, luxury=0.60)

    # ── Fixed additional costs ─────────────────────────────────────────────────
    ADDITIONAL = dict(
        electrical=15_000,
        plumbing=20_000,
        painting_per_sqft=30,
        flooring_install_per_sqft=50,
    )

    DESIGNER_FEE_RATE = 0.10
    GST_RATE          = 0.18

    # ── Quality tier classifier ────────────────────────────────────────────────
    LUXURY_STYLES   = {"luxury", "elegant", "opulent", "glamorous", "victorian", "art deco"}
    PREMIUM_STYLES  = {"contemporary", "mid-century", "mid-century modern", "transitional",
                       "french country", "mediterranean"}
    STANDARD_STYLES = {"modern", "scandinavian", "nordic", "minimalist", "minimal",
                       "coastal", "nautical", "bohemian", "boho", "japandi"}
    LUXURY_MOODS    = {"luxurious", "elegant", "sophisticated", "opulent"}

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def estimate_cost(
        self,
        parsed_data: Dict,
        image_analysis: Optional[Dict] = None,
    ) -> Dict:
        """
        Returns a fully structured cost breakdown dict suitable for
        direct JSON serialisation and dynamic front-end rendering.
        """
        try:
            furniture = _safe_list(parsed_data.get("furniture"))
            materials = _safe_list(parsed_data.get("materials"))
            lighting  = _safe_list(parsed_data.get("lighting"))
            room_type = parsed_data.get("room_type") or "room"

            tier = self._determine_tier(parsed_data)
            area = self._room_area(parsed_data.get("dimensions") or {}, room_type)

            base_cost       = self._base_cost(area, tier, room_type)
            furniture_items = self._furniture_items(furniture, tier, room_type)
            furniture_cost  = sum(i["amount"] for i in furniture_items)

            material_items  = self._material_items(materials, area, tier)
            material_cost   = sum(i["amount"] for i in material_items)

            lighting_cost   = self._lighting_cost(tier)
            labour_cost     = (furniture_cost + material_cost) * self.LABOUR_RATE[tier]
            additional_cost = self._additional_costs(room_type, area)

            subtotal     = (base_cost + furniture_cost + material_cost +
                            lighting_cost + labour_cost + additional_cost)
            designer_fee = subtotal * self.DESIGNER_FEE_RATE
            gst          = subtotal * self.GST_RATE
            total        = subtotal + designer_fee + gst

            style_val = parsed_data.get("style") or "modern"
            if not isinstance(style_val, str):
                style_val = _safe_list(style_val)[0] if _safe_list(style_val) else "modern"

            lighting_desc = (
                f"{tier.capitalize()} lighting package"
                + (f" — {', '.join(lighting[:2])}" if lighting else "")
            )

            return {
                "room_details": {
                    "room_type":            room_type,
                    "area_sqft":            round(area, 1),
                    "quality_tier":         tier.upper(),
                    "style":                style_val,
                    "furniture_count":      len(furniture),
                    "material_count":       len(materials),
                    "has_lighting":         bool(lighting),
                    "dimensions_specified": bool(parsed_data.get("dimensions")),
                },
                "cost_breakdown": {
                    "base_construction": {
                        "label":       "Base Construction",
                        "icon":        "🏗️",
                        "amount":      round(base_cost),
                        "description": (
                            f"Interior finishing @ ₹{self.CONSTRUCTION_RATE[tier]:,}/sq ft "
                            f"× {area:.0f} sq ft ({tier.capitalize()} tier)"
                        ),
                        "items": [],
                    },
                    "furniture": {
                        "label":       "Furniture",
                        "icon":        "🛋️",
                        "amount":      round(furniture_cost),
                        "description": (
                            f"{len(furniture_items)} item(s) — {tier.capitalize()} quality"
                            if furniture_items else "No specific furniture listed"
                        ),
                        "items": [
                            {
                                "name":      i["name"],
                                "quantity":  i["quantity"],
                                "unit_cost": round(i["unit_cost"]),
                                "amount":    round(i["amount"]),
                            }
                            for i in furniture_items
                        ],
                    },
                    "materials": {
                        "label":       "Materials & Finishes",
                        "icon":        "🪵",
                        "amount":      round(material_cost),
                        "description": (
                            f"{len(material_items)} material(s) selected"
                            if material_items else "Standard finishes applied"
                        ),
                        "items": [
                            {
                                "name":          i["name"],
                                "coverage_sqft": round(i["coverage_sqft"], 1),
                                "rate_per_sqft": round(i["rate"]),
                                "amount":        round(i["amount"]),
                            }
                            for i in material_items
                        ],
                    },
                    "lighting": {
                        "label":       "Lighting",
                        "icon":        "💡",
                        "amount":      round(lighting_cost),
                        "description": lighting_desc,
                        "items":       [],
                    },
                    "labour": {
                        "label":       "Labour & Installation",
                        "icon":        "👷",
                        "amount":      round(labour_cost),
                        "description": (
                            f"{int(self.LABOUR_RATE[tier]*100)}% of furniture + "
                            f"materials cost (skilled labour)"
                        ),
                        "items": [],
                    },
                    "additional": {
                        "label":       "Additional Works",
                        "icon":        "🔧",
                        "amount":      round(additional_cost),
                        "description": self._additional_desc(room_type, area),
                        "items":       self._additional_items(room_type, area),
                    },
                },
                "subtotal":       round(subtotal),
                "designer_fee":   round(designer_fee),
                "gst_18_percent": round(gst),
                "total_cost":     round(total),
                "cost_range": {
                    "minimum": round(total * 0.85),
                    "maximum": round(total * 1.15),
                },
                "tier_multipliers": {
                    "basic":    self.CONSTRUCTION_RATE["basic"],
                    "standard": self.CONSTRUCTION_RATE["standard"],
                    "premium":  self.CONSTRUCTION_RATE["premium"],
                    "luxury":   self.CONSTRUCTION_RATE["luxury"],
                },
                "notes":       self._notes(parsed_data, tier),
                "ui_metadata": {
                    "currency":        "INR",
                    "currency_symbol": "₹",
                    "locale":          "en-IN",
                    "generated_at":    datetime.now().isoformat(timespec="seconds"),
                },
            }

        except Exception as e:
            print(f"❌ CostEstimator.estimate_cost error: {e}")
            import traceback; traceback.print_exc()
            return self._default_estimate()

    def compare_tiers(self, parsed_data: Dict) -> OrderedDict:
        """
        Returns cost breakdowns for all four tiers in a guaranteed
        ordered dict: basic → standard → premium → luxury.

        The Flask /api/cost-comparison endpoint should return:
            {"comparisons": estimator.compare_tiers(parsed_data)}
        This ensures the JS front-end always renders tier cards in
        the correct ascending-cost order.
        """
        result = OrderedDict()
        original_style = parsed_data.get("style")
        for tier in self.TIER_ORDER:
            # Temporarily override style to force the correct tier
            patched = dict(parsed_data)
            patched["_force_tier"] = tier
            result[tier] = self._estimate_for_tier(parsed_data, tier)
        return result

    def _estimate_for_tier(self, parsed_data: Dict, tier: str) -> Dict:
        """Compute cost breakdown for a specific tier, ignoring style-based detection."""
        try:
            furniture = _safe_list(parsed_data.get("furniture"))
            materials = _safe_list(parsed_data.get("materials"))
            lighting  = _safe_list(parsed_data.get("lighting"))
            room_type = parsed_data.get("room_type") or "room"
            area      = self._room_area(parsed_data.get("dimensions") or {}, room_type)

            base_cost       = self._base_cost(area, tier, room_type)
            furniture_items = self._furniture_items(furniture, tier, room_type)
            furniture_cost  = sum(i["amount"] for i in furniture_items)
            material_items  = self._material_items(materials, area, tier)
            material_cost   = sum(i["amount"] for i in material_items)
            lighting_cost   = self._lighting_cost(tier)
            labour_cost     = (furniture_cost + material_cost) * self.LABOUR_RATE[tier]
            additional_cost = self._additional_costs(room_type, area)

            subtotal     = (base_cost + furniture_cost + material_cost +
                            lighting_cost + labour_cost + additional_cost)
            designer_fee = subtotal * self.DESIGNER_FEE_RATE
            gst          = subtotal * self.GST_RATE
            total        = subtotal + designer_fee + gst

            style_val = parsed_data.get("style") or "modern"
            if not isinstance(style_val, str):
                style_val = _safe_list(style_val)[0] if _safe_list(style_val) else "modern"

            return {
                "room_details": {
                    "room_type":            room_type,
                    "area_sqft":            round(area, 1),
                    "quality_tier":         tier.upper(),
                    "style":                style_val,
                    "furniture_count":      len(furniture),
                    "material_count":       len(materials),
                    "has_lighting":         bool(lighting),
                    "dimensions_specified": bool(parsed_data.get("dimensions")),
                },
                "cost_breakdown": {
                    "base_construction": {
                        "label": "Base Construction", "icon": "🏗️",
                        "amount": round(base_cost),
                        "description": f"@ ₹{self.CONSTRUCTION_RATE[tier]:,}/sq ft × {area:.0f} sq ft",
                        "items": [],
                    },
                    "furniture": {
                        "label": "Furniture", "icon": "🛋️",
                        "amount": round(furniture_cost),
                        "description": f"{len(furniture_items)} item(s) — {tier.capitalize()} quality",
                        "items": [{"name": i["name"], "quantity": 1, "unit_cost": round(i["unit_cost"]), "amount": round(i["amount"])} for i in furniture_items],
                    },
                    "materials": {
                        "label": "Materials & Finishes", "icon": "🪵",
                        "amount": round(material_cost),
                        "description": f"{len(material_items)} material(s)",
                        "items": [{"name": i["name"], "coverage_sqft": round(i["coverage_sqft"], 1), "rate_per_sqft": round(i["rate"]), "amount": round(i["amount"])} for i in material_items],
                    },
                    "lighting": {"label": "Lighting", "icon": "💡", "amount": round(lighting_cost), "description": f"{tier.capitalize()} lighting package", "items": []},
                    "labour":   {"label": "Labour & Installation", "icon": "👷", "amount": round(labour_cost), "description": f"{int(self.LABOUR_RATE[tier]*100)}% of materials + furniture", "items": []},
                    "additional": {"label": "Additional Works", "icon": "🔧", "amount": round(additional_cost), "description": self._additional_desc(room_type, area), "items": self._additional_items(room_type, area)},
                },
                "subtotal":       round(subtotal),
                "designer_fee":   round(designer_fee),
                "gst_18_percent": round(gst),
                "total_cost":     round(total),
                "cost_range":     {"minimum": round(total * 0.85), "maximum": round(total * 1.15)},
                "notes":          self._notes(parsed_data, tier),
                "ui_metadata":    {"currency": "INR", "currency_symbol": "₹", "locale": "en-IN", "generated_at": datetime.now().isoformat(timespec="seconds")},
            }
        except Exception as e:
            print(f"❌ _estimate_for_tier({tier}) error: {e}")
            return self._default_estimate()

    def format_cost_report(self, breakdown: Dict) -> str:
        """Human-readable text report (used for download / print)."""
        rd  = breakdown.get("room_details", {})
        cb  = breakdown.get("cost_breakdown", {})
        sep = "═" * 60

        lines = [
            sep,
            "    💰  INTERIOR DESIGN COST ESTIMATE REPORT",
            sep,
            "",
            f"  Room Type    : {rd.get('room_type', '—').upper()}",
            f"  Area         : {rd.get('area_sqft', 0):.0f} sq ft",
            f"  Quality Tier : {rd.get('quality_tier', '—')}",
            f"  Style        : {str(rd.get('style', '—')).capitalize()}",
            "",
            "─" * 60,
            "  COST BREAKDOWN",
            "─" * 60,
        ]

        for key in ["base_construction", "furniture", "materials",
                    "lighting", "labour", "additional"]:
            item   = cb.get(key, {})
            label  = item.get("label", key)
            amount = item.get("amount", 0)
            lines.append(f"  {label:<28} ₹{amount:>12,.0f}")
            for sub in item.get("items", []):
                if "name" in sub:
                    lines.append(f"     ↳ {sub['name']:<24} ₹{sub.get('amount', 0):>10,.0f}")

        lines += [
            "─" * 60,
            f"  {'Subtotal':<28} ₹{breakdown.get('subtotal', 0):>12,.0f}",
            f"  {'Designer Fee (10%)':<28} ₹{breakdown.get('designer_fee', 0):>12,.0f}",
            f"  {'GST (18%)':<28} ₹{breakdown.get('gst_18_percent', 0):>12,.0f}",
            sep,
            f"  {'TOTAL ESTIMATED COST':<28} ₹{breakdown.get('total_cost', 0):>12,.0f}",
            sep,
            "",
            f"  Range: ₹{breakdown['cost_range']['minimum']:,.0f}"
            f"  –  ₹{breakdown['cost_range']['maximum']:,.0f}",
            "",
            "  NOTES:",
        ]
        for note in breakdown.get("notes", []):
            lines.append(f"    • {note}")
        lines += [
            "",
            f"  Generated: {breakdown.get('ui_metadata', {}).get('generated_at', '—')}",
            sep,
        ]
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _determine_tier(self, parsed_data: Dict) -> str:
        """
        Detect quality tier — handles:
        - Combined style strings like "minimalist and contemporary"
        - set / list / None style values
        - mood sets from PromptAnalyzer
        """
        style_raw = parsed_data.get("style", "modern")

        # Normalise style to a lowercase string
        if isinstance(style_raw, str):
            style = style_raw.lower()
        else:
            parts = _safe_list(style_raw)
            style = " ".join(str(p).lower() for p in parts) if parts else "modern"

        # mood may be a set from PromptAnalyzer — convert safely
        mood = set(_safe_list(parsed_data.get("mood")))

        # Check each keyword within the (possibly combined) style string
        if any(s in style for s in self.LUXURY_STYLES) or mood & self.LUXURY_MOODS:
            return "luxury"
        if any(s in style for s in self.PREMIUM_STYLES):
            return "premium"
        if any(s in style for s in self.STANDARD_STYLES):
            return "standard"
        return "basic"

    def _room_area(self, dims: Dict, room_type: str = "") -> float:
        w = dims.get("width")
        l = dims.get("length")
        if w and l:
            unit = dims.get("unit", "feet")
            if unit in ("meters", "m", "metre", "metres"):
                w *= 3.28084
                l *= 3.28084
            return float(w) * float(l)
        # Use room-type specific default area
        rt = str(room_type).lower().strip() if room_type else ""
        for key, default_area in self.ROOM_DEFAULT_AREA.items():
            if key in rt:
                return default_area
        return 150.0

    def _base_cost(self, area: float, tier: str, room_type: str = "") -> float:
        rt = str(room_type).lower().strip() if room_type else ""
        rate_dict = self.CONSTRUCTION_RATE  # fallback
        for key, rates in self.ROOM_CONSTRUCTION_RATE.items():
            if key in rt:
                rate_dict = rates
                break
        return area * rate_dict[tier]

    # Default furniture assumed per room type when user lists none
    ROOM_DEFAULT_FURNITURE = {
        "bathroom":    ["toilet", "vanity", "mirror", "shower"],
        "kitchen":     ["cabinets", "countertops", "sink", "stove"],
        "office":      ["desk", "office chair", "filing cabinet", "bookshelf"],
        "bedroom":     ["bed", "wardrobe", "nightstand", "dresser"],
        "living room": ["sofa", "coffee table", "tv unit", "bookshelf"],
        "dining room": ["dining table", "chair"],
        "kids room":   ["bed", "study table", "wardrobe"],
        "gym":         ["bench"],
    }

    def _furniture_items(self, furniture: List[str], tier: str, room_type: str = "") -> List[Dict]:
        # If no furniture listed, apply room-type defaults so estimate is non-zero
        if not furniture and room_type:
            rt = str(room_type).lower()
            for key, defaults in self.ROOM_DEFAULT_FURNITURE.items():
                if key in rt:
                    furniture = defaults
                    break
        items = []
        for name in furniture:
            key   = str(name).lower().strip()
            # Try exact match first, then partial match
            price = self.FURNITURE.get(key)
            if price is None:
                # Try partial key match for compound names
                for fk, fv in self.FURNITURE.items():
                    if fk in key or key in fk:
                        price = fv
                        break
            if price is None:
                price = {"basic": 5_000, "standard": 10_000, "premium": 20_000, "luxury": 40_000}
            tier_price = price.get(tier, 5_000) if isinstance(price, dict) else 5_000
            items.append(dict(name=name, quantity=1, unit_cost=tier_price, amount=tier_price))
        return items

    def _material_items(self, materials: List[str], area: float, tier: str) -> List[Dict]:
        if not materials:
            return []
        items = []
        coverage_frac = 0.30
        for mat in materials:
            key  = str(mat).lower().strip()
            rate_dict = self.MATERIALS.get(key)
            if rate_dict is None:
                for mk, mv in self.MATERIALS.items():
                    if mk in key or key in mk:
                        rate_dict = mv
                        break
            if rate_dict is None:
                rate_dict = {"basic": 100, "standard": 200, "premium": 400, "luxury": 800}
            rate = rate_dict.get(tier, 200) if isinstance(rate_dict, dict) else 200
            cov  = area * coverage_frac
            items.append(dict(name=mat, coverage_sqft=cov, rate=rate, amount=cov * rate))
        return items

    def _lighting_cost(self, tier: str) -> float:
        return float(self.LIGHTING[tier])

    def _get_room_additional(self, room_type: str) -> Dict:
        """Return the correct additional-cost config for the room type."""
        rt = str(room_type).lower()
        for key, cfg in self.ROOM_ADDITIONAL_FIXED.items():
            if key in rt:
                return cfg
        return self.ADDITIONAL  # generic fallback

    def _additional_costs(self, room_type: str, area: float) -> float:
        cfg = self._get_room_additional(room_type)
        total = (
            cfg.get("electrical", self.ADDITIONAL["electrical"])
            + area * cfg.get("painting_per_sqft", self.ADDITIONAL["painting_per_sqft"])
            + area * cfg.get("flooring_install_per_sqft", self.ADDITIONAL["flooring_install_per_sqft"])
            + cfg.get("plumbing", 0)
            + cfg.get("waterproofing", 0)
            + cfg.get("networking", 0)
        )
        return total

    def _additional_desc(self, room_type: str, area: float) -> str:
        cfg = self._get_room_additional(room_type)
        parts = [
            f"Electrical (₹{cfg.get('electrical', self.ADDITIONAL['electrical']):,})",
            f"Painting (₹{cfg.get('painting_per_sqft', 30)}/sq ft)",
            f"Flooring install (₹{cfg.get('flooring_install_per_sqft', 50)}/sq ft)",
        ]
        if cfg.get("plumbing", 0):
            parts.append(f"Plumbing (₹{cfg['plumbing']:,})")
        if cfg.get("waterproofing", 0):
            parts.append(f"Waterproofing (₹{cfg['waterproofing']:,})")
        if cfg.get("networking", 0):
            parts.append(f"Networking/Data points (₹{cfg['networking']:,})")
        return "  •  ".join(parts)

    def _additional_items(self, room_type: str, area: float) -> List[Dict]:
        cfg = self._get_room_additional(room_type)
        items = [
            dict(name="Electrical work",  amount=cfg.get("electrical", self.ADDITIONAL["electrical"])),
            dict(name="Painting",          amount=area * cfg.get("painting_per_sqft", 30)),
            dict(name="Flooring install",  amount=area * cfg.get("flooring_install_per_sqft", 50)),
        ]
        if cfg.get("plumbing", 0):
            items.append(dict(name="Plumbing", amount=cfg["plumbing"]))
        if cfg.get("waterproofing", 0):
            items.append(dict(name="Waterproofing", amount=cfg["waterproofing"]))
        if cfg.get("networking", 0):
            items.append(dict(name="Networking / Data points", amount=cfg["networking"]))
        return [dict(name=i["name"], amount=round(i["amount"])) for i in items]

    def _notes(self, parsed_data: Dict, tier: str) -> List[str]:
        notes = [
            "Estimates based on Indian market rates (2024–2025).",
            "Actual costs may vary ±15% by city, vendor & season.",
            "Includes materials, skilled labour & basic contractor fees.",
            "Prices exclude premium imports unless explicitly specified.",
        ]
        if tier == "luxury":
            notes.append("Luxury tier: high-end imported materials & bespoke finishes included.")
        elif tier == "premium":
            notes.append("Premium tier: branded Indian & select imported materials.")
        room_type = str(parsed_data.get("room_type", ""))
        if "bathroom" in room_type or "kitchen" in room_type:
            notes.append("Plumbing allowance included for wet-area rooms.")
        if not parsed_data.get("dimensions"):
            rt2 = str(parsed_data.get("room_type", "")).lower()
            default_a = 150.0
            for k, v in self.ROOM_DEFAULT_AREA.items():
                if k in rt2:
                    default_a = v
                    break
            notes.append(f"⚠️ Dimensions not specified — area defaulted to {default_a:.0f} sq ft.")
        return notes

    def _default_estimate(self) -> Dict:
        return {
            "room_details": {
                "room_type":            "room",
                "area_sqft":            150.0,
                "quality_tier":         "STANDARD",
                "style":                "modern",
                "furniture_count":      0,
                "material_count":       0,
                "has_lighting":         False,
                "dimensions_specified": False,
            },
            "cost_breakdown": {
                "base_construction": {
                    "label": "Base Construction", "icon": "🏗️",
                    "amount": 270_000,
                    "description": "Standard finish @ ₹1,800/sq ft × 150 sq ft",
                    "items": [],
                },
                "furniture": {
                    "label": "Furniture", "icon": "🛋️",
                    "amount": 100_000,
                    "description": "Estimated furniture package",
                    "items": [],
                },
                "materials": {
                    "label": "Materials & Finishes", "icon": "🪵",
                    "amount": 50_000,
                    "description": "Standard finishes",
                    "items": [],
                },
                "lighting": {
                    "label": "Lighting", "icon": "💡",
                    "amount": 12_000,
                    "description": "Standard lighting package",
                    "items": [],
                },
                "labour": {
                    "label": "Labour & Installation", "icon": "👷",
                    "amount": 60_000,
                    "description": "40% of materials + furniture",
                    "items": [],
                },
                "additional": {
                    "label": "Additional Works", "icon": "🔧",
                    "amount": 30_000,
                    "description": "Electrical, painting, flooring installation",
                    "items": [],
                },
            },
            "subtotal":       522_000,
            "designer_fee":    52_200,
            "gst_18_percent":  93_960,
            "total_cost":     668_160,
            "cost_range":     {"minimum": 567_936, "maximum": 768_384},
            "tier_multipliers": {
                "basic": 1_200, "standard": 1_800,
                "premium": 2_500, "luxury": 3_500,
            },
            "notes":          ["Default estimate — please provide more details."],
            "ui_metadata": {
                "currency":        "INR",
                "currency_symbol": "₹",
                "locale":          "en-IN",
                "generated_at":    datetime.now().isoformat(timespec="seconds"),
            },
        }