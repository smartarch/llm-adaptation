import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
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
        assigned_map = {}  # drone -> field_id

        # Helper to compute field center
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

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

        # If no field can be fully protected (top field requires more drones than available),
        # allocate all drones to the top field to maximize protection there.
        if not target_set:
            top_field = threat_fields[0]
            top_id = top_field.id
            for c in components:
                assigned_map[c] = top_id
        else:
            # 4) Ensure each field in target_set gets full protection by reallocating closest drones.
            # First, mark current protectors for each target field
            for f in target_set:
                fid = f.id
                current = [d for d in components if getattr(d, "target_id", None) == fid]
                for d in current:
                    assigned_map[d] = fid

            # For each field in target_set, fill the deficit
            for f in target_set:
                fid = f.id
                needed = int(getattr(f, "drones_for_full_protection", 0)) - len([d for d in components if assigned_map.get(d) == fid])
                if needed <= 0:
                    continue
                cx, cy = center_of(f)

                # Pool of all drones, sorted by distance to this field
                def dist2(d):
                    dx = getattr(d.location, "x", 0.0) - cx
                    dy = getattr(d.location, "y", 0.0) - cy
                    return dx*dx + dy*dy

                pool = sorted(components, key=dist2)
                for d in pool:
                    if assigned_map.get(d) == fid:
                        continue
                    assigned_map[d] = fid
                    needed -= 1
                    if needed == 0:
                        break

            # 5) Allocate leftovers to the top threat field to boost protection if possible
            remaining = total_drones - len(set(assigned_map.keys()))
            if remaining > 0:
                top_field = threat_fields[0]
                top_id = top_field.id
                cx, cy = center_of(top_field)

                def dist2_top(d):
                    dx = getattr(d.location, "x", 0.0) - cx
                    dy = getattr(d.location, "y", 0.0) - cy
                    return dx*dx + dy*dy

                pool = sorted(components, key=dist2_top)
                for d in pool:
                    if d in assigned_map:
                        continue
                    assigned_map[d] = top_id
                    remaining -= 1
                    if remaining == 0:
                        break

        # 6) Final: assign groups based on assigned_map, rest idle
        for c in components:
            if c in assigned_map:
                environment.assign_group(c, f"protecting {assigned_map[c]}")
            else:
                environment.assign_group(c, "idle")