import math
from generated_adaptations.base_classes.farm import FarmAdaptation as BaseFarmAdaptation

class SmartFarmAdaptation(BaseFarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Valid group names
        valid_groups = set(group_ids)

        # Identify fields with non-zero threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Pick the most threatened field
        top_field = max(threat_fields, key=lambda f: f.threat_level)
        top_id = top_field.id

        # Count drones effectively protecting top field or on their way to it
        in_transit_to_top = sum(1 for d in components
                               if getattr(d, "state", "") == "moving_to_field"
                               and getattr(d, "target_id", None) == top_id)

        eff_prot = getattr(top_field, "protecting_drones", 0) \
                   + getattr(top_field, "arriving_drones", 0) \
                   + in_transit_to_top

        full_needed = getattr(top_field, "drones_for_full_protection", 0)
        need = max(0, full_needed - eff_prot)

        chosen_for_top = set()

        if need > 0:
            # Center of the field for distance calculations
            cx = (top_field.left + top_field.right) / 2.0
            cy = (top_field.top + top_field.bottom) / 2.0

            # Drones already effectively on top
            for d in components:
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_id:
                    chosen_for_top.add(d)
                elif getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == top_id:
                    chosen_for_top.add(d)

            # Candidates exclude those already on top
            idle_candidates = []
            other_candidates = []
            for d in components:
                if d in chosen_for_top:
                    continue
                loc = getattr(d, "location", None)
                dist = float('inf')
                if loc is not None:
                    dist = math.hypot(loc.x - cx, loc.y - cy)

                if getattr(d, "state", None) == "idle":
                    idle_candidates.append((dist, d))
                else:
                    other_candidates.append((dist, d))

            idle_candidates.sort(key=lambda t: t[0])
            other_candidates.sort(key=lambda t: t[0])

            # First use idle drones, then others
            take_from_idle = min(need, len(idle_candidates))
            for i in range(take_from_idle):
                chosen_for_top.add(idle_candidates[i][1])

            remaining = need - take_from_idle
            if remaining > 0:
                for i in range(min(remaining, len(other_candidates))):
                    chosen_for_top.add(other_candidates[i][1])

        # Apply assignments
        for d in components:
            if d in chosen_for_top:
                group = f"protecting {top_id}"
                if group in valid_groups:
                    environment.assign_group(d, group)
                else:
                    # Fallback to idle if the target group isn't valid
                    environment.assign_group(d, "idle")
                continue

            st = getattr(d, "state", None)
            tid = getattr(d, "target_id", None)

            if st == "protecting" and tid is not None:
                group = f"protecting {tid}"
                if group in valid_groups:
                    environment.assign_group(d, group)
                else:
                    environment.assign_group(d, "idle")
            elif st == "moving_to_field" and tid is not None:
                # Treat en route drones as targeting their destination field
                group = f"protecting {tid}"
                if group in valid_groups:
                    environment.assign_group(d, group)
                else:
                    environment.assign_group(d, "idle")
            else:
                # Idle or unknown targets
                if "idle" in valid_groups:
                    environment.assign_group(d, "idle")
                else:
                    # Fallback: try to assign to the top field group if still valid
                    top_group = f"protecting {top_id}"
                    if top_group in valid_groups:
                        environment.assign_group(d, top_group)
                    else:
                        environment.assign_group(d, "idle")