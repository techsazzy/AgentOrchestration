import pytest
import os
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse
from src.api.middleware import SecurityMiddleware

def test_security_middleware_normal_pass():
    app = FastAPI()
    app.add_middleware(SecurityMiddleware)
    
    @app.get("/test")
    async def test_route():
        return {"message": "ok"}
    
    client = TestClient(app)
    # Ensure AO_PRODUCTION_PROXY is false
    os.environ["AO_PRODUCTION_PROXY"] = "false"
    
    response = client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"

def test_security_middleware_production_proxy_reject_http():
    app = FastAPI()
    app.add_middleware(SecurityMiddleware)
    
    @app.get("/test")
    async def test_route():
        return {"message": "ok"}
    
    client = TestClient(app)
    os.environ["AO_PRODUCTION_PROXY"] = "true"
    
    # HTTP request should be rejected
    response = client.get("http://testserver/test")
    assert response.status_code == 403
    assert response.text == "HTTPS Required"
    assert response.headers["X-Content-Type-Options"] == "nosniff"

def test_security_middleware_production_proxy_accept_https_header():
    app = FastAPI()
    app.add_middleware(SecurityMiddleware)
    
    @app.get("/test")
    async def test_route():
        return {"message": "ok"}
    
    client = TestClient(app)
    os.environ["AO_PRODUCTION_PROXY"] = "true"
    
    # Request with X-Forwarded-Proto: https should be accepted
    response = client.get("/test", headers={"X-Forwarded-Proto": "https"})
    assert response.status_code == 200
    assert response.json() == {"message": "ok"}
    assert "Strict-Transport-Security" in response.headers

def test_security_middleware_exception_handling():
    app = FastAPI()
    app.add_middleware(SecurityMiddleware)
    
    @app.get("/error")
    async def error_route():
        raise ValueError("Sensitive error info")
    
    client = TestClient(app)
    os.environ["AO_PRODUCTION_PROXY"] = "false"
    
    response = client.get("/error")
    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    # Ensure sensitive info is not leaked in the body
    assert "Sensitive error info" not in response.text
    assert response.headers["X-Content-Type-Options"] == "nosniff"

def test_security_middleware_hsts_header():
    app = FastAPI()
    app.add_middleware(SecurityMiddleware)
    
    @app.get("/test")
    async def test_route():
        return {"message": "ok"}
    
    client = TestClient(app)
    
    # Case 1: Not production, but direct HTTPS
    os.environ["AO_PRODUCTION_PROXY"] = "false"
    response = client.get("https://testserver/test")
    assert response.status_code == 200
    assert "Strict-Transport-Security" in response.headers
    
    # Case 2: Not production, direct HTTP -> No HSTS (optional, but good for safety)
    response = client.get("http://testserver/test")
    assert response.status_code == 200
    assert "Strict-Transport-Security" not in response.headers
