from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Enhanced multi-field protection with in-flight awareness and safe reallocation:
        - Identify all fields with threat_level > 0, sorted by threat descending.
        - Drones already targeting a field (state in {"protecting","moving_to_field"}) are treated as allocated to that field.
        - For each threatened field in threat order, allocate drones to reach drones_for_full_protection.
          Allocation prefers the closest available drones to the field center.
        - Prefer reallocating drones only from fields that are already fully protected or from fields with
          lower or equal threat than the current field, to minimize damage risk on currently protected fields.
        - After processing all threatened fields, remaining drones go idle.
        - Groups used: "idle" and "protecting <Field_ID>".
        """
        # 1) Gather threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort fields by threat (highest first)
        threatened_fields.sort(key=lambda fld: fld.threat_level, reverse=True)

        # 3) Track allocations: field_id -> set(drones)
        field_alloc = {fld.id: set() for fld in threatened_fields}
        allocated = set()                # all drones allocated to any field
        drone_to_field = {}                # mapping drone -> field_id

        field_ids = {fld.id for fld in threatened_fields}

        # 4) Pre-allocate drones already heading to some field
        for d in components:
            fid = getattr(d, "target_id", None)
            st = getattr(d, "state", "")
            if fid in field_ids and st in ("protecting", "moving_to_field"):
                field_alloc[fid].add(d)
                allocated.add(d)
                drone_to_field[d] = fid

        # 5) Allocate for each field in threat order
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

            # Build candidate pool
            candidates = []

            # Idle drones first
            idle_candidates = [d for d in components if getattr(d, "state", "") == "idle" and d not in allocated]
            candidates.extend(idle_candidates)

            # If not enough, consider reallocating from lower-threat fields or fully-protected fields
            if len(candidates) < remaining:
                for d in components:
                    if d in allocated:
                        continue
                    st = getattr(d, "state", "")
                    if st in ("protecting", "moving_to_field"):
                        other_fid = getattr(d, "target_id", None)
                        other_field = next((ff for ff in environment.fields if ff.id == other_fid), None)
                        other_threat = getattr(other_field, "threat_level", 0) if other_field else 0
                        # Reallocate from lower-or-equal-threat fields if safe
                        if other_threat <= fld.threat_level:
                            # Check if the other field is fully protected
                            if other_field is not None:
                                needed_other = int(getattr(other_field, "drones_for_full_protection", 0))
                                count_other = len([dd for dd in components if getattr(dd, "target_id", None) == other_fid and getattr(dd, "state", "") in ("protecting","moving_to_field")])
                                if count_other >= max(needed_other, 0):
                                    candidates.append(d)
                            else:
                                candidates.append(d)

            # Sort candidates by distance to field center
            def dist2(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float("inf")
                dx = loc.x - center_x
                dy = loc.y - center_y
                return dx * dx + dy * dy

            candidates.sort(key=dist2)

            # Take closest remaining
            for i in range(min(remaining, len(candidates))):
                d = candidates[i]
                field_alloc.setdefault(fid, set()).add(d)
                allocated.add(d)
                drone_to_field[d] = fid

        # 6) Apply groups based on final allocations
        for d in components:
            fid = drone_to_field.get(d)
            if fid is not None:
                environment.assign_group(d, f"protecting {fid}")
            else:
                environment.assign_group(d, "idle")