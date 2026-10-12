from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        N = len(components)
        if N == 0:
            return

        # Gather fields with positive threat, sorted by threat (desc)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # No threat: idle all drones if possible
            for d in components:
                if "idle" in group_ids:
                    environment.assign_group(d, "idle")
                elif group_ids:
                    environment.assign_group(d, group_ids[0])
            return

        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = threatened_fields[0]

        # Helper to compute center of a field
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Top field protection
        top_center = center_of(top_field)
        top_required = max(0, getattr(top_field, "drones_for_full_protection", 0))
        protect_group_top = f"protecting {top_field.id}"
        use_top_group = protect_group_top in group_ids

        # Distances from drones to top field center
        dist_to_top = []
        for d in components:
            loc = getattr(d, "location", None)
            dx = (loc.x if loc is not None else 0.0) - top_center[0]
            dy = (loc.y if loc is not None else 0.0) - top_center[1]
            dist = math.hypot(dx, dy)
            dist_to_top.append((dist, d))
        dist_to_top.sort(key=lambda t: t[0])

        assigned = set()

        # Allocate top field drones (as many as allowed by available drones)
        num_top = min(top_required, N)
        for i in range(num_top):
            drone = dist_to_top[i][1]
            if use_top_group:
                environment.assign_group(drone, protect_group_top)
            else:
                if group_ids:
                    environment.assign_group(drone, group_ids[0])
            assigned.add(drone)

        # Step 2: Allocate remaining drones to other threatened fields, fully if possible
        for field in threatened_fields[1:]:
            if len(assigned) >= N:
                break
            available = [d for d in components if d not in assigned]
            if not available:
                break

            field_center = center_of(field)
            required = max(0, getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue

            # Sort available drones by distance to this field center
            dist_list = []
            for d in available:
                loc = getattr(d, "location", None)
                dx = (loc.x if loc is not None else 0.0) - field_center[0]
                dy = (loc.y if loc is not None else 0.0) - field_center[1]
                dist = math.hypot(dx, dy)
                dist_list.append((dist, d))
            dist_list.sort(key=lambda t: t[0])

            to_assign = min(required, len(dist_list))
            protect_group = f"protecting {field.id}"
            valid_group = protect_group in group_ids

            for i in range(to_assign):
                drone = dist_list[i][1]
                if valid_group:
                    environment.assign_group(drone, protect_group)
                else:
                    if group_ids:
                        environment.assign_group(drone, group_ids[0])
                assigned.add(drone)

        # Step 3: Any remaining drones: idle or fallback
        for d in components:
            if d in assigned:
                continue
            if "idle" in group_ids:
                environment.assign_group(d, "idle")
            elif group_ids:
                environment.assign_group(d, group_ids[0])