import uuid
from starlette.testclient import TestClient

from app.main import app
from app.auth import create_access_token
from app.database.mongodb import users_collection, trips_collection


def run_security_tests():
    print("=" * 60)
    print("STARTING TRAVELTRACK DEFENSIVE SECURITY & VAPT TEST SUITE")
    print("=" * 60)

    test_client = TestClient(app, raise_server_exceptions=False)

    # -------------------------------------------------------------
    # 1. SSRF Protection Tests (/explore/photo)
    # -------------------------------------------------------------
    print("\n[SEC TEST 1] Verifying SSRF Protections on /explore/photo...")
    ssrf_payloads = [
        ("Loopback IP", "http://127.0.0.1:8000/health"),
        ("Localhost", "http://localhost:27017/"),
        ("Cloud Metadata AWS/GCP", "http://169.254.169.254/latest/meta-data/"),
        ("RFC1918 Class A", "http://10.0.0.1/admin"),
        ("RFC1918 Class B", "http://172.16.0.1/internal"),
        ("RFC1918 Class C", "http://192.168.1.1/router"),
        ("Non-whitelisted Domain", "https://attacker-controlled-site.com/exploit.jpg"),
        ("Arbitrary Scheme (file)", "file:///etc/passwd"),
        ("Arbitrary Scheme (ftp)", "ftp://ftp.is.co.za/test.jpg"),
        ("Subdomain Impersonation", "https://wikimedia.org.attacker.com/evil.jpg"),
    ]

    for label, payload_url in ssrf_payloads:
        res = test_client.get("/explore/photo", params={"url": payload_url})
        assert res.status_code in [400, 404], (
            f"SSRF Vulnerability: {label} ({payload_url}) returned unexpected status {res.status_code}: {res.text}"
        )
        print(f"  [PASS] {label:<25} properly blocked (HTTP {res.status_code})")

    # -------------------------------------------------------------
    # 2. Defensive Security Headers
    # -------------------------------------------------------------
    print("\n[SEC TEST 2] Verifying Defensive Security Headers...")
    res = test_client.get("/api")
    assert res.status_code == 200

    headers = res.headers
    assert headers.get("x-frame-options") == "DENY", f"Missing/incorrect X-Frame-Options: {headers.get('x-frame-options')}"
    print("  [PASS] X-Frame-Options: DENY (Clickjacking protection)")

    assert headers.get("x-content-type-options") == "nosniff", f"Missing X-Content-Type-Options: {headers.get('x-content-type-options')}"
    print("  [PASS] X-Content-Type-Options: nosniff (MIME-sniffing protection)")

    assert "frame-ancestors 'none'" in headers.get("content-security-policy", ""), "CSP frame-ancestors missing"
    print("  [PASS] Content-Security-Policy: frame-ancestors 'none'")

    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin", "Referrer-Policy header missing"
    print("  [PASS] Referrer-Policy: strict-origin-when-cross-origin")

    assert "geolocation" in headers.get("permissions-policy", ""), "Permissions-Policy missing"
    print("  [PASS] Permissions-Policy configured")

    assert "no-store" in headers.get("cache-control", ""), "Cache-Control no-store missing on dynamic endpoint"
    print("  [PASS] Cache-Control: no-store (Web Cache Deception protection)")

    # -------------------------------------------------------------
    # 3. Strict CORS Validation (Render Wildcard Removal)
    # -------------------------------------------------------------
    print("\n[SEC TEST 3] Verifying CORS Boundary Enforcement...")
    # Malicious Render tenant origin should be REJECTED
    untrusted_origin = "https://evil-attacker-app.onrender.com"
    res_cors_bad = test_client.get(
        "/api",
        headers={"Origin": untrusted_origin}
    )
    cors_allow = res_cors_bad.headers.get("access-control-allow-origin")
    assert cors_allow != untrusted_origin, (
        f"CORS Misconfiguration: Untrusted origin {untrusted_origin} was allowed!"
    )
    print(f"  [PASS] Untrusted Render tenant origin rejected ({untrusted_origin})")

    # Legitimate configured origin should be ALLOWED
    trusted_origin = "https://triptrack-frontend.onrender.com"
    res_cors_good = test_client.get(
        "/api",
        headers={"Origin": trusted_origin}
    )
    assert res_cors_good.headers.get("access-control-allow-origin") == trusted_origin, (
        f"Legitimate origin {trusted_origin} was unexpectedly not allowed"
    )
    print(f"  [PASS] Legitimate frontend origin permitted ({trusted_origin})")

    # -------------------------------------------------------------
    # 4. Request Body Size Limit (DoS Protection)
    # -------------------------------------------------------------
    print("\n[SEC TEST 4] Verifying Request Body Size Limit...")
    # Attempt request declaring Content-Length > 2MB (2097152 bytes)
    res_oversize = test_client.post(
        "/users/login",
        headers={"Content-Length": "3000000", "Content-Type": "application/json"},
        content=b'{"email":"a@b.com"}'
    )
    assert res_oversize.status_code == 413, f"Expected 413 Payload Too Large, got {res_oversize.status_code}"
    print("  [PASS] Oversized request payload blocked (HTTP 413)")

    # -------------------------------------------------------------
    # 5. Password Length Limit & Boundary Validation
    # -------------------------------------------------------------
    print("\n[SEC TEST 5] Verifying Password Length Limit (Bcrypt 72-Byte Boundary)...")
    huge_password = "A" * 150
    res_huge_pw = test_client.post(
        "/users/register",
        json={
            "name": "Buffer Test",
            "email": "huge_pw_test@example.com",
            "password": huge_password
        }
    )
    assert res_huge_pw.status_code == 422, (
        f"Expected 422 for password exceeding 72 chars, got {res_huge_pw.status_code}"
    )
    print("  [PASS] Password > 72 chars rejected by schema (HTTP 422)")

    # -------------------------------------------------------------
    # 6. Rate Limiting on Authentication Endpoints
    # -------------------------------------------------------------
    print("\n[SEC TEST 6] Verifying Rate Limiting on Login & Registration...")
    # Trigger login rate limit
    login_rate_triggered = False
    for i in range(20):
        res_login_flood = test_client.post(
            "/users/login",
            json={"email": "ratelimit_probe@example.com", "password": "WrongPassword!"}
        )
        if res_login_flood.status_code == 429:
            login_rate_triggered = True
            assert "Retry-After" in res_login_flood.headers
            print(f"  [PASS] Login rate limit triggered after {i + 1} attempts (HTTP 429, Retry-After: {res_login_flood.headers['Retry-After']}s)")
            break

    assert login_rate_triggered, "Login rate limiter was not triggered after 20 rapid attempts"

    # -------------------------------------------------------------
    # 7. Information Disclosure Prevention in Error Handling
    # -------------------------------------------------------------
    print("\n[SEC TEST 7] Verifying Error Message Sanitization...")
    # Attempting to fetch non-existent or invalid format
    res_invalid_id = test_client.get("/trips/single/invalid_hex_id", headers={"Authorization": "Bearer fake"})
    assert "Traceback" not in res_invalid_id.text
    assert "pymongo" not in res_invalid_id.text
    print("  [PASS] No internal tracebacks or driver exceptions disclosed in error responses")

    # -------------------------------------------------------------
    # 8. JWT Security & Tampering Checks
    # -------------------------------------------------------------
    print("\n[SEC TEST 8] Verifying JWT Tampering & Algorithm Confusion Rejection...")
    # Create valid user token
    user_id = "507f1f77bcf86cd799439011"
    valid_token = create_access_token(user_id)

    # 8a. Valid token works
    # Header format verification
    res_valid = test_client.get(f"/trips/{user_id}", headers={"Authorization": f"Bearer {valid_token}"})
    assert res_valid.status_code == 200
    print("  [PASS] Valid JWT token accepted")

    # 8b. Tampered signature rejected
    tampered_token = valid_token[:-6] + "xxxxxx"
    res_tampered = test_client.get(f"/trips/{user_id}", headers={"Authorization": f"Bearer {tampered_token}"})
    assert res_tampered.status_code == 401
    print("  [PASS] Tampered JWT signature rejected (HTTP 401)")

    # 8c. Unsigned / "none" algorithm token rejected
    none_alg_token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiI1MDdmMWY3N2JjZjg2Y2Q3OTk0MzkwMTEifQ."
    res_none = test_client.get(f"/trips/{user_id}", headers={"Authorization": f"Bearer {none_alg_token}"})
    assert res_none.status_code == 401
    print("  [PASS] 'none' algorithm token rejected (HTTP 401)")

    # -------------------------------------------------------------
    # 9. IDOR / Mass Assignment Hardening on Trip Creation
    # -------------------------------------------------------------
    print("\n[SEC TEST 9] Verifying IDOR & Mass Assignment Protections...")
    other_user_id = "507f1f77bcf86cd799439099"
    # Attempt to create trip specifying someone else's user_id
    res_spoof = test_client.post(
        "/trips/",
        headers={"Authorization": f"Bearer {valid_token}"},
        json={
            "user_id": other_user_id,
            "destination": "Paris, France",
            "title": "Spoofed Trip",
            "start_date": "2026-09-01",
            "end_date": "2026-09-05",
            "status": "planned",
            "budget": 1000.0,
            "travelers": 1
        }
    )
    assert res_spoof.status_code == 403, f"Expected 403 Forbidden when specifying different user_id, got {res_spoof.status_code}"
    print("  [PASS] Cross-user trip creation blocked with 403 Forbidden")

    print("\n" + "=" * 60)
    print("ALL DEFENSIVE SECURITY & VAPT TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_security_tests()
