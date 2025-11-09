from unittest.mock import patch, MagicMock
from google.cloud.firestore_v1 import FieldFilter

def test_api_full_flow_create_list_cron_runs(client, fake_db):
    # 1) Create schedule via HTTP
    body = {
        "name": "Program ISO",
        "active": True,
        "spec": {
            "tz": "Europe/Bucharest",
            "week": {
                "Mon": {"enabled": True, "checkIn": "09:00", "checkOut": "17:00", "location": "birou"},
                "Tue": {"enabled": True, "checkIn": "09:00", "checkOut": "17:00", "location": "telemunca"},
                "Wed": {"enabled": True, "checkIn": "09:00", "checkOut": "17:00", "location": "birou"},
                "Thu": {"enabled": True, "checkIn": "09:00", "checkOut": "17:00", "location": "telemunca"},
                "Fri": {"enabled": True, "checkIn": "09:00", "checkOut": "16:00", "location": "birou"},
                "Sat": {"enabled": False}, "Sun": {"enabled": False}
            },
            "jitter": {"minutesMinus": 0, "minutesPlus": 0},
            "holidays": {"publicCalendars": ["RO"], "personalDates": [], "behavior": "skip"},
            "exceptions": {"include": [], "exclude": [], "hourWindows": []},
        }
    }
    r = client.post("/api/schedules", json=body)
    assert r.status_code == 200, r.text
    doc = r.json()
    schedule_id = doc["id"]

    # 2) List schedules
    r2 = client.get("/api/schedules")
    assert r2.status_code == 200
    assert any(s["id"] == schedule_id for s in r2.json())

    # 3) Make it "due": set next_event.at to a past ISO (so cron will pick it)
    schedules = fake_db.collection("schedules")
    snap = schedules.document(schedule_id).get()
    data = snap.to_dict()
    data["next_event"]["at"] = "2000-01-01T00:00:00+00:00"
    schedules.document(schedule_id).set(data)

    # 4) Run cron (dev bypass is enabled by fixture)
    # Mock iso_task.run_iso_check to avoid Playwright automation in tests
    with patch("routers.cron.run_iso_check") as mock_run:
        mock_run.return_value = ("success", "Test execution")
        r3 = client.post("/cron/tick", headers={"x-bypass-oidc": "true"})
        assert r3.status_code == 200
        assert r3.json()["processed"] >= 1

    # 5) Verify a run exists for this schedule, ordered by scheduledAt
    runs = fake_db.collection("runs")
    q = (
        runs.where(filter=FieldFilter("uid", "==", "u_test"))
            .where(filter=FieldFilter("scheduleId", "==", schedule_id))
            .order_by("scheduledAt")
            .stream()
    )
    result = list(q)
    assert len(result) >= 1
    assert result[-1].to_dict()["scheduleId"] == schedule_id
