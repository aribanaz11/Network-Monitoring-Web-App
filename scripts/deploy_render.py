#!/usr/bin/env python3
"""
Automated Render Deployment Script for NetWatch
Calls the Render REST API to create and deploy the service.
"""

import sys
import json
import urllib.request
import urllib.error

def deploy_to_render(api_key, repo_url="https://github.com/aribanaz11/Network-Monitoring-Web-App"):
    print(f"Connecting to Render REST API with repository: {repo_url}...")

    # 1. Get User / Owner ID
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        req = urllib.request.Request("https://api.render.com/v1/owners", headers=headers)
        with urllib.request.urlopen(req) as resp:
            owners = json.loads(resp.read().decode())
            if not owners:
                print("Error: No Render owners found for this API key.")
                return False
            owner_id = owners[0]["owner"]["id"]
            owner_name = owners[0]["owner"].get("name", "User")
            print(f"Authenticated as Render Owner: {owner_name} (ID: {owner_id})")

    except urllib.error.HTTPError as e:
        print(f"Authentication failed (HTTP {e.code}): {e.read().decode()}")
        return False

    # 2. Create Web Service
    service_payload = {
        "type": "web_service",
        "name": "network-monitoring-web-app",
        "ownerId": owner_id,
        "repo": repo_url,
        "branch": "main",
        "serviceDetails": {
            "env": "python",
            "plan": "free",
            "region": "oregon",
            "buildCommand": "chmod +x build.sh && ./build.sh",
            "startCommand": "gunicorn --chdir backend netwatch_core.wsgi:application --bind 0.0.0.0:$PORT --workers 2",
            "envVars": [
                {"key": "PYTHON_VERSION", "value": "3.12.0"},
                {"key": "DEBUG", "value": "False"},
                {"key": "ALLOWED_HOSTS", "value": "*"},
                {"key": "USE_SQLITE", "value": "True"},
                {"key": "SIMULATOR_MODE", "value": "True"},
                {"key": "FERNET_KEY", "value": "W3sO-LqP7b_dG5vUv-0L2Y1t9kLpM_xZ7sQ2dF4jK8M="}
            ]
        }
    }

    try:
        data = json.dumps(service_payload).encode("utf-8")
        req = urllib.request.Request("https://api.render.com/v1/services", data=data, headers=headers)
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode())
            service_id = res["service"]["id"]
            service_url = res["service"]["serviceDetails"]["url"]
            print("\n" + "="*60)
            print("SUCCESS! Render Web Service Created!")
            print(f"Service ID:  {service_id}")
            print(f"Live URL:    {service_url}")
            print("="*60 + "\n")
            print("Render is now building and deploying your application.")
            return True

    except urllib.error.HTTPError as e:
        err_msg = e.read().decode()
        print(f"Service creation failed (HTTP {e.code}): {err_msg}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deploy_render.py <RENDER_API_KEY>")
        sys.exit(1)

    api_key = sys.argv[1].strip()
    deploy_to_render(api_key)
