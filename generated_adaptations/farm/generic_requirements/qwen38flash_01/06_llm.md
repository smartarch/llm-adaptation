

## Analysis of the Regression

The 135.0 score indicates my "stickiness" approach was harmful — it caused **stale assignments** where drones stayed on low-threat fields while threats shifted. The simulation requires **responsiveness** to changing bird preferences.

## New Strategy

Key principles for this improved version:
1. **Fresh reassignment every step** (no stale state locks), but with a **proximity bonus** for drones already at/near a field to reduce switching churn.
2. **Virtual position for moving drones**: Drones in transit should be counted based on where they're heading, not where they currently are.
3. **Layered protection**: First protect the top-threat field fully, then cascade down — only if full protection is achievable.
4. **Reserve positioning**: Spare drones should cluster near the **second-most-threatened** field (a likely next target), rather than being scattered into useless partial protection everywhere.
5. **Switching-aware selection**: When choosing drones for a field, strongly prefer those already at that field, then those nearby, then idle. Never pull a drone that's actively protecting a still-critical field unless the top-threat field needs it.
6. **No partial protection unless idle > 50%**: Only assign "partial" drones if too many would otherwise be idle.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        num_drones = len(components)
        assignments = {}
        assigned_set = set()

        if num_drones == 0:
            return

        # Build field lookup
        field_by_id = {f.id: f for f in environment.fields}
        threatened = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level,
            reverse=True
        )

        if not threatened:
            for d in components:
                environment.assign_group(d, "idle")
            return

        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def effective_position(drone):
            """For moving drones, use the target location as their effective position."""
            if drone.state == "moving_to_field" and drone.target_id:
                target = field_by_id.get(drone.target_id)
                if target:
                    return field_center(target)
            return (drone.location.x, drone.location.y)

        def dist(drone, field):
            cx, cy = field_center(field)
            ex, ey = effective_position(drone)
            return math.sqrt((ex - cx) ** 2 + (ey - cy) ** 2)

        def group_for(fid):
            return f"protecting {fid}"

        def avail():
            return [d for d in components if id(d) not in assigned_set]

        def assign_drone(drone, gid):
            assignments[id(drone)] = gid
            assigned_set.add(id(drone))

        def pick_closest(field, count, pool):
            """Pick up to `count` drones from `pool` closest to `field`.
            Strong bonus for drones already targeting/protecting this field."""
            def sort_key(d):
                base = dist(d, field)
                bonus = 0
                if d.target_id == field.id:
                    bonus = -50  # Strongly prefer drones already heading/protecting this field
                elif d.state == "idle":
                    bonus = 5   # Slight penalty for idle (they need to fly the whole way)
                return base + bonus
            pool_sorted = sorted(pool, key=sort_key)
            return pool_sorted[:count]

        # === Pass 1: Mandatory full protection for the MOST threatened field ===
        top = threatened[0]
        need = top.drones_for_full_protection
        pool = avail()
        chosen = pick_closest(top, need, pool)
        gid = group_for(top.id)
        for d in chosen:
            assign_drone(d, gid)

        # === Pass 2: Greedy full protection of remaining threatened fields ===
        for field in threatened[1:]:
            need = field.drones_for_full_protection
            pool = avail()
            if len(pool) < need:
                break  # Can't fully protect; skip to avoid waste
            chosen = pick_closest(field, need, pool)
            if len(chosen) < need:
                break
            gid = group_for(field.id)
            for d in chosen:
                assign_drone(d, gid)

        # === Pass 3: Utilize spare drones to reduce idle count ===
        # Half the drones should be active. Partial protection helps a little.
        # But prefer clustering reserves near the 2nd-most-threatened field
        # over spreading them thin.
        protecting_count = len(assigned_set)
        target_active = max(num_drones // 2, num_drones - 2)  # Allow at most ~2 idle

        if protecting_count < target_active and threatened:
            # Try to partially protect the next threatened fields (highest threat first)
            # but only give them a small share and only if threat is meaningful
            for field in threatened[1:]:
                if len(assigned_set) >= target_active:
                    break
                if field.threat_level < 0.15:
                    break  # Low threat, not worth partial coverage
                pool = avail()
                if not pool:
                    break
                # Assign up to (need-1) drones for partial, but max 2 to avoid waste
                max_partial = min(2, field.drones_for_full_protection - 1, len(pool))
                if max_partial <= 0:
                    continue
                chosen = pick_closest(field, max_partial, pool)
                gid = group_for(field.id)
                for d in chosen:
                    assign_drone(d, gid)
                    if len(assigned_set) >= target_active:
                        break

        # === Pass 4: Any remaining drones → idle ===
        for d in components:
            if id(d) not in assigned_set:
                assign_drone(d, "idle")

        # === Apply ===
        for d in components:
            gid = assignments.get(id(d), "idle")
            if gid not in group_ids:
                gid = "idle"
            environment.assign_group(d, gid)
```