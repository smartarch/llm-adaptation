from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Top-field-first strategy with in-flight awareness:
        - Identify fields with threat_level > 0, and pick the field with the highest threat.
        - Treat drones already targeting or protecting that field (state in {"protecting","moving_to_field"}) as allocated.
        - If allocated >= drones_for_full_protection, assign those drones to "protecting <Field_ID>" and idle the rest.
        - Otherwise, use the closest idle drones to fill the remaining need and assign them to the top field.
        - All other drones become idle.
        """
        # 1) Identify threatened fields
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Pick the field with the highest threat
        top_field = max(fields_with_threat, key=lambda fld: fld.threat_level)
        top_group = f"protecting {top_field.id}"

        # 3) Field center for proximity calculations
        center_x = (top_field.left + top_field.right) / 2.0
        center_y = (top_field.top + top_field.bottom) / 2.0

        # 4) Drones already allocated to top field (protecting or moving toward)
        allocated = set()
        for d in components:
            if getattr(d, "target_id", None) == top_field.id and getattr(d, "state", "") in ("protecting", "moving_to_field"):
                allocated.add(d)

        # 5) How many drones are needed for full protection
        needed = int(getattr(top_field, "drones_for_full_protection", 0))

        # 6) If already enough, keep them; others idle
        if len(allocated) >= max(needed, 0):
            for d in components:
                if d in allocated:
                    environment.assign_group(d, top_group)
                else:
                    environment.assign_group(d, "idle")
            return

        # 7) Otherwise, find closest idle drones to fill the gap
        remaining = max(0, needed - len(allocated))

        candidates = [d for d in components if d not in allocated and getattr(d, "state", "") == "idle"]

        def dist2(drone):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            return (loc.x - center_x) ** 2 + (loc.y - center_y) ** 2

        candidates.sort(key=dist2)

        selected = set(allocated)
        for i in range(min(remaining, len(candidates))):
            selected.add(candidates[i])

        # 8) Assign groups: selected drones to top_group; others idle
        for d in components:
            if d in selected:
                environment.assign_group(d, top_group)
            else:
                environment.assign_group(d, "idle")