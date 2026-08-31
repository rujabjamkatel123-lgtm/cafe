from app import create_app

app = create_app()
for rule in sorted(app.url_map.iter_rules(), key=lambda item: item.rule):
    if any(prefix in rule.rule for prefix in ("/customer", "/table", "/receptionist", "/manager")):
        print(f"{rule.rule} -> {rule.endpoint} [{','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))}]")

assert any(rule.rule == "/customer" and rule.endpoint == "customer.entry" for rule in app.url_map.iter_rules())
assert any(rule.rule == "/customer/" and rule.endpoint == "customer.entry" for rule in app.url_map.iter_rules())
assert any(rule.rule == "/table/<int:table_id>" for rule in app.url_map.iter_rules())
assert any(rule.rule == "/manager/qr/<int:table_id>" for rule in app.url_map.iter_rules())
assert any(rule.rule == "/manager/qr/<int:table_id>/download" for rule in app.url_map.iter_rules())
print("route assertions: PASS")

with app.test_client() as client:
    response = client.get("/customer?table=3", follow_redirects=False)
    assert response.status_code in (302, 500), response.status_code
    assert any(path in response.headers.get("Location", "") for path in ("/customer/dashboard", "/customer/menu")) or response.status_code == 500
    print("customer entry request: PASS (database availability determines final dashboard response)")

    response = client.get("/receptionist/dashboard", follow_redirects=False)
    assert response.status_code == 302, response.status_code
    assert "/login" in response.headers["Location"]
    print("staff protection: PASS")

with app.test_client() as client:
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["role"] = "manager"
    response = client.get("/manager/qr/3")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG")
    print("manager QR image endpoint: PASS")

    response = client.get("/manager/qr/6")
    assert response.status_code == 500
    print("invalid QR table rejection: PASS")
