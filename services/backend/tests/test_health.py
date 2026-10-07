import io
import json
import sys


def test_health_ok(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["error"] is None
    assert body["data"]["status"] == "ok"
    assert "meta" in body


def test_openapi_available(client):
    r = client.get("/api/v1/openapi.json")
    assert r.status_code == 200
    assert "/api/v1/health" in r.json()["paths"]


def test_passenger_wsgi_serves_health():
    import passenger_wsgi

    status_holder = {}

    def start_response(status, headers, exc_info=None):
        status_holder["status"] = status

    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/api/v1/health",
        "QUERY_STRING": "",
        "SERVER_NAME": "testserver",
        "SERVER_PORT": "80",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(b""),
        "wsgi.errors": sys.stderr,
        "wsgi.version": (1, 0),
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }
    body = b"".join(passenger_wsgi.application(environ, start_response))
    assert status_holder["status"].startswith("200")
    assert json.loads(body)["data"]["status"] == "ok"
