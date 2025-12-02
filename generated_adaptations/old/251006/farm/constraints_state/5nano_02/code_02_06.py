from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields (threat_level > 0)
        fields = getattr(environment, "fields", []) or []
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # Helper: field center
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # If no threatened fields, idle all drones (or fallback if idle not available)
        if not threatened:
            for d in components:
                if "idle" in group_ids:
                    environment.assign_group(d, "idle")
                elif group_ids:
                    environment.assign_group(d, group_ids[0])
            return

        # Sort threatened fields by threat level (highest first)
        threatened.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        top_field = threatened[0]
        top_group = f"protecting {top_field.id}"

        # If top group not valid, idle all
        if top_group not in group_ids:
            for d in components:
                if "idle" in group_ids:
                    environment.assign_group(d, "idle")
                elif group_ids:
                    environment.assign_group(d, group_ids[0])
            return

        assigned = set()
        # Step 1: Fully protect the top field using idle drones first, then fall back if needed
        needed_top = max(
            0,
            getattr(top_field, "drones_for_full_protection", 0)
            - (getattr(top_field, "protecting_drones", 0) + getattr(top_field, "arriving_drones", 0))
        )

        center_x, center_y = center_of(top_field)

        # Use idle drones first
        idle_candidates = []
        for d in components:
            if getattr(d, "state", "") == "idle":
                loc = getattr(d, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0)
                    dy = getattr(loc, "y", 0.0)
                else:
                    dx = dy = 0.0
                dist = math.hypot(dx - center_x, dy - center_y)
                idle_candidates.append((dist, d))
        idle_candidates.sort(key=lambda t: t[0])

        top_assigned = []
        if needed_top > 0 and idle_candidates:
            to_take = min(needed_top, len(idle_candidates))
            for i in range(to_take):
                d = idle_candidates[i][1]
                environment.assign_group(d, top_group)
                assigned.add(d)
                top_assigned.append(d)

        # If still not fully protected, reallocate from any remaining drones (to meet top need)
        still_needed = max(0, needed_top - len(top_assigned))
        if still_needed > 0:
            # Consider all other drones not already in top_group, sort by distance to top field center
            remaining = []
            for d in components:
                if d in assigned:
                    continue
                # Distance to top field center
                loc = getattr(d, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0)
                    dy = getattr(loc, "y", 0.0)
                else:
                    dx = dy = 0.0
                dist = math.hypot(dx - center_x, dy - center_y)
                remaining.append((dist, d))
            remaining.sort(key=lambda t: t[0])
            for dist, d in remaining[:still_needed]:
                environment.assign_group(d, top_group)
                assigned.add(d)
                still_needed -= 1
                if still_needed == 0:
                    break

        # Step 2: After top field is (ideally) fully protected, allocate to other threatened fields
        # Use remaining drones (prefer idle first)
        # Build a pool of currently idle drones not yet assigned
        remaining_idle = []
        for d in components:
            if d in assigned:
                continue
            if getattr(d, "state", "") == "idle":
                loc = getattr(d, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0)
                    dy = getattr(loc, "y", 0.0)
                else:
                    dx = dy = 0.0
                dist = math.hypot(dx - center_x, dy - center_y)
                remaining_idle.append((dist, d))
        remaining_idle.sort(key=lambda t: t[0])

        # For other fields (in threat order), try to help if there are idle drones
        for f in threatened[1:]:
            grp = f"protecting {f.id}"
            if grp not in group_ids:
                continue
            current = getattr(f, "protecting_drones", 0) + getattr(f, "arriving_drones", 0)
            needed = max(0, getattr(f, "drones_for_full_protection", 0) - current)
            if needed <= 0:
                continue
            if not remaining_idle:
                break
            # Allocate from closest idle drones
            take = min(needed, len(remaining_idle))
            for i in range(take):
                d = remaining_idle[i][1]
                environment.assign_group(d, grp)
                assigned.add(d)
            # Remove allocated from pool
            remaining_idle = remaining_idle[take:]

        # Step 3: As a safety, ensure every drone has a valid group
        for d in components:
            if d in assigned:
                continue
            st = getattr(d, "state", "")
            tgt = getattr(d, "target_id", None)
            if st == "protecting" and tgt is not None:
                grp = f"protecting {tgt}"
                if grp in group_ids:
                    environment.assign_group(d, grp)
                    assigned.add(d)
                    continue
            if st == "moving_to_field" and tgt is not None:
                grp = f"protecting {tgt}"
                if grp in group_ids:
                    environment.assign_group(d, grp)
                    assigned.add(d)
                    continue
            # Fallback to idle if available
            if "idle" in group_ids:
                environment.assign_group(d, "idle")
            elif group_ids:
                environment.assign_group(d, group_ids[0])