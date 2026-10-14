

Looking at the failure, the issue is **partial protection coverage** (0.65 average means many fields are only partially covered). The constraint says: *"Prefer fully protecting fewer fields to partially protecting many fields."* My previous code kept drones on fields that couldn't reach full protection, creating partial coverage.

**Fix:** Never partially protect a field. If we cannot assign exactly `drones_for_full_protection` drones to a field, assign **zero** drones to it. Drones that were on an under-protected field get released to idle. Only the top-threat field is guaranteed full protection; secondary fields are fully protected only if enough drones exist.

```python
import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _dist_to_field(self, drone, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return math.sqrt((drone.location.x - cx) ** 2 + (drone.location.y - cy) ** 2)

    def assign_drones(self, components, environment, group_ids, step: int):
        active_fields = [f for f in environment.fields if f.threat_level > 0]
        active_fields.sort(key=lambda f: f.threat_level, reverse=True)

        if not active_fields:
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        active_field_ids = set(f.id for f in active_fields)

        # Track which drones are currently on which active field (for stability)
        drone_on_field = {}
        for comp in components:
            if comp.state in ("protecting", "moving_to_field") and comp.target_id in active_field_ids:
                drone_on_field[id(comp)] = comp.target_id
            else:
                drone_on_field[id(comp)] = None

        # All drones start unassigned; we will greedily pick for each field
        unassigned = list(components)
        assignments = {}  # field_id -> [drones]

        # ---- Top threat field: ALWAYS fully protect with closest drones ----
        top_field = active_fields[0]
        top_needed = top_field.drones_for_full_protection
        unassigned.sort(key=lambda d: self._dist_to_field(d, top_field))
        top_take = unassigned[:min(top_needed, len(unassigned))]
        assignments[top_field.id] = top_take
        taken = set(id(d) for d in top_take)
        unassigned = [d for d in unassigned if id(d) not in taken]

        # ---- Remaining fields: only assign if FULL protection is achievable ----
        for field in active_fields[1:]:
            needed = field.drones_for_full_protection
            if needed <= 0:
                assignments[field.id] = []
                continue

            # Drones already on this field (not stolen by top field)
            already_on = [d for d in unassigned if drone_on_field[id(d)] == field.id]

            if len(already_on) >= needed:
                # Keep the closest 'needed' of those already here; excess goes back
                already_on.sort(key=lambda d: self._dist_to_field(d, field))
                keep = already_on[:needed]
                assignments[field.id] = keep
                for d in keep:
                    taken.add(id(d))
                unassigned = [d for d in unassigned if id(d) not in taken]
            else:
                # Need to top up – can we reach full protection?
                gap = needed - len(already_on)
                other_avail = [d for d in unassigned if drone_on_field[id(d)] != field.id]
                if len(other_avail) >= gap:
                    other_avail.sort(key=lambda d: self._dist_to_field(d, field))
                    to_add = other_avail[:gap]
                    chosen = already_on + to_add
                    assignments[field.id] = chosen
                    for d in chosen:
                        taken.add(id(d))
                    unassigned = [d for d in unassigned if id(d) not in taken]
                else:
                    # Cannot fully protect -> assign ZERO (no partial protection)
                    assignments[field.id] = []

        # ---- Execute assignments ----
        drone_assignment = {}  # id(comp) -> field_id or None
        for fid, drones in assignments.items():
            for d in drones:
                drone_assignment[id(d)] = fid

        for comp in components:
            fid = drone_assignment.get(id(comp))
            if fid is not None:
                group_name = f"protecting {fid}"
                if group_name in group_ids:
                    environment.assign_group(comp, group_name)
                else:
                    environment.assign_group(comp, "idle")
            else:
                environment.assign_group(comp, "idle")
```

Key changes from the previous version:
1. **Removed Step 3** that filled partial gaps to meet the "half active" quota — that was creating the 0.65 coverage.
2. **Strict full-protection-or-nothing**: if a secondary field can't reach `drones_for_full_protection`, it gets 0 drones.
3. **Drones already on a field are preferred** for that field (stability), but only if the field can be fully protected.
4. Every field that has drones assigned has exactly the right number for full protection → 100% coverage on all protected fields.