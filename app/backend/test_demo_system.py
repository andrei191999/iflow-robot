"""
Quick test script for demo/simulation system.

Run this to verify all components are working:
    python test_demo_system.py
"""

import sys
import traceback

# Fix for Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def test_imports():
    """Test that all new modules can be imported."""
    print("Testing imports...")

    try:
        from schemas.demo import DemoRequest, DemoResult, SimulationStep
        print("  ✓ Demo schemas")
    except Exception as e:
        print(f"  ✗ Demo schemas: {e}")
        return False

    try:
        from services.screenshot_storage import ScreenshotStorage, get_screenshot_storage
        print("  ✓ Screenshot storage")
    except Exception as e:
        print(f"  ✗ Screenshot storage: {e}")
        return False

    try:
        from services.mock_iflow import mock_iflow_router, MockState, get_mock_state
        print("  ✓ Mock iFlow router")
    except Exception as e:
        print(f"  ✗ Mock iFlow router: {e}")
        return False

    try:
        from services.mock_iflow.state import set_mock_behavior, reset_mock_state
        print("  ✓ Mock iFlow state")
    except Exception as e:
        print(f"  ✗ Mock iFlow state: {e}")
        return False

    try:
        from services.mock_iflow.templates import get_login_page, get_dashboard_page
        print("  ✓ Mock iFlow templates")
    except Exception as e:
        print(f"  ✗ Mock iFlow templates: {e}")
        return False

    try:
        from services.iso_task_enhanced import run_iso_check_enhanced, SimulationLogger
        print("  ✓ Enhanced automation")
    except Exception as e:
        print(f"  ✗ Enhanced automation: {e}")
        return False

    try:
        from routers.demo import router as demo_router
        print("  ✓ Demo router")
    except Exception as e:
        print(f"  ✗ Demo router: {e}")
        return False

    print("All imports successful!\n")
    return True


def test_schemas():
    """Test schema models."""
    print("Testing schemas...")

    try:
        from schemas.demo import DemoRequest, DemoResult, SimulationStep

        # Test DemoRequest
        request = DemoRequest(
            mode="screenshot",
            speed="normal",
            scenario="check-in",
            location="telemunca",
            use_mock=True,
            mock_behavior="success"
        )
        assert request.mode == "screenshot"
        assert request.speed == "normal"
        print("  ✓ DemoRequest model")

        # Test SimulationStep
        step = SimulationStep(
            step_number=0,
            name="test_step",
            timestamp="2025-11-09T10:00:00Z",
            duration_ms=100,
            status="success",
            message="Test message",
            screenshot_url=None
        )
        assert step.step_number == 0
        print("  ✓ SimulationStep model")

        # Test DemoResult
        result = DemoResult(
            success=True,
            duration_ms=5000,
            step_count=10,
            scenario="check-in",
            location="telemunca",
            mode="screenshot",
            steps=[step],
            screenshots=[],
            summary="Test summary"
        )
        assert result.success is True
        print("  ✓ DemoResult model")

    except Exception as e:
        print(f"  ✗ Schema tests failed: {e}")
        traceback.print_exc()
        return False

    print("Schema tests passed!\n")
    return True


def test_mock_state():
    """Test mock state management."""
    print("Testing mock state...")

    try:
        from services.mock_iflow.state import (
            get_mock_state,
            set_mock_behavior,
            reset_mock_state
        )

        # Get initial state
        state = get_mock_state()
        assert state.behavior == "success"
        print("  ✓ Get mock state")

        # Change behavior
        set_mock_behavior(behavior="login_fail")
        state = get_mock_state()
        assert state.behavior == "login_fail"
        print("  ✓ Set mock behavior")

        # Test validation
        assert not state.should_succeed_login()
        print("  ✓ Behavior validation")

        # Reset state
        reset_mock_state()
        state = get_mock_state()
        assert state.behavior == "success"
        print("  ✓ Reset mock state")

    except Exception as e:
        print(f"  ✗ Mock state tests failed: {e}")
        traceback.print_exc()
        return False

    print("Mock state tests passed!\n")
    return True


