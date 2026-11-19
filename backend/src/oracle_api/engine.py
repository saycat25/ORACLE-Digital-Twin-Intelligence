from collections import deque

from oracle_api.schemas import ImpactedNode


def analyze_impact(nodes: list[dict], edges: list[dict], failed_node_id: int,
                   failure_mode: str) -> list[ImpactedNode]:
    """Return upstream dependents affected by a failed dependency.

    Edge direction is consumer -> dependency. Starting at the failed node, the
    engine traverses reverse edges to find consumers. Impact decays by hop and
    is weighted by each traversed dependency's criticality and node criticality.
    """
    by_id = {node["id"]: node for node in nodes}
    if failed_node_id not in by_id:
        raise ValueError("Failed node does not exist.")

    reverse: dict[int, list[tuple[int, float]]] = {}
    for edge in edges:
        reverse.setdefault(edge["target_id"], []).append(
            (edge["source_id"], edge["criticality"])
        )

    queue = deque([(failed_node_id, 0, [failed_node_id], 1.0)])
    best: dict[int, tuple[float, int, list[int]]] = {}
    while queue:
        current, hops, path, score = queue.popleft()
        for consumer_id, edge_criticality in sorted(reverse.get(current, [])):
            if consumer_id in path:
                continue
            consumer = by_id[consumer_id]
            next_hops = hops + 1
            mode_factor = 1.0 if failure_mode == "unavailable" else 0.55
            next_score = score * edge_criticality * consumer["criticality"] * 0.8 * mode_factor
            previous = best.get(consumer_id)
            if previous is None or next_score > previous[0]:
                next_path = path + [consumer_id]
                best[consumer_id] = (next_score, next_hops, next_path)
                queue.append((consumer_id, next_hops, next_path, next_score))

    results = [
        ImpactedNode(
            node_id=node_id,
            name=by_id[node_id]["name"],
            hop_distance=hops,
            impact_score=round(min(score, 1.0), 4),
            path_to_failure=list(reversed(path)),
        )
        for node_id, (score, hops, path) in best.items()
    ]
    return sorted(results, key=lambda item: (-item.impact_score, item.hop_distance, item.name))



def assess_capacity(nodes: list[dict], demand_multiplier: float = 1.0) -> list[dict]:
    """Project component load against declared capacity without inferring failover."""
    if demand_multiplier <= 0 or demand_multiplier > 5:
        raise ValueError("Demand multiplier must be greater than 0 and at most 5.")

    results = []
    for node in nodes:
        capacity = float(node["capacity_units"])
        current_load = float(node["current_load_units"])
        if capacity <= 0 or current_load < 0:
            raise ValueError("Node capacity must be positive and load cannot be negative.")
        projected_load = current_load * demand_multiplier
        utilization = projected_load / capacity
        state = "over_capacity" if utilization >= 1.0 else (
            "warning" if utilization >= 0.8 else "normal"
        )
        results.append(
            {
                "node_id": node["id"],
                "name": node["name"],
                "kind": node["kind"],
                "capacity_units": round(capacity, 4),
                "current_load_units": round(current_load, 4),
                "projected_load_units": round(projected_load, 4),
                "utilization_ratio": round(utilization, 4),
                "headroom_units": round(max(0.0, capacity - projected_load), 4),
                "status": state,
            }
        )
    return sorted(
        results,
        key=lambda item: (
            {"over_capacity": 0, "warning": 1, "normal": 2}[item["status"]],
            -item["utilization_ratio"],
            item["name"],
        ),
    )
