from backend.services.capacity_service import CapacityService

def test_capacity_target_calculations():
    # Blueprint example: 60 days total, 10 shadow, 10 reverse shadow = 40 KT days
    # At 5.0 hours/day = 200 hours target capacity
    res = CapacityService.calculate_transition_capacity_targets(
        total_duration_days=60,
        shadow_days=10,
        reverse_shadow_days=10,
        daily_kt_hours=5.0,
    )
    assert res["total_duration_days"] == 60
    assert res["shadow_days"] == 10
    assert res["reverse_shadow_days"] == 10
    assert res["available_kt_days"] == 40
    assert res["target_capacity_hours"] == 200.0

def test_capacity_target_edge_cases():
    # Zero or negative protection
    res = CapacityService.calculate_transition_capacity_targets(
        total_duration_days=20,
        shadow_days=15,
        reverse_shadow_days=10,
        daily_kt_hours=4.0,
    )
    assert res["available_kt_days"] == 0
    assert res["target_capacity_hours"] == 0.0

