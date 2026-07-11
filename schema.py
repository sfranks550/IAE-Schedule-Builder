"""
Equipment schedule column schemas by discipline.

Each discipline maps to a list of column definitions. Every column has:
  - key: internal field name (used in extracted JSON)
  - label: display header text on the schedule
  - required: whether this must be present for every row (blank allowed, but column always shown)

Mechanical (HVAC) is the pilot discipline. Plumbing / Electrical / Fire Protection
are stubbed below so the same app can be extended to them later without a rebuild.
"""

MECHANICAL_COLUMNS = [
    {"key": "tag", "label": "Tag", "required": True},
    {"key": "equipment_type", "label": "Equipment Type", "required": True},
    {"key": "manufacturer", "label": "Manufacturer", "required": True},
    {"key": "model_number", "label": "Model Number", "required": True},
    {"key": "location_served", "label": "Location / Area Served", "required": False},
    {"key": "voltage", "label": "Voltage (V)", "required": True},
    {"key": "phase", "label": "Phase", "required": True},
    {"key": "fla", "label": "FLA (A)", "required": True},
    {"key": "mca", "label": "MCA (A)", "required": True},
    {"key": "mop", "label": "MOP (A)", "required": True},
    {"key": "cfm", "label": "CFM", "required": False},
    {"key": "esp", "label": "ESP (in. w.g.)", "required": False},
    {"key": "cooling_capacity_mbh", "label": "Cooling Capacity (MBH)", "required": False},
    {"key": "heating_capacity_mbh", "label": "Heating Capacity (MBH)", "required": False},
    {"key": "eer_seer", "label": "EER / SEER", "required": False},
    {"key": "refrigerant", "label": "Refrigerant Type", "required": False},
    {"key": "weight_lbs", "label": "Weight (lbs)", "required": False},
    {"key": "sound_rating_dba", "label": "Sound Rating (dBA)", "required": False},
    {"key": "mounting", "label": "Mounting", "required": False},
    {"key": "notes", "label": "Notes", "required": False},
]

PLUMBING_COLUMNS = [
    {"key": "tag", "label": "Tag", "required": True},
    {"key": "equipment_type", "label": "Equipment Type", "required": True},
    {"key": "manufacturer", "label": "Manufacturer", "required": True},
    {"key": "model_number", "label": "Model Number", "required": True},
    {"key": "location_served", "label": "Location / Area Served", "required": False},
    {"key": "voltage", "label": "Voltage (V)", "required": False},
    {"key": "phase", "label": "Phase", "required": False},
    {"key": "hp", "label": "HP", "required": False},
    {"key": "fla", "label": "FLA (A)", "required": False},
    {"key": "gpm", "label": "GPM", "required": False},
    {"key": "head_ft", "label": "Head (ft)", "required": False},
    {"key": "pipe_size_in", "label": "Pipe Size (in)", "required": False},
    {"key": "capacity_gal", "label": "Capacity (gal)", "required": False},
    {"key": "weight_lbs", "label": "Weight (lbs)", "required": False},
    {"key": "notes", "label": "Notes", "required": False},
]

ELECTRICAL_COLUMNS = [
    {"key": "tag", "label": "Tag", "required": True},
    {"key": "equipment_type", "label": "Equipment Type", "required": True},
    {"key": "manufacturer", "label": "Manufacturer", "required": True},
    {"key": "model_number", "label": "Model Number", "required": True},
    {"key": "voltage", "label": "Voltage (V)", "required": True},
    {"key": "phase", "label": "Phase", "required": True},
    {"key": "fla", "label": "FLA (A)", "required": True},
    {"key": "breaker_size", "label": "Breaker Size (A)", "required": False},
    {"key": "panel_circuit", "label": "Panel / Circuit", "required": False},
    {"key": "kva", "label": "kVA", "required": False},
    {"key": "notes", "label": "Notes", "required": False},
]

FIRE_PROTECTION_COLUMNS = [
    {"key": "tag", "label": "Tag", "required": True},
    {"key": "equipment_type", "label": "Equipment Type", "required": True},
    {"key": "manufacturer", "label": "Manufacturer", "required": True},
    {"key": "model_number", "label": "Model Number", "required": True},
    {"key": "voltage", "label": "Voltage (V)", "required": False},
    {"key": "phase", "label": "Phase", "required": False},
    {"key": "fla", "label": "FLA (A)", "required": False},
    {"key": "flow_gpm", "label": "Flow (GPM)", "required": False},
    {"key": "pressure_psi", "label": "Pressure (PSI)", "required": False},
    {"key": "zone", "label": "Zone", "required": False},
    {"key": "notes", "label": "Notes", "required": False},
]

DISCIPLINES = {
    "Mechanical (HVAC)": MECHANICAL_COLUMNS,
    "Plumbing": PLUMBING_COLUMNS,
    "Electrical": ELECTRICAL_COLUMNS,
    "Fire Protection": FIRE_PROTECTION_COLUMNS,
}
