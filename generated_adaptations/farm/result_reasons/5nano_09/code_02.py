from generated_adaptations.base_classes.farm import FarmAdaptation
import abc
from math import hypot

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Persisted memory to reduce churn: map drone -> field_id (str) it protected previously
        # None means idle or no field memory
        self.prev_assignments = {}

    def _center_of_field(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return (cx, cy)

    def _dist(self, drone, field):
        cx, cy = self._center_of_field(field)
        dx = getattr(drone.location, "x", 0.0) - cx
        dy = getattr(drone.location, "y", 0.0) - cy
        return (dx*dx + dy*dy) ** 0.5

    def _drones_protecting(self, drones, field):
        if field is None:
            return []
        return [
            d for d in drones
            if getattr(d, "state", None) in ("protecting", "moving_to_field")
            and getattr(d, "target_id", None) == field.id
        ]

    def assign_drones(self, components, environment, group_ids, step: int):
        # List of fields with positive threat
        fields = list(environment.fields)
        protectable = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If nothing is threatened, idle all drones
        if not protectable:
            for d in components:
                environment.assign_group(d, "idle")
            self.prev_assignments = {}
            return

        # Sort protectable fields by threat level (desc). Tie-breaker by drones_for_full_protection (desc)
        protectable.sort(
            key=lambda f: (f.threat_level, getattr(f, "drones_for_full_protection", 0)),
            reverse=True
        )

        # Ensure groups exist for each threatened field
        # (We rely on the environment's group_ids to contain "protecting {field.id}" for each threatened field.)
        # Build mapping: field_id -> group_name
        field_to_group = {f.id: f"protecting {f.id}" for f in protectable}

        # Compute current protection per field
        current_protection = {}
        for f in protectable:
            current_protection[f.id] = len(self._drones_protecting(components, f))

        # Determine top field (most threatened)
        top_field = protectable[0]
        top_group = field_to_group[top_field.id]
        top_desired = getattr(top_field, "drones_for_full_protection", 0)

        # Helper: mark which drones are assigned to top/second fields this step
        assigned_to = {d: None for d in components}  # maps drone -> field_id or None

        # Step 1: Top field allocation
        top_current = self._drones_protecting(components, top_field)

        # We want to keep as many as possible up to top_desired, prioritizing closer drones
        # If too many current protectors, drop the farthest ones
        if len(top_current) > top_desired:
            # sort by distance to top field (descending to drop farthest)
            top_current_sorted = sorted(top_current, key=lambda d: self._dist(d, top_field), reverse=True)
            to_drop = top_current_sorted[top_desired:]
            for d in to_drop:
                environment.assign_group(d, "idle")
                assigned_to[d] = None
            top_current = top_current_sorted[:top_desired]

        # Now we may still need more drones to reach top_desired
        for d in top_current:
            environment.assign_group(d, top_group)
            assigned_to[d] = top_field.id  # remember protection target

        # Collect drones not yet assigned to top_field
        remaining_drones = [d for d in components if assigned_to.get(d) != top_field.id]

        # If we need more to reach full protection, pick closest from remaining
        if len(top_current) < top_desired:
            needed = top_desired - len(top_current)
            candidates = []
            for d in remaining_drones:
                # distance to top field center
                dist = self._dist(d, top_field)
                candidates.append((dist, d))
            candidates.sort(key=lambda x: x[0])
            for dist, d in candidates[:needed]:
                environment.assign_group(d, top_group)
                assigned_to[d] = top_field.id
            # Update remaining_drones after allocation
            remaining_drones = [d for d in components if assigned_to.get(d) != top_field.id]

        # Step 1b: If there are more protectors than needed (due to previous step), ensure we didn't exceed
        # (already handled by dropping farthest earlier)

        # Step 2: Allocate to subsequent fields (second, third, ...) if possible
        # We'll try to fully protect as many of the next-threatened fields as possible with remaining drones
        for field in protectable[1:]:
            group_name = field_to_group[field.id]
            desired = getattr(field, "drones_for_full_protection", 0)
            current = self._drones_protecting(components, field)
            # Count how many currently protect this field
            current_ids = set(d for d in current)
            # If current > desired, drop farthest among current
            if len(current) > desired:
                # sort by distance to field center, farthest first
                current_sorted = sorted(current, key=lambda d: self._dist(d, field), reverse=True)
                to_drop = current_sorted[desired:]
                for d in to_drop:
                    environment.assign_group(d, "idle")
                    assigned_to[d] = None
                current = current_sorted[:desired]
                current_ids = set(d for d in current)

            # Assign gaps to reach desired
            if len(current) < desired:
                needed = desired - len(current)
                # candidates are drones not already assigned to a field
                available = [d for d in remaining_drones if d not in current_ids]
                # sort by distance to this field
                cand_list = [(self._dist(d, field), d) for d in available]
                cand_list.sort(key=lambda x: x[0])
                for dist, d in cand_list[:needed]:
                    environment.assign_group(d, group_name)
                    assigned_to[d] = field.id
                # Update remaining_drones
                remaining_drones = [d for d in remaining_drones if d not in {c[1] for c in cand_list[:needed]}]

            # If after this still fewer than half drones are protecting, we may re-distribute idle drones to this field
            # (handled later in a separate pass to ensure "at least half" guidance)

        # Step 3: If still not meeting the "at least half protecting" guideline, allocate some idle drones to the most threatened fields
        total_drones = len(components)
        protecting_now = [d for d in components if assigned_to.get(d) is not None]
        if len(protecting_now) < total_drones * 0.5:
            # We'll allocate from currently idle drones (not assigned to any field this step)
            idle_drones = [d for d in components if assigned_to.get(d) is None]
            # Prefer drones closest to the top field, then to next best field
            # Build a prioritized list of fields to fill
            fields_order = protectable  # already sorted by threat
            for d in idle_drones:
                if len(protecting_now) >= total_drones * 0.5:
                    break
                # choose the best field to protect among those that are not yet at full protection
                chosen = None
                for f in fields_order:
                    current = self._drones_protecting(components, f)
                    if len(current) < getattr(f, "drones_for_full_protection", 0):
                        chosen = f
                        break
                if chosen is None:
                    # If all at full protection, assign to idle
                    continue
                group_name = field_to_group[chosen.id]
                environment.assign_group(d, group_name)
                assigned_to[d] = chosen.id
                protecting_now.append(d)

        # Step 4: If there are drones still not assigned (should be idle)
        for d in components:
            if assigned_to.get(d) is None:
                environment.assign_group(d, "idle")

        # Persist memory to reduce churn: remember which field each drone protected this step
        new_memory = {}
        for d in components:
            grp = None
            # Determine the field this drone is protecting now (if any)
            if getattr(d, "state", None) in ("protecting", "moving_to_field"):
                tgt = getattr(d, "target_id", None)
                if tgt is not None:
                    grp = tgt
            new_memory[d] = grp  # could be None if idle

        self.prev_assignments = new_memory