from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat levels
        fields = getattr(environment, "fields", []) or []
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # Helper: compute field center
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # If there is no threat, idle all drones (fallback to a valid group)
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

        # If the top_group isn't allowed, idle all
        if top_group not in group_ids:
            for d in components:
                if "idle" in group_ids:
                    environment.assign_group(d, "idle")
                elif group_ids:
                    environment.assign_group(d, group_ids[0])
            return

        assigned = set()

        # Step 1: Fully protect the top field if possible
        needed_top = max(
            0,
            getattr(top_field, "drones_for_full_protection", 0)
            - (getattr(top_field, "protecting_drones", 0) + getattr(top_field, "arriving_drones", 0))
        )
        cx, cy = center_of(top_field)

        # Step 1a: Allocate the necessary drones to the top field from the closest drones
        if needed_top > 0:
            # Distances from all drones to the top field center
            all_by_dist = []
            for d in components:
                loc = getattr(d, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0.0)
                    dy = getattr(loc, "y", 0.0)
                    dist = math.hypot(dx - cx, dy - cy)
                else:
                    dist = float("inf")
                all_by_dist.append((dist, d))
            all_by_dist.sort(key=lambda t: t[0])

            to_take = min(needed_top, len(all_by_dist))
            for i in range(to_take):
                d = all_by_dist[i][1]
                environment.assign_group(d, top_group)
                assigned.add(d)

        # Step 2: After top field addressed, help other threatened fields with remaining drones
        # Build a pool of remaining drones (not yet assigned to top_group)
        pool = []
        for d in components:
            if d in assigned:
                continue
            loc = getattr(d, "location", None)
            if loc is not None:
                dx = getattr(loc, "x", 0.0)
                dy = getattr(loc, "y", 0.0)
                dist = math.hypot(dx - cx, dy - cy)
            else:
                dist = float("inf")
            pool.append((dist, d))
        pool.sort(key=lambda t: t[0])

        for f in threatened[1:]:
            grp = f"protecting {f.id}"
            if grp not in group_ids:
                continue
            current = getattr(f, "protecting_drones", 0) + getattr(f, "arriving_drones", 0)
            needed = max(0, getattr(f, "drones_for_full_protection", 0) - current)
            if needed <= 0:
                continue
            if not pool:
                break
            take = min(needed, len(pool))
            for i in range(take):
                d = pool[i][1]
                environment.assign_group(d, grp)
                assigned.add(d)
            pool = pool[take:]

        # Step 3: Final safety – ensure every drone has a valid group
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
            if "idle" in group_ids:
                environment.assign_group(d, "idle")
            elif group_ids:
                environment.assign_group(d, group_ids[0])