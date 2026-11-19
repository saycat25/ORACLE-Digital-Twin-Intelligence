from oracle_api.engine import analyze_impact


def sample_graph():
    nodes = [
        {"id": 1, "name": "frontend", "criticality": 0.9},
        {"id": 2, "name": "api", "criticality": 0.95},
        {"id": 3, "name": "database", "criticality": 1.0},
        {"id": 4, "name": "unrelated", "criticality": 0.5},
    ]
    edges = [
        {"source_id": 1, "target_id": 2, "criticality": 0.9},
        {"source_id": 2, "target_id": 3, "criticality": 0.95},
    ]
    return nodes, edges


def test_failure_propagates_to_transitive_consumers():
    nodes, edges = sample_graph()
    result = analyze_impact(nodes, edges, 3, "unavailable")
    assert {item.node_id for item in result} == {1, 2}
    assert [2, 3] in [item.path_to_failure for item in result]
    assert [1, 2, 3] in [item.path_to_failure for item in result]


def test_unrelated_nodes_are_not_impacted():
    nodes, edges = sample_graph()
    result = analyze_impact(nodes, edges, 3, "unavailable")
    assert 4 not in {item.node_id for item in result}


def test_degraded_mode_has_lower_impact_than_unavailable():
    nodes, edges = sample_graph()
    unavailable = analyze_impact(nodes, edges, 3, "unavailable")
    degraded = analyze_impact(nodes, edges, 3, "degraded")
    assert degraded[0].impact_score < unavailable[0].impact_score


def test_missing_failed_node_is_rejected():
    nodes, edges = sample_graph()
    try:
        analyze_impact(nodes, edges, 999, "unavailable")
    except ValueError as exc:
        assert "does not exist" in str(exc)
    else:
        raise AssertionError("Expected ValueError")



def test_capacity_assessment_marks_warnings_and_over_capacity():
    from oracle_api.engine import assess_capacity

    result = assess_capacity(
        [
            {
                "id": 1,
                "name": "healthy",
                "kind": "service",
                "capacity_units": 100.0,
                "current_load_units": 40.0,
            },
            {
                "id": 2,
                "name": "warning",
                "kind": "database",
                "capacity_units": 100.0,
                "current_load_units": 80.0,
            },
            {
                "id": 3,
                "name": "overloaded",
                "kind": "worker",
                "capacity_units": 100.0,
                "current_load_units": 95.0,
            },
        ],
        demand_multiplier=1.1,
    )
    by_name = {item["name"]: item for item in result}
    assert by_name["healthy"]["status"] == "normal"
    assert by_name["warning"]["status"] == "warning"
    assert by_name["overloaded"]["status"] == "over_capacity"
    assert by_name["overloaded"]["headroom_units"] == 0.0
    assert result[0]["name"] == "overloaded"


def test_capacity_assessment_rejects_invalid_demand_multiplier():
    from oracle_api.engine import assess_capacity

    try:
        assess_capacity([], demand_multiplier=6.0)
    except ValueError as exc:
        assert "at most 5" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
