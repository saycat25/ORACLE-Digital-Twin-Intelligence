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