def test_templates():
    """Test HTML template generation."""
    print("Testing templates...")

    try:
        from services.mock_iflow.templates import (
            get_login_page,
            get_dashboard_page,
            get_success_page
        )

        # Test login page
        login_html = get_login_page()
        assert "td_reg_email" in login_html
        assert "td_reg_password" in login_html
        assert "Intră în cont" in login_html
        print("  ✓ Login page template")

        # Test login page with error
        login_error_html = get_login_page(error="Test error")
        assert "Test error" in login_error_html
        print("  ✓ Login page with error")

        # Test dashboard page
        dashboard_html = get_dashboard_page("test_session_123")
        assert "test_session_123" in dashboard_html
        assert "td-check-in-out" in dashboard_html
        print("  ✓ Dashboard page template")

        # Test success page
        success_html = get_success_page()
        assert "Success" in success_html or "success" in success_html
        print("  ✓ Success page template")

    except Exception as e:
        print(f"  ✗ Template tests failed: {e}")
        traceback.print_exc()
        return False

    print("Template tests passed!\n")
    return True


def test_screenshot_storage():
    """Test screenshot storage (local mode)."""
    print("Testing screenshot storage...")

    try:
        from services.screenshot_storage import ScreenshotStorage
        import os

        # Test local storage
        storage = ScreenshotStorage(mode="local")
        assert storage.mode == "local"
        print("  ✓ Local storage initialization")

        # Test save screenshot
        test_data = b"fake_png_data_for_testing"
        path = storage.save_screenshot(
            uid="test_user",
            timestamp="2025-11-09T10-00-00",
            step_number=0,
            screenshot_data=test_data,
            step_name="test_step"
        )
        assert "test_user" in path
        assert "test_step" in path
        print("  ✓ Save screenshot")

        # Test list screenshots
        screenshots = storage.get_simulation_screenshots(
            uid="test_user",
            timestamp="2025-11-09T10-00-00"
        )
        assert len(screenshots) > 0
        print("  ✓ List screenshots")

        # Cleanup test files
        import shutil
        test_dir = storage.local_root / "users" / "test_user"
        if test_dir.exists():
            shutil.rmtree(test_dir)
        print("  ✓ Cleanup")

    except Exception as e:
        print(f"  ✗ Screenshot storage tests failed: {e}")
        traceback.print_exc()
        return False

    print("Screenshot storage tests passed!\n")
    return True


def test_simulation_logger():
    """Test simulation logger."""
    print("Testing simulation logger...")

    try:
        from services.iso_task_enhanced import SimulationLogger

        logger = SimulationLogger(
            capture_screenshots=False,
            speed="normal",
            screenshot_storage=None,
            uid="test_user",
            timestamp="2025-11-09"
        )

        # Add some steps
        step1 = logger.add_step(
            name="test_step_1",
            status="success",
            message="First test step"
        )
        assert step1.step_number == 0
        print("  ✓ Add step")

        step2 = logger.add_step(
            name="test_step_2",
            status="warning",
            message="Second test step"
        )
        assert step2.step_number == 1
        print("  ✓ Add another step")

        # Check total steps
        assert len(logger.steps) == 2
        print("  ✓ Step count")

        # Get duration
        duration = logger.get_total_duration_ms()
        assert duration >= 0
        print("  ✓ Get duration")

    except Exception as e:
        print(f"  ✗ Simulation logger tests failed: {e}")
        traceback.print_exc()
        return False

    print("Simulation logger tests passed!\n")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Demo System Test Suite")
    print("=" * 60)
    print()

    tests = [
        ("Imports", test_imports),
        ("Schemas", test_schemas),
        ("Mock State", test_mock_state),
        ("Templates", test_templates),
        ("Screenshot Storage", test_screenshot_storage),
        ("Simulation Logger", test_simulation_logger),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"FATAL ERROR in {name}: {e}")
            traceback.print_exc()
            results.append((name, False))

    print()
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
