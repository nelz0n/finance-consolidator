import requests
import sys
import time

BASE_URL = "http://localhost:8000"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def check_health():
    url = f"{BASE_URL}/api/v1/health"
    try:
        log(f"Checking {url}...")
        response = requests.get(url)
        if response.status_code == 200:
            log("Backend Health Check: PASSED", "SUCCESS")
            return True
        else:
            log(f"Backend Health Check: FAILED (Status {response.status_code})", "ERROR")
            return False
    except Exception as e:
        log(f"Backend Health Check: FAILED (Connection refused/Error: {e})", "ERROR")
        return False

def check_frontend():
    url = f"{BASE_URL}/"
    try:
        log(f"Checking {url}...")
        response = requests.get(url)
        if response.status_code == 200:
            # Simple check for HTML content
            if "<!doctype html>" in response.text.lower() or "<html" in response.text.lower():
                log("Frontend Serving: PASSED", "SUCCESS")
                return True
            else:
                log("Frontend Serving: FAILED (Content does not look like HTML)", "ERROR")
                return False
        else:
            log(f"Frontend Serving: FAILED (Status {response.status_code})", "ERROR")
            return False
    except Exception as e:
        log(f"Frontend Serving: FAILED (Connection refused/Error: {e})", "ERROR")
        return False

def check_api_endpoints():
    endpoints = [
        "/api/v1/transactions",
        "/api/v1/dashboard/summary",
        "/api/v1/categories/tree"
    ]
    all_passed = True
    for ep in endpoints:
        url = f"{BASE_URL}{ep}"
        try:
            log(f"Checking {url}...")
            response = requests.get(url)
            if response.status_code == 200:
                log(f"Endpoint {ep}: PASSED", "SUCCESS")
            else:
                log(f"Endpoint {ep}: FAILED (Status {response.status_code})", "ERROR")
                all_passed = False
        except Exception as e:
            log(f"Endpoint {ep}: FAILED (Error: {e})", "ERROR")
            all_passed = False
    return all_passed

def main():
    log("Starting End-to-End Deployment Test...")
    
    # Wait a bit for startup if needed (though it should be up)
    time.sleep(1)

    if not check_health():
        log("Health check failed. Aborting.", "CRITICAL")
        sys.exit(1)

    if not check_frontend():
        log("Frontend check failed.", "WARNING")
    
    if not check_api_endpoints():
        log("Some API endpoints failed.", "WARNING")
    else:
        log("All API endpoints responded with 200 OK.", "SUCCESS")

    log("Deployment Test Complete.")

if __name__ == "__main__":
    main()
