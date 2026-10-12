from math import sqrt
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Persist across steps: map drone_id -> last_protected_field_id or None
        self._last_target_by_drone = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Gather threatened fields (threat_level > 0)
        fields = list(getattr(environment, "fields", []))
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If nothing is threatened, idle all drones
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            # Update memory to reflect no protection
            for d in components:
                self._last_target_by_drone[id(d)] = None
            return

        # 2) Compute field centers for distance calculations
        field_centers = {}
        for f in threatened_fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top  + f.bottom) / 2.0
            field_centers[f.id] = (cx, cy)

        # 3) Helper: determine current group for a drone (consider moving_to_field as protection)
        def current_group(d):
            st = getattr(d, "state", None)
            tid = getattr(d, "target_id", None)
            if st in ("protecting", "moving_to_field") and tid is not None:
                return f"protecting {tid}"
            return "idle"

        # 4) Start with the current assignment as the baseline
        final_group = {d: current_group(d) for d in components}

        # 5) Sort threatened fields by threat descending
        threatened_sorted = sorted(
            threatened_fields,
            key=lambda ff: getattr(ff, "threat_level", 0),
            reverse=True
        )

        # Local helper to add drones to protect a specific field until its full_protection is reached
        def fill_field_to_full(field):
            field_id = field.id
            grp = f"protecting {field_id}"
            # Current protectors for this field
            current_protectors = sum(1 for d in components if final_group.get(d) == grp)
            needed = int(getattr(field, "drones_for_full_protection", 0)) - current_protectors
            if needed <= 0:
                return
            cx, cy = field_centers[field_id]

            # Build candidate drones not currently protecting this field
            candidates = []
            for d in components:
                if final_group.get(d) == grp:
                    continue
                loc = getattr(d, "location", None)
                if loc is None:
                    dist = float("inf")
                else:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist = sqrt(dx*dx + dy*dy)
                last_match = (self._last_target_by_drone.get(id(d)) == field_id)
                # Prioritize drones that previously protected this field
                candidates.append((0 if last_match else 1, dist, d))
            candidates.sort(key=lambda t: (t[0], t[1]))

            for _, _, d in candidates[:max(0, needed)]:
                final_group[d] = grp

        # 6) Step 1: Fully protect the most threatened field
        top_field = threatened_sorted[0]
        fill_field_to_full(top_field)

        # 7) Step 2: Fully protect remaining threatened fields, in order
        for f in threatened_sorted[1:]:
            fill_field_to_full(f)

        # 8) Step 3: Ensure at least half of drones are protecting, if possible
        total_drones = len(components)
        half = (total_drones + 1) // 2
        current_protectors = sum(1 for d in components if final_group.get(d, "idle").startswith("protecting "))
        if current_protectors < half:
            # We'll allocate additional drones (preferring last_target memory)
            # Build a pool of all drones not currently protecting this needed field when filling
            # We'll attempt to bolster in threat-descending order across threatened fields
            for f in threatened_sorted:
                if current_protectors >= half:
                    break
                grp = f"protecting {f.id}"
                count = sum(1 for d in components if final_group.get(d) == grp)
                if count >= int(getattr(f, "drones_for_full_protection", 0)):
                    continue
                cx, cy = field_centers[f.id]

                candidates = []
                for d in components:
                    if final_group.get(d) == grp:
                        continue
                    loc = getattr(d, "location", None)
                    if loc is None:
                        dist = float("inf")
                    else:
                        dx = getattr(loc, "x", 0.0) - cx
                        dy = getattr(loc, "y", 0.0) - cy
                        dist = sqrt(dx*dx + dy*dy)
                    last_match = (self._last_target_by_drone.get(id(d)) == f.id)
                    candidates.append((0 if last_match else 1, dist, d))
                candidates.sort(key=lambda t: (t[0], t[1]))

                # How many we need for this field to reach its full protection
                needed = int(getattr(f, "drones_for_full_protection", 0)) - count
                if needed <= 0:
                    continue
                for _, _, d in candidates[:needed]:
                    final_group[d] = grp
                    current_protectors += 1
                    if current_protectors >= half:
                        break

        # 9) Step 4: Update memory of last target per drone
        for d in components:
            g = final_group.get(d, "idle")
            if isinstance(g, str) and g.startswith("protecting "):
                field_id = g.split(" ", 1)[1]
                self._last_target_by_drone[id(d)] = field_id
            else:
                self._last_target_by_drone[id(d)] = None

        # 10) Final assignment to environment
        for d in components:
            grp = final_group.get(d, "idle")
            environment.assign_group(d, grp)