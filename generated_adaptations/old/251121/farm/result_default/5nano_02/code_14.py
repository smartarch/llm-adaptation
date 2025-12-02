import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _center_of_field(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _safe_group(self, name, group_ids):
        if name in group_ids:
            return name
        if "idle" in group_ids:
            return "idle"
        return group_ids[0] if group_ids else "idle"

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Allocation strategy:
        - Forcefully protect the top-threat field if possible.
        - Use a 0/1 knapsack (on remaining capacity) to decide additional fields to fully protect,
          maximizing total threat value.
        - Allocate drones to the chosen fields starting from current protectors, filling with closest idle drones.
        - All drones end up in a concrete group (idle or protecting a field).
        """
        # Gather fields with positive threat and positive drones_for_full_protection
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0 and int(getattr(f, "drones_for_full_protection", 0)) > 0]

        total_drones = len(components)
        if not fields:
            # Nothing to protect
            for d in components:
                environment.assign_group(d, self._safe_group("idle", group_ids))
            return

        # Identify the top-threat field
        top_field = max(fields, key=lambda f: getattr(f, "threat_level", 0))
        w_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Prepare knapsack: we will force-top if possible
        # Build candidate list excluding the top field
        candidates = []
        for f in fields:
            if f is top_field:
                continue
            w = int(getattr(f, "drones_for_full_protection", 0))
            v = float(getattr(f, "threat_level", 0.0))
            if w > 0:
                candidates.append((f, w, v))

        # DP for subset of candidates with capacity cap = total_drones - w_top (if top is feasible)
        chosen_fields = set()

        if w_top <= total_drones:
            cap = total_drones - w_top
            # 0/1 knapsack DP: items are candidates, weight=w, value=v
            n = len(candidates)
            # dp[cap] = best value; par tracks (prev_cap, item_index)
            dp = [-1.0] * (cap + 1)
            dp[0] = 0.0
            par = [(-1, -1)] * (cap + 1)

            for i, (fld, w, val) in enumerate(candidates):
                for c in range(cap, w - 1, -1):
                    if dp[c - w] >= 0 and dp[c - w] + val > dp[c]:
                        dp[c] = dp[c - w] + val
                        par[c] = (c - w, i)

            # pick best cap
            best_cap = max(range(cap + 1), key=lambda c: dp[c])
            if dp[best_cap] > -1e-9:
                # reconstruct
                c = best_cap
                while c != 0 and par[c] != (-1, -1):
                    prev, idx = par[c]
                    fld, w, val = candidates[idx]
                    chosen_fields.add(fld)
                    c = prev
        else:
            # Not enough drones to even cover the top field
            cap = -1  # indicate we cannot force top
            chosen_fields = set()

        # Final set of fields we will fully protect
        top_included = (w_top <= total_drones)
        if top_included:
            final_fields = {top_field}.union(chosen_fields)
        else:
            # Top cannot be protected; fall back to other fields only
            final_fields = set(chosen_fields)

        # Map field -> required drones (weight)
        req_by_field = {}
        for f in final_fields:
            w = int(getattr(f, "drones_for_full_protection", 0))
            req_by_field[f] = w

        # Track drones currently protecting any of the final fields
        assigned = set()
        current_by_field = {f.id: [] for f in final_fields}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                fid = getattr(d, "target_id", None)
                # If this drone protects one of the selected fields, keep it assigned to that group
                if any(fid == f.id for f in final_fields):
                    grp = self._safe_group(f"protecting {fid}", group_ids)
                    environment.assign_group(d, grp)
                    current_by_field.get(fid, []).append(d)
                    assigned.add(d)

        # If top field is included but some of its current protectors are not yet assigned to the exact group,
        # re-assign them above in the loop; they are now part of assigned for their field.

        # Build pool of drones available to fill remaining needs
        pool = [d for d in components if d not in assigned]

        # For each field in final_fields, fill to full protection using closest drones from pool
        # Sort fields by threat level high-to-low to prioritize higher threats
        for f in sorted(final_fields, key=lambda ff: getattr(ff, "threat_level", 0), reverse=True):
            needed = max(0, int(getattr(f, "drones_for_full_protection", 0)) - len(current_by_field.get(f.id, [])))
            if needed <= 0:
                continue
            center = self._center_of_field(f)

            def dist(d):
                loc = getattr(d, "location", None)
                if loc is not None and hasattr(loc, "x") and hasattr(loc, "y"):
                    dx = loc.x - center[0]
                    dy = loc.y - center[1]
                    return (dx * dx + dy * dy) ** 0.5
                return float("inf")

            pool.sort(key=dist)
            take = min(needed, len(pool))
            grp = self._safe_group(f"protecting {f.id}", group_ids)
            for i in range(take):
                d = pool[i]
                environment.assign_group(d, grp)
                assigned.add(d)
            pool = [d for d in pool if d not in assigned]

        # Step: assign any remaining drones to idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, self._safe_group("idle", group_ids))