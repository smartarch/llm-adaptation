import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Strategy notes embedded as comments:
        # - Dynamically protect as many high-threat fields as possible, prioritizing higher threat fields.
        # - Keep drones on higher-priority fields if already protecting them; only move drones from lower-priority
        #   fields when needed to fulfill higher-priority protection.
        # - When filling deficits, prefer drones that are not currently protecting higher-priority fields and are close
        #   to the target field to minimize movement.
        # - If no field can be fully protected due to limited drones, concentrate on the top-threat field by moving
        #   the closest available drones there.

        # 1) Collect fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle everyone
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # 2) Sort threat fields by threat level (high to low)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        total_drones = len(components)

        # 3) Determine target set: as many top fields as possible to full protection
        target_set = []
        cum_required = 0
        for f in threat_fields:
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                continue
            if cum_required + req <= total_drones:
                target_set.append(f)
                cum_required += req
            else:
                break

        # If no field can be fully protected, concentrate all drones on the top field
        if not target_set:
            top_field = threat_fields[0]
            top_id = top_field.id
            for c in components:
                environment.assign_group(c, f"protecting {top_id}")
            return

        # 4) Build an assignment map: drone -> field_id
        assigned = {}

        # Step 1: Keep existing protection for target_set fields
        for f in target_set:
            fid = f.id
            for c in components:
                if getattr(c, "target_id", None) == fid:
                    assigned[c] = fid

        # Helper to compute field center
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Step 2: Fill deficits for each field in target_set in order
        for idx, f in enumerate(target_set):
            fid = f.id
            # Current count of drones targeting this field
            current_count = len([d for d in components if getattr(d, "target_id", None) == fid])
            needed = int(getattr(f, "drones_for_full_protection", 0)) - current_count
            if needed <= 0:
                continue

            cx, cy = center_of(f)
            # Drones that are not currently targeting this field and not targeting higher-priority fields
            forbidden_ids = set([ff.id for ff in target_set[:idx]])  # higher priority fields
            candidates = [
                d for d in components
                if getattr(d, "target_id", None) != fid and getattr(d, "target_id", None) not in forbidden_ids
            ]

            def dist2(d):
                dx = getattr(d.location, "x", 0.0) - cx
                dy = getattr(d.location, "y", 0.0) - cy
                return dx*dx + dy*dy

            candidates.sort(key=dist2)

            for d in candidates[:needed]:
                assigned[d] = fid

        # 5) Assign groups based on assignment
        for c in components:
            if c in assigned:
                environment.assign_group(c, f"protecting {assigned[c]}")
            else:
                environment.assign_group(c, "idle")