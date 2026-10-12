from math import ceil, hypot
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Track last assigned group per drone (keyed by drone unique key) and stability count
        self.prev_group = {}
        self.stable_counts = {}
        self.last_step = -1

    def _comp_key(self, component):
        # Try common id/name attributes, otherwise use Python id
        for attr in ("id", "name", "uid"):
            if hasattr(component, attr):
                val = getattr(component, attr)
                if val is not None:
                    return f"{attr}:{val}"
        return f"pyid:{id(component)}"

    def assign_drones(self, components, environment, group_ids, step: int):
        # Ensure we have tracking entries for every component
        comp_key_map = {}
        for c in components:
            k = self._comp_key(c)
            comp_key_map[k] = c
            if k not in self.prev_group:
                # Initialize as idle
                self.prev_group[k] = "idle"
                self.stable_counts[k] = 0

        # Build list of threatened fields (threat_level > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # No threats: assign all drones to idle
            for c in components:
                environment.assign_group(c, "idle")
                k = self._comp_key(c)
                # update tracking
                if self.prev_group.get(k) == "idle":
                    self.stable_counts[k] = self.stable_counts.get(k, 0) + 1
                else:
                    self.stable_counts[k] = 1
                self.prev_group[k] = "idle"
            return

        # Sort fields by descending threat_level
        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Precompute field centers
        field_centers = {}
        for f in threatened_fields:
            cx = (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0
            cy = (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0
            field_centers[f.id] = (cx, cy)

        # Precompute drone distances to each field center and current state/group
        drone_info = {}
        for c in components:
            k = self._comp_key(c)
            lx = getattr(c.location, "x", 0)
            ly = getattr(c.location, "y", 0)
            drone_info[k] = {
                "component": c,
                "loc": (lx, ly),
                "state": getattr(c, "state", None),
                "target_id": getattr(c, "target_id", None),
                "prev_group": self.prev_group.get(k, "idle"),
                "stable": self.stable_counts.get(k, 0)
            }

        total_drones = len(components)
        half_needed = ceil(total_drones / 2)

        # Determine which fields to fully protect.
        # Always include the top field. Then include further fields while we have drones
        # and want to reach at least half_needed protected drones.
        plan_fields = []  # list of (field, required_drones)
        remaining_drones_slots = total_drones
        # but we don't want to allocate more than necessary; we'll select drones per field exactly
        for idx, f in enumerate(threatened_fields):
            required = int(getattr(f, "drones_for_full_protection", 0))
            if required <= 0:
                continue
            if idx == 0:
                # always include top field
                plan_fields.append((f, required))
                remaining_drones_slots -= required
            else:
                # add this field only if we still have enough unallocated drones
                # and we need more protected drones to reach half_needed
                current_allocated = sum(req for (_, req) in plan_fields)
                if current_allocated < half_needed and required <= remaining_drones_slots:
                    plan_fields.append((f, required))
                    remaining_drones_slots -= required
                else:
                    # stop adding fields if we either reached half or we can't fit this field
                    continue

        # Select drones for each planned field
        assigned = {}  # comp_key -> group_name
        unallocated_keys = set(drone_info.keys())

        # Helper to compute distance
        def dist(k, field_id):
            cx, cy = field_centers[field_id]
            lx, ly = drone_info[k]["loc"]
            return hypot(lx - cx, ly - cy)

        # Iterate over plan_fields; for the most threatened field (first), prioritize distance
        for i, (field, required) in enumerate(plan_fields):
            group_name = f"protecting {field.id}"
            if group_name not in group_ids:
                # Skip if group not available
                continue

            candidates = list(unallocated_keys)

            # For top field: primarily choose closest drones, but tie-break prefer those already in that group
            if i == 0:
                # build list of (distance, already_assigned_penalty, -stable, key)
                ranked = []
                for k in candidates:
                    d = dist(k, field.id)
                    already = 0 if (drone_info[k]["prev_group"] == group_name or drone_info[k]["target_id"] == field.id) else 1
                    # prefer higher stable counts for tie-breaking (so negative to sort ascending)
                    ranked.append((d, already, -drone_info[k]["stable"], k))
                ranked.sort()
                chosen = [k for (_, _, _, k) in ranked[:required]]
            else:
                # For other fields: prefer keeping drones already assigned there (stability), then pick movers with small stable counts and decent distance
                keepers = [k for k in candidates if drone_info[k]["prev_group"] == group_name or drone_info[k]["target_id"] == field.id]
                # sort keepers by stable desc then distance asc
                keepers.sort(key=lambda k: (-drone_info[k]["stable"], dist(k, field.id)))
                chosen = []
                for k in keepers:
                    if len(chosen) >= required:
                        break
                    chosen.append(k)
                if len(chosen) < required:
                    # fill rest from remaining candidates excluding already chosen
                    remaining_cands = [k for k in candidates if k not in chosen]
                    # prefer to move drones with lower stable counts (less churn), then closer distance
                    remaining_cands.sort(key=lambda k: (drone_info[k]["stable"], dist(k, field.id)))
                    need = required - len(chosen)
                    chosen.extend(remaining_cands[:need])

            # Assign chosen to this field
            for k in chosen:
                assigned[k] = group_name
                if k in unallocated_keys:
                    unallocated_keys.remove(k)

        # All remaining drones go to idle
        for k in list(unallocated_keys):
            assigned[k] = "idle"

        # Now apply assignments (explicitly assign each component to a group) and update tracking
        for k, group in assigned.items():
            comp = drone_info[k]["component"]
            # safety: ensure group exists in group_ids; if not, fallback to "idle"
            if group not in group_ids:
                group = "idle"
            environment.assign_group(comp, group)

        # Update prev_group and stable_counts based on these assignments
        for k, group in assigned.items():
            prev = self.prev_group.get(k)
            if prev == group:
                # continue stability
                self.stable_counts[k] = self.stable_counts.get(k, 0) + 1
            else:
                # reset count to 1 (we count current step)
                self.stable_counts[k] = 1
            self.prev_group[k] = group

        # End of assign_drones