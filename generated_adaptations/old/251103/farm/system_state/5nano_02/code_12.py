from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Multi-field, top-threat-first but with in-flight awareness:
        - Identify all fields with threat_level > 0 and sort by threat descending.
        - Treat drones already targeting a field (state in {"protecting", "moving_to_field"}) as allocated to that field.
        - For each threatened field in that order, ensure drones_for_full_protection drones are allocated to that field.
          Allocation prefers closest idle drones to the field center.
        - Drones already allocated to one field are not reassigned to another field.
        - After attempting to protect all threatened fields, any remaining drones are set to idle.
        - Groups used: "idle" and "protecting <Field_ID>".
        - This strategy aims to maximize protection where it matters most while minimiting wasted travel and avoiding disruption of already-committed drones.
        """
        # 1) Gather threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort fields by threat (highest first)
        threatened_fields.sort(key=lambda fld: fld.threat_level, reverse=True)

        # Keep track of allocations: field_id -> set(drones)
        field_alloc = {}
        # Also global set of allocated drones
        allocated = set()
        # Mapping from drone -> field_id for assigning groups later
        drone_to_field = {}

        # 3) Pre-allocate drones already heading to some field
        field_ids = {fld.id for fld in threatened_fields}
        for d in components:
            fid = getattr(d, "target_id", None)
            st = getattr(d, "state", "")
            if fid in field_ids and st in ("protecting", "moving_to_field"):
                field_alloc.setdefault(fid, set()).add(d)
                allocated.add(d)
                drone_to_field[d] = fid

        # 4) Iterate fields in threat order and fill as needed
        for fld in threatened_fields:
            fid = fld.id
            needed = int(getattr(fld, "drones_for_full_protection", 0))

            current = field_alloc.get(fid, set())
            current_count = len(current)

            if current_count >= max(needed, 0):
                continue  # already fully protected

            remaining = max(0, needed - current_count)
            if remaining == 0:
                continue

            # 5) Find closest idle drones to this field center
            center_x = (fld.left + fld.right) / 2.0
            center_y = (fld.top + fld.bottom) / 2.0

            # Idle drones are the preferred pool to fill; avoid disturbing drones already en route
            idle_candidates = [
                d for d in components
                if d not in allocated and getattr(d, "state", "") == "idle"
            ]

            def dist2(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float("inf")
                dx = loc.x - center_x
                dy = loc.y - center_y
                return dx * dx + dy * dy

            idle_candidates.sort(key=dist2)

            # 6) Take the closest remaining drones
            to_assign = idle_candidates[:remaining]
            for d in to_assign:
                field_alloc.setdefault(fid, set()).add(d)
                allocated.add(d)
                drone_to_field[d] = fid

        # 7) Apply groups: allocated drones to their respective protect groups; others idle
        for d in components:
            fid = drone_to_field.get(d)
            if fid is not None:
                environment.assign_group(d, f"protecting {fid}")
            else:
                environment.assign_group(d, "idle")