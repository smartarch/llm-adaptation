from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Enhanced multi-field, top-threat-first strategy with in-flight awareness and
        flexible reallocation:
        - Consider all fields with threat_level > 0, sorted by threat descending.
        - Drones already targeting a field (protecting or moving_to_field) are treated as allocated.
        - For each threatened field in threat order, allocate drones to reach drones_for_full_protection.
          Allocation prefers the closest available drones to the field center.
        - Drones currently protecting other fields can be reallocated to higher-threat fields if needed.
        - After processing all threatened fields, any remaining drones are set to idle.
        - Groups used: "idle" and "protecting <Field_ID>".
        """
        # 1) Gather threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort fields by threat descending
        threatened_fields.sort(key=lambda fld: fld.threat_level, reverse=True)

        # 3) Build initial allocations: field_id -> set(drones)
        field_alloc = {fld.id: set() for fld in threatened_fields}
        allocated = set()  # drones already allocated to some field
        drone_to_field = {}

        field_ids = {fld.id for fld in threatened_fields}

        # 4) Pre-allocate drones already heading to some field
        for d in components:
            fid = getattr(d, "target_id", None)
            st = getattr(d, "state", "")
            if fid in field_ids and st in ("protecting", "moving_to_field"):
                field_alloc[fid].add(d)
                allocated.add(d)
                drone_to_field[d] = fid

        # 5) Allocate drones for each field in threat order
        for fld in threatened_fields:
            fid = fld.id
            needed = int(getattr(fld, "drones_for_full_protection", 0))

            current = field_alloc.get(fid, set())
            current_count = len(current)

            if current_count >= max(needed, 0):
                # Already enough; ensure mapping
                for d in current:
                    drone_to_field[d] = fid
                continue

            remaining = max(0, needed - current_count)
            if remaining == 0:
                continue

            # Field center
            center_x = (fld.left + fld.right) / 2.0
            center_y = (fld.top + fld.bottom) / 2.0

            # 6) Build candidate pool: all drones not currently allocated to this field
            candidates = [d for d in components if d not in current]

            # 7) Sort candidates by distance to field center
            def dist2(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float("inf")
                dx = loc.x - center_x
                dy = loc.y - center_y
                return dx * dx + dy * dy

            candidates.sort(key=dist2)

            # 8) Take the closest remaining drones
            for i in range(min(remaining, len(candidates))):
                d = candidates[i]
                # If this drone was allocated to another field, steal it
                prev_field = None
                for other_id, s in field_alloc.items():
                    if other_id != fid and d in s:
                        s.remove(d)
                        prev_field = other_id
                        break
                field_alloc.setdefault(fid, set()).add(d)
                allocated.add(d)
                drone_to_field[d] = fid

        # 9) Build final mapping: drone -> final field id
        drone_final_field = {}
        for fid, drones in field_alloc.items():
            for d in drones:
                drone_final_field[d] = fid

        # 10) Assign groups: protecting <Field_ID> for final field allocations; idle otherwise
        for d in components:
            fid = drone_final_field.get(d)
            if fid is not None:
                environment.assign_group(d, f"protecting {fid}")
            else:
                environment.assign_group(d, "idle")