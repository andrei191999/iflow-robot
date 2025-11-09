def _sample_spec():
    return {
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
        "holidays": {"publicCalendars": [], "personalDates": [], "behavior": "skip"},
        "exceptions": {"include": [], "exclude": [], "hourWindows": []},
    }

def test_update_delete_preview_flow(client):
    # Create
    body = {"name": "Prog", "active": True, "spec": _sample_spec()}
    r = client.post("/api/schedules", json=body)
    assert r.status_code == 200, r.text
    sched = r.json()
    sid = sched["id"]

    # Update: change location & jitter
    upd = {
        "name": "Prog v2",
        "active": True,
        "uid": "will_be_overridden",
        "spec": _sample_spec()
    }
    upd["spec"]["week"]["Mon"]["location"] = "telemunca"
    upd["spec"]["jitter"] = {"minutesMinus": 2, "minutesPlus": 3}

    r2 = client.put(f"/api/schedules/{sid}", json=upd)
    assert r2.status_code == 200
    assert r2.json()["spec"]["week"]["Mon"]["location"] == "telemunca"

    # Preview next 5 events
    r3 = client.post("/api/schedules/preview", json={"spec": _sample_spec(), "count": 5})
    assert r3.status_code == 200
    events = r3.json()["events"]
    assert len(events) == 5
    assert all(k in events[0] for k in ("type", "at", "localDate", "location"))

    # Delete
    r4 = client.delete(f"/api/schedules/{sid}")
    assert r4.status_code in (200, 204)

    # Check list is empty again
    r5 = client.get("/api/schedules")
    assert sid not in [s["id"] for s in r5.json()]
