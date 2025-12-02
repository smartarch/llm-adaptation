import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Gather fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle everyone
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # 2) Sort threat fields by threat level (high to low)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        total_drones = len(components)

        # 3) Build initial assignment map from current targeting (preserve existing commitments)
        assigned = {}
        for c in components:
            tid = getattr(c, "target_id", None)
            if tid is not None:
                assigned[c] = tid  # drone -> field_id

        # 4) Determine target_set: as many top fields as possible to full protection
        target_set = []
        cum = 0
        # Always try to include the top field if it has a positive requirement
        for f in threat_fields:
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                continue
            if cum + req <= total_drones:
                target_set.append(f)
                cum += req
            else:
                break

        # If no field can be fully protected, concentrate all drones on the top field
        if not target_set:
            top_field = threat_fields[0]
            top_id = top_field.id
            for c in components:
                assigned[c] = top_id
        else:
            # 5) For each field in target_set, ensure it has enough drones
            target_ids = [f.id for f in target_set]

            for idx, field in enumerate(target_set):
                fid = field.id
                current = sum(1 for c in components if assigned.get(c) == fid)
                needed = int(getattr(field, "drones_for_full_protection", 0)) - current
                if needed <= 0:
                    continue

                cx, cy = ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

                # Higher priority fields are those earlier in target_set
                higher_ids = set([f.id for f in target_set[:idx]])

                # Candidates: drones not already protecting this field and not from higher priority fields
                candidates = []
                for d in components:
                    if assigned.get(d) == fid:
                        continue
                    t = getattr(d, "target_id", None)
                    if t in higher_ids:
                        continue
                    # Do not take drones that are currently protecting other target fields
                    if t in target_ids and t != fid:
                        continue
                    candidates.append(d)

                def dist2(d):
                    dx = getattr(d.location, "x", 0.0) - cx
                    dy = getattr(d.location, "y", 0.0) - cy
                    return dx*dx + dy*dy

                candidates.sort(key=dist2)

                for d in candidates[:needed]:
                    assigned[d] = fid

        # 6) If there are still drones not assigned to any field (leftover), assign them to the top-threat field
        remaining = total_drones - len([1 for c in components if c in assigned])
        if remaining > 0:
            top_field = threat_fields[0]
            top_id = top_field.id
            cx, cy = ((top_field.left + top_field.right) / 2.0, (top_field.top + top_field.bottom) / 2.0)

            def dist2_top(d):
                dx = getattr(d.location, "x", 0.0) - cx
                dy = getattr(d.location, "y", 0.0) - cy
                return dx*dx + dy*dy

            # Prefer drones not already assigned to any target field
            unassigned = [d for d in components if assigned.get(d) is None]
            unassigned.sort(key=dist2_top)
            for d in unassigned[:remaining]:
                assigned[d] = top_id

        # 7) Final: map to groups
        for c in components:
            fid = assigned.get(c, None)
            if fid is not None:
                environment.assign_group(c, f"protecting {fid}")
            else:
                environment.assign_group(c, "idle")