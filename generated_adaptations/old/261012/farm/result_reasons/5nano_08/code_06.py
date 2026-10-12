from math import inf
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Remember previous assignment (drone -> group_id) to help persistence
        self.prev_group = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to compute field center
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Helper to compute squared distance between a drone and a point
        def dist2_to_point(drone, pt):
            loc = getattr(drone, 'location', None)
            if loc is None:
                return inf
            x = getattr(loc, 'x', None)
            y = getattr(loc, 'y', None)
            if x is None or y is None:
                return inf
            dx = x - pt[0]
            dy = y - pt[1]
            return dx * dx + dy * dy

        # Gather threat-enabled fields
        fields = list(environment.fields)
        threatened_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If no threatened fields, idle all drones
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
                self.prev_group[d] = "idle"
            return

        # Identify top (most threatened) field
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"

        # Validate group name
        if top_group not in group_ids:
            # Fall back to idle if the group isn't valid
            for d in components:
                environment.assign_group(d, "idle")
                self.prev_group[d] = "idle"
            return

        top_center = field_center(top_field)
        capacity_top = getattr(top_field, 'drones_for_full_protection', len(components))

        # Build top drones with bias
        candidates = []
        for d in components:
            dist = dist2_to_point(d, top_center)
            prev_bonus = 1.0 if self.prev_group.get(d) == top_group else 0.0
            moving_to_top = (getattr(d, 'state', None) == "moving_to_field" and getattr(d, 'target_id', None) == top_field.id)
            # Score: we want high score; closer (smaller dist) yields higher score
            score = -dist  + (1000.0 * prev_bonus) + (800.0 if moving_to_top else 0.0)
            candidates.append((score, d, dist, prev_bonus, moving_to_top))

        candidates.sort(key=lambda x: x[0], reverse=True)
        top_drones = [d for (_, d, _, _, _) in candidates[:capacity_top]]

        # If we don't have enough due to some reason, fill from remaining by distance
        if len(top_drones) < capacity_top:
            seen = set(top_drones)
            rest = [d for d in components if d not in seen]
            rest.sort(key=lambda d: dist2_to_point(d, top_center))
            need = capacity_top - len(top_drones)
            top_drones.extend(rest[:need])

        # Assign top drones
        final_group = {}
        for d in top_drones:
            final_group[d] = top_group

        # Remaining drones pool
        remaining = [d for d in components if d not in top_drones]

        # Other threatened fields
        other_fields = [f for f in threatened_fields if f.id != top_field.id]
        other_fields.sort(key=lambda f: f.threat_level, reverse=True)

        for f in other_fields:
            g = f"protecting {f.id}"
            if g not in group_ids:
                continue
            center = field_center(f)
            capacity = getattr(f, 'drones_for_full_protection', len(components))

            # Current drones protecting this field in our final_group
            current = [d for d in components if final_group.get(d) == g]
            if len(current) > capacity:
                current.sort(key=lambda d: dist2_to_point(d, center))
                for d in current[capacity:]:
                    final_group[d] = "idle"
                current = current[:capacity]

            # Fill up to capacity with best candidates from 'remaining'
            if len(current) < capacity:
                need = capacity - len(current)
                # prefer drones not already allocated elsewhere except possibly to maintain previous
                pool = [d for d in remaining if d not in final_group]
                pool.sort(key=lambda d: (dist2_to_point(d, center),
                                         -1 if self.prev_group.get(d) == g else 0))
                chosen = pool[:need]
                for d in chosen:
                    final_group[d] = g
                # remove chosen from remaining
                for d in chosen:
                    if d in remaining:
                        remaining.remove(d)

        # Idle remaining
        for d in remaining:
            final_group[d] = "idle"

        # Enforce minimum protection: ensure at least half drones are protecting
        protected = [d for d in components if final_group.get(d) != "idle"]
        if len(protected) < len(components) // 2:
            # try to move idle drones to top field up to capacity
            top_current = [d for d in components if final_group.get(d) == top_group]
            can_add = max(0, capacity_top - len(top_current))
            if can_add > 0:
                idle_candidates = [d for d in components if final_group.get(d) == "idle"]
                idle_candidates.sort(key=lambda d: dist2_to_point(d, top_center))
                for d in idle_candidates[:can_add]:
                    final_group[d] = top_group

        # Assign to environment and update memory
        for d in components:
            grp = final_group.get(d, "idle")
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(d, grp)
            self.prev_group[d] = grp