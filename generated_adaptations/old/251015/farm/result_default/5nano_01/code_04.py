from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat
        all_fields = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not all_fields:
            # No threat; idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat level descending
        fields_sorted = sorted(
            all_fields,
            key=lambda f: float(getattr(f, "threat_level", 0.0)),
            reverse=True
        )

        # Helpers
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        def distance_to_field(drone, field):
            cx, cy = field_center(field)
            loc = drone.location
            dx = loc.x - cx
            dy = loc.y - cy
            return (dx * dx + dy * dy) ** 0.5

        # Map of field_id to field object for quick lookup
        field_by_id = {f.id: f for f in fields_sorted}

        # Initial current protectors per field (from the observable state)
        initial_protectors = {f.id: [] for f in fields_sorted}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in field_by_id:
                    initial_protectors[tid].append(c)

        # Prepare final assignment plan
        final_group_for = {id(c): None for c in components}
        allocated = set()  # IDs of drones already assigned in this plan

        # Step 1: Top field protection (highest threat)
        top_field = fields_sorted[0]
        required_top = max(0, int(getattr(top_field, "drones_for_full_protection", 0)))
        current_top = len(initial_protectors.get(top_field.id, []))

        # Keep existing protectors in place
        for c in initial_protectors.get(top_field.id, []):
            final_group_for[id(c)] = f"protecting {top_field.id}"
            allocated.add(id(c))

        # If we need more drones for top field, allocate the closest ones
        if current_top < required_top:
            needed = required_top - current_top
            # Build candidate pool: drones not yet allocated
            candidates = []
            for c in components:
                if id(c) in allocated:
                    continue
                # distance to top field center
                dist = distance_to_field(c, top_field)
                candidates.append((dist, c))
            candidates.sort(key=lambda x: x[0])
            for i in range(min(needed, len(candidates))):
                drone = candidates[i][1]
                final_group_for[id(drone)] = f"protecting {top_field.id}"
                allocated.add(id(drone))

        # Step 2: Allocate remaining drones to other fields in threat order
        # For each subsequent field, try to fully protect if possible, or at least partially protect
        for idx in range(1, len(fields_sorted)):
            field = fields_sorted[idx]
            required = max(0, int(getattr(field, "drones_for_full_protection", 0)))
            # Current protectors for this field (from initial state and any previous step)
            current_init = len(initial_protectors.get(field.id, []))
            # Count how many drones we've already assigned to this field in final plan
            current_final = len([d for d in components if final_group_for.get(id(d)) == f"protecting {field.id}"])
            current = current_init + current_final
            if current >= required:
                # If some drones are already protecting this field, keep them; else nothing to do
                continue

            needed = max(0, required - current_final)  # focus on additional allocations from the pool

            # Build candidate pool: drones not yet allocated
            candidates = []
            for c in components:
                if id(c) in allocated:
                    continue
                dist = distance_to_field(c, field)
                candidates.append((dist, c))
            candidates.sort(key=lambda x: x[0])

            for i in range(min(needed, len(candidates))):
                drone = candidates[i][1]
                final_group_for[id(drone)] = f"protecting {field.id}"
                allocated.add(id(drone))

        # Step 3: Idle all drones not assigned
        for c in components:
            if final_group_for.get(id(c)) is None:
                final_group_for[id(c)] = "idle"

        # Apply assignments
        for c in components:
            environment.assign_group(c, final_group_for[id(c)])