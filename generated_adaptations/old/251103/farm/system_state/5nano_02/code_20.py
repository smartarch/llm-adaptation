from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Enhanced multi-field protection with thoughtful reallocation:
        - Protect threatened fields in descending threat order.
        - Pre-allocate drones already targeting a field (protecting/moving_to_field).
        - For each field, fill to drones_for_full_protection using closest idle drones first,
          then consider reallocating drones from other fields only if that other field is safe to reduce.
        - After processing all threatened fields, assign remaining drones to idle.
        """
        # 1) Gather threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort by threat (highest first)
        threatened_fields.sort(key=lambda fld: fld.threat_level, reverse=True)

        # Helpers
        id_to_field = {fld.id: fld for fld in threatened_fields}
        field_ids = {fld.id for fld in threatened_fields}
        field_alloc = {fld.id: set() for fld in threatened_fields}
        allocated = set()
        drone_to_field = {}

        # 3) Pre-allocate drones already heading to some field
        for d in components:
            fid = getattr(d, "target_id", None)
            st = getattr(d, "state", "")
            if fid in field_ids and st in ("protecting", "moving_to_field"):
                field_alloc[fid].add(d)
                allocated.add(d)
                drone_to_field[d] = fid

        # 4) Allocate for each field in threat order
        for fld in threatened_fields:
            fid = fld.id
            needed = int(getattr(fld, "drones_for_full_protection", 0))
            current = field_alloc.get(fid, set())
            current_count = len(current)

            if current_count >= max(needed, 0):
                continue

            remaining = max(0, needed - current_count)
            if remaining == 0:
                continue

            center_x = (fld.left + fld.right) / 2.0
            center_y = (fld.top + fld.bottom) / 2.0

            candidates = []

            # 5a) Idle drones first
            idle_candidates = [d for d in components if getattr(d, "state", "") == "idle" and d not in allocated]
            candidates.extend(idle_candidates)

            # 5b) If not enough, consider reallocating from other fields safely
            if len(candidates) < remaining:
                for d in components:
                    if d in allocated or d in current:
                        continue
                    st = getattr(d, "state", "")
                    if st in ("protecting", "moving_to_field"):
                        other_fid = getattr(d, "target_id", None)
                        other_field = id_to_field.get(other_fid) if other_fid in id_to_field else None
                        other_threat = getattr(other_field, "threat_level", 0) if other_field else 0
                        # Only steal from fields with threat <= current field's threat and that are potentially over-protected
                        if other_field is not None and other_threat <= fld.threat_level:
                            other_needed = int(getattr(other_field, "drones_for_full_protection", 0))
                            other_current = len(field_alloc.get(other_fid, set()))
                            if other_current > max(other_needed, 0):
                                candidates.append(d)

            # 6) Sort by distance to field center
            def dist2(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float("inf")
                dx = loc.x - center_x
                dy = loc.y - center_y
                return dx * dx + dy * dy

            candidates.sort(key=dist2)

            # 7) Take the closest remaining drones
            for i in range(min(remaining, len(candidates))):
                d = candidates[i]
                # Reallocate if needed
                prev_field = None
                if d in allocated:
                    for other_id, s in field_alloc.items():
                        if d in s and other_id != fid:
                            s.remove(d)
                            prev_field = other_id
                            break
                field_alloc.setdefault(fid, set()).add(d)
                allocated.add(d)
                drone_to_field[d] = fid

        # 8) Assign groups
        for d in components:
            fid = drone_to_field.get(d)
            if fid is not None:
                environment.assign_group(d, f"protecting {fid}")
            else:
                environment.assign_group(d, "idle")