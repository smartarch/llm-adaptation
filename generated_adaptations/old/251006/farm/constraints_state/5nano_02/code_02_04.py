from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat levels
        fields = getattr(environment, "fields", []) or []
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # Helper to compute field center
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

        assigned = {}
        available = list(components)

        top_field = threatened[0]
        top_grp = f"protecting {top_field.id}"

        # Step 1: Try to fully protect the top field if possible
        if top_grp in group_ids:
            needed = max(
                0,
                getattr(top_field, "drones_for_full_protection", 0)
                - (getattr(top_field, "protecting_drones", 0) + getattr(top_field, "arriving_drones", 0))
            )
            if needed > 0:
                cx, cy = center_of(top_field)
                candidates = []
                for d in available:
                    if getattr(d, "state", "") == "idle":
                        loc = getattr(d, "location", None)
                        if loc is not None:
                            dx = getattr(loc, "x", 0.0)
                            dy = getattr(loc, "y", 0.0)
                        else:
                            dx = dy = 0.0
                        dist = ((dx - cx) ** 2 + (dy - cy) ** 2) ** 0.5
                        candidates.append((dist, d))
                candidates.sort(key=lambda t: t[0])
                for _, d in candidates[:needed]:
                    environment.assign_group(d, top_grp)
                    assigned[d] = top_grp
                    if d in available:
                        available.remove(d)

        # Step 2: Use remaining drones to help other threatened fields (greedy)
        for f in threatened:
            grp = f"protecting {f.id}"
            if grp not in group_ids:
                continue
            current = getattr(f, "protecting_drones", 0) + getattr(f, "arriving_drones", 0)
            needed = max(0, getattr(f, "drones_for_full_protection", 0) - current)
            if needed <= 0:
                continue
            if not available:
                break
            if f.id == top_field.id and current >= getattr(f, "drones_for_full_protection", 0):
                continue
            cx, cy = center_of(f)
            candidates = []
            for d in available:
                if getattr(d, "state", "") == "idle":
                    loc = getattr(d, "location", None)
                    if loc is not None:
                        dx = getattr(loc, "x", 0.0)
                        dy = getattr(loc, "y", 0.0)
                    else:
                        dx = dy = 0.0
                    dist = ((dx - cx) ** 2 + (dy - cy) ** 2) ** 0.5
                    candidates.append((dist, d))
            candidates.sort(key=lambda t: t[0])
            for _, d in candidates[:needed]:
                environment.assign_group(d, grp)
                assigned[d] = grp
                if d in available:
                    available.remove(d)

        # Step 3: Final pass to ensure everyone has a valid group
        for d in components:
            if d in assigned:
                continue
            st = getattr(d, "state", "")
            tgt = getattr(d, "target_id", None)
            if st == "protecting" and tgt is not None:
                grp = f"protecting {tgt}"
                if grp in group_ids:
                    environment.assign_group(d, grp)
                    assigned[d] = grp
                    continue
            if st == "moving_to_field" and tgt is not None:
                grp = f"protecting {tgt}"
                if grp in group_ids:
                    environment.assign_group(d, grp)
                    assigned[d] = grp
                    continue
            if "idle" in group_ids:
                environment.assign_group(d, "idle")
            elif group_ids:
                environment.assign_group(d, group_ids[0])