from app import app

def test_home():
    resp = app.test_client().get("/")
    assert resp.status_code == 200
    assert b"Hello from Flask" in resp.data
