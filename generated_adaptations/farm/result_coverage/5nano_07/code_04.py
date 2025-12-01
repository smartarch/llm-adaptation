from generated_adaptations.base_classes import farm as base

class SmartFarmAdaptation(base.FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields = getattr(environment, "fields", []) or []
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If there are no threats, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Map field id to field object for quick access
        field_by_id = {getattr(f, "id"): f for f in threat_fields}

        # Determine how many drones are currently protecting each field
        current_protect_count = {}
        for f in threat_fields:
            cid = f.id
            current_protect_count[cid] = 0

        for c in components:
            if getattr(c, "state", None) == "protecting":
                tgt = getattr(c, "target_id", None)
                if tgt in current_protect_count:
                    current_protect_count[tgt] = current_protect_count.get(tgt, 0) + 1

        # Fields that are already fully protected
        fully_protected_fields = []
        for f in threat_fields:
            required = getattr(f, "drones_for_full_protection", 0)
            if required > 0 and current_protect_count.get(f.id, 0) >= required:
                fully_protected_fields.append(f)

        # First, idle all drones (we'll reassign as needed)
        for c in components:
            environment.assign_group(c, "idle")

        # Reassign drones that are currently protecting a fully protected field to that field's group
        for f in fully_protected_fields:
            field_group = f"protecting {f.id}"
            for c in components:
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id:
                    environment.assign_group(c, field_group)

        # Build the set of drones that are currently protecting fully protected fields
        protected_drones = set()
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tgt = getattr(c, "target_id", None)
                if any(tgt == fp.id for fp in fully_protected_fields):
                    protected_drones.add(c)

        # Spare drones are all drones not in protected_drones
        spare_drones = [c for c in components if c not in protected_drones]

        # Compute remaining needs for fields that are not fully protected yet
        remaining_needs = []
        for f in threat_fields:
            if f in fully_protected_fields:
                continue
            required = getattr(f, "drones_for_full_protection", 0)
            if required <= 0:
                continue
            current = current_protect_count.get(f.id, 0)
            remaining = max(0, int(required) - int(current))
            if remaining > 0:
                remaining_needs.append((f, remaining, getattr(f, "threat_level", 0.0)))

        # If nothing to do, keep fully protected fields and idle others
        if not remaining_needs:
            # Ensure fully protected drones stay in their groups
            for f in fully_protected_fields:
                group = f"protecting {f.id}"
                # Reassign any drones that should be there (best-effort)
                for c in components:
                    if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id:
                        environment.assign_group(c, group)
            return

        # Budget: number of spare drones we can allocate to complete some fields
        budget = len(spare_drones)
        if budget <= 0:
            # No spare drones to allocate; keep as is (fully protected fields have their drones; others idle)
            return

        # Greedy selection of fields to fully protect based on efficiency threat_per_remaining
        # Sort by threat per remaining (higher first); break ties by smaller remaining (cheaper first)
        remaining_needs.sort(key=lambda t: (-(t[2] / max(1, t[1])), t[1]))

        chosen_fields = []
        remaining_budget = budget
        for (f, rem, threat) in remaining_needs:
            if rem <= remaining_budget:
                chosen_fields.append((f, rem))
                remaining_budget -= rem
            # else skip this field (cannot fully protect it with remaining budget)

        # If nothing chosen, we're done
        if not chosen_fields:
            return

        # Helper to compute field center
        def field_center(field):
            cx = (getattr(field, "left", 0) + getattr(field, "right", 0)) / 2.0
            cy = (getattr(field, "top", 0) + getattr(field, "bottom", 0)) / 2.0
            return cx, cy

        # Allocate spare drones to chosen fields, prioritizing closer drones
        # Note: we re-check distances using current location of drones
        for (f, rem) in chosen_fields:
            cx, cy = field_center(f)
            # sort remaining spare drones by distance to this field
            spare_drones.sort(key=lambda d: self._dist2(d, cx, cy))
            to_take = min(rem, len(spare_drones))
            group_name = f"protecting {f.id}"
            for i in range(to_take):
                d = spare_drones[i]
                environment.assign_group(d, group_name)
            # remove allocated drones from spare list
            spare_drones = spare_drones[to_take:]

        # Any remaining spare drones stay idle (already assigned to "idle" at the start)

    @staticmethod
    def _dist2(drone, cx, cy):
        loc = getattr(drone, "location", None)
        if loc is None:
            return float("inf")
        dx = getattr(loc, "x", 0.0) - cx
        dy = getattr(loc, "y", 0.0) - cy
        return dx*dx + dy*dy