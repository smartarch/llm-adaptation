import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):

    TRANSIT_PENALTY = 0.15  # minimum advantage needed to justify moving a drone

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._threat_history = defaultdict(list)  # field_id -> recent threat values
        self._drone_field = {}  # drone_id -> field_id it was last assigned to

    def _dist(self, loc, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return math.sqrt((loc.x - cx) ** 2 + (loc.y - cy) ** 2)

    def _urgency(self, field):
        """Urgency = current threat weighted by rate of increase (momentum)."""
        hist = self._threat_history[field.id]
        if len(hist) >= 2:
            # Rate of change: how fast threat is growing
            delta = hist[-1] - hist[-2]
            # Momentum: positive delta means threat is rising (urgent)
            momentum = max(0, delta) * 2.0
        else:
            momentum = 0
        return field.threat_level + momentum

    def assign_drones(self, components, environment, group_ids, step: int):
        field_by_id = {f.id: f for f in environment.fields}

        # --- Update threat history ---
        for field in environment.fields:
            self._threat_history[field.id].append(field.threat_level)
            if len(self._threat_history[field.id]) > 5:
                self._threat_history[field.id] = self._threat_history[field.id][-5:]

        # --- Compute urgency for all fields ---
        urgency = {}
        for field in environment.fields:
            urgency[field.id] = self._urgency(field)

        # --- Sort active fields by urgency (descending) ---
        active_fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: urgency[f.id], reverse=True
        )
        active_ids = set(f.id for f in active_fields)

        # --- Classify drones: who is currently "assigned" where ---
        # Use the previous assignment tracking, but validate against reality
        assigned_to = defaultdict(list)
        truly_free = []

        for drone in components:
            did = id(drone)
            tid = drone.target_id

            if tid is not None and tid in field_by_id:
                fld = field_by_id[tid]
                if fld.threat_level > 0 or self._threat_history.get(tid, [0])[-1] > 0.01:
                    # Field is active or was very recently active - drone stays here for now
                    assigned_to[tid].append(drone)
                else:
                    # Field is dead - drone is available
                    truly_free.append(drone)
            else:
                truly_free.append(drone)

        # --- Release over-protected drones ---
        for fid in list(assigned_to.keys()):
            if fid not in field_by_id:
                truly_free.extend(assigned_to[fid])
                del assigned_to[fid]
                continue
            fld = field_by_id[fid]
            need = fld.drones_for_full_protection
            drones_here = assigned_to[fid]
            if len(drones_here) > need:
                # Release excess (prefer releasing those still in transit)
                drones_here.sort(key=lambda d: 0 if d.state == "protecting" else 1)
                excess = drones_here[need:]
                assigned_to[fid] = drones_here[:need]
                truly_free.extend(excess)

        # --- Build assignment: start with committed ---
        drone_assignment = {}  # drone_id -> field_id
        for fid, drones in assigned_to.items():
            for d in drones:
                drone_assignment[id(d)] = fid

        # --- Phase 1: Full protection greedy (highest urgency first) ---
        # Available pool: free drones + drones whose current field is less urgent
        pool = list(truly_free)

        for field in active_fields:
            fid = field.id
            need = field.drones_for_full_protection
            have = len(assigned_to.get(fid, [])) + sum(
                1 for d in components if drone_assignment.get(id(d)) == fid and d not in assigned_to.get(fid, [])
            )
            deficit = need - have
            if deficit <= 0:
                continue

            # Sort pool by distance to this field
            pool.sort(key=lambda d: self._dist(d.location, field))
            take = pool[:deficit]
            pool = pool[deficit:]
            for d in take:
                drone_assignment[id(d)] = fid
                assigned_to[fid].append(d)

        # --- Phase 2: Consider pulling drones from lower-urgency fields to help higher ones ---
        # Only if the urgency gap justifies transit cost
        for field in active_fields:
            fid = field.id
            need = field.drones_for_full_protection
            have = len(assigned_to.get(fid, []))
            deficit = need - have
            if deficit <= 0:
                continue

            my_urgency = urgency[fid]

            # Find donors from lower-urgency active fields (over-satisfied or equal urgency is fine)
            for other_field in reversed(active_fields):  # lowest urgency first
                if deficit <= 0:
                    break
                ofid = other_field.id
                if ofid == fid:
                    continue
                other_urgency = urgency[ofid]
                # Only pull if my urgency significantly exceeds theirs
                if my_urgency - other_urgency < self.TRANSIT_PENALTY:
                    break  # fields are sorted, so all remaining are even lower but close

                other_have = len(assigned_to.get(ofid, []))
                other_need = other_field.drones_for_full_protection
                if other_have <= other_need - 1:
                    continue  # they need their drones too (keep at least need-1)

                # Pull the closest drone from other field
                donors = [d for d in assigned_to.get(ofid, []) if drone_assignment.get(id(d)) == ofid]
                if not donors:
                    continue
                donors.sort(key=lambda d: self._dist(d.location, field))
                # Pull one at a time
                d = donors[0]
                assigned_to[ofid].remove(d)
                drone_assignment[id(d)] = fid
                assigned_to[fid].append(d)
                deficit -= 1

        # --- Phase 3: Partial protection with remaining pool ---
        for field in active_fields:
            if not pool:
                break
            fid = field.id
            have = len(assigned_to.get(fid, []))
            need = field.drones_for_full_protection
            deficit = need - have
            if deficit <= 0:
                continue
            pool.sort(key=lambda d: self._dist(d.location, field))
            take = pool[:deficit]
            pool = pool[deficit:]
            for d in take:
                drone_assignment[id(d)] = fid
                assigned_to[fid].append(d)

        # --- Phase 4: Extra drones - give to field with highest unmet partial need ---
        if pool:
            for d in pool:
                best_fid = None
                best_score = -1
                for field in active_fields:
                    fid = field.id
                    have = len(assigned_to.get(fid, []))
                    need = field.drones_for_full_protection
                    if have >= need:
                        continue
                    # Score: urgency × benefit of one more drone
                    remaining_need = need - have
                    score = urgency[fid] * (1.0 / remaining_need)  # more marginal benefit when close to full
                    if score > best_score:
                        best_score = score
                        best_fid = fid
                if best_fid:
                    drone_assignment[id(d)] = best_fid
                    assigned_to[best_fid].append(d)
                # else stays idle

        # --- Execute assignments ---
        for drone in components:
            did = id(drone)
            fid = drone_assignment.get(did)
            if fid is not None:
                gn = f"protecting {fid}"
                if gn in group_ids:
                    environment.assign_group(drone, gn)
                else:
                    environment.assign_group(drone, "idle")
            else:
                environment.assign_group(drone, "idle")
            self._drone_field[did] = fid