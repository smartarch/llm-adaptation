from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Advanced multi-field protection strategy:
        - Consider all fields with threat_level > 0, sorted by threat descending.
        - For each field, allocate drones to 'protecting <Field_ID>' until drones_for_full_protection is met.
        - Drones already targeting a field (protecting or moving_to_field) are treated as allocated to that field.
        - Always assign the closest available drones to fill a field's protection need.
        - Drones not allocated to any field after processing are set to idle.
        - Groups follow the pattern: "protecting <Field_ID>" and "idle".
        """
        # 1) Identify threatened fields
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort fields by threat level (highest first)
        fields_sorted = sorted(fields_with_threat, key=lambda f: f.threat_level, reverse=True)

        allocated_set = set()          # drones assigned to some field
        allocated_to_field = {}          # drone -> field_id mapping

        # 3) Pre-allocate drones that are already targeting fields
        for field in fields_sorted:
            field_id = field.id
            current_alloc = [
                d for d in components
                if getattr(d, "target_id", None) == field_id
                and getattr(d, "state", "") in ("protecting", "moving_to_field")
            ]
            for d in current_alloc:
                allocated_set.add(d)
                allocated_to_field[d] = field_id
                environment.assign_group(d, f"protecting {field_id}")

        # 4) Process each field in threat order
        for field in fields_sorted:
            field_id = field.id
            needed = int(getattr(field, "drones_for_full_protection", 0))

            # Count how many drones are currently allocated to this field
            current_alloc = [
                d for d in components
                if allocated_to_field.get(d) == field_id
            ]
            current_count = len(current_alloc)

            # If already enough, continue (we've already re-assigned above)
            if current_count >= max(needed, 0):
                continue

            remaining_needed = max(0, needed - current_count)
            if remaining_needed <= 0:
                continue

            # 5) Find closest available drones to this field's center
            center_x = (getattr(field, "left") + getattr(field, "right")) / 2.0
            center_y = (getattr(field, "top") + getattr(field, "bottom")) / 2.0

            candidates = [d for d in components if d not in allocated_set]

            def dist2(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float("inf")
                return (loc.x - center_x) ** 2 + (loc.y - center_y) ** 2

            candidates.sort(key=dist2)

            # 6) Assign the closest drones to this field
            for i in range(min(remaining_needed, len(candidates))):
                d = candidates[i]
                environment.assign_group(d, f"protecting {field_id}")
                allocated_set.add(d)
                allocated_to_field[d] = field_id

        # 7) Any drones not allocated to any field -> idle
        for d in components:
            if d not in allocated_set:
                environment.assign_group(d, "idle")