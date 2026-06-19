#!/usr/bin/env python3
import os
import sys
import time
import json
import subprocess
import argparse

# Re-execute in virtualenv if not already running in it
venv_python = "/home/team/shared/builder/venv/bin/python"
if sys.executable != venv_python and os.path.exists(venv_python):
    os.execv(venv_python, [venv_python] + sys.argv)

# Now we can safely import requests
try:
    import requests
except ImportError:
    print("[ERROR] 'requests' library not found. Please install it in the virtual environment.")
    sys.exit(1)

# Helper to run database queries via team-db CLI
def run_team_db(sql_statement):
    env = os.environ.copy()
    env["TMPDIR"] = "/home/agent-site-builder/tmp"
    cli_path = "/home/agent-site-builder/bin/team-db"
    
    # Run team-db command
    result = subprocess.run([cli_path, sql_statement], env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] team-db query failed: {sql_statement}")
        print(f"Stderr: {result.stderr}")
        raise Exception(f"Database query failed: {result.stderr}")
        
    try:
        return json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        # Non-select queries may return empty string or non-JSON
        return []

# Deploy static HTML directly to Vercel via REST API
def deploy_to_vercel(project_name, html_content, token):
    url = "https://api.vercel.com/v13/deployments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": project_name,
        "files": [
            {
                "file": "index.html",
                "data": html_content
            }
        ],
        "projectSettings": {
            "framework": None
        }
    }
    print(f"[Vercel] Triggering deployment for project '{project_name}'...")
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code in [200, 201]:
        data = response.json()
        deployment_url = data.get("url")
        if deployment_url:
            return f"https://{deployment_url}"
        return f"https://{project_name}.vercel.app"
    else:
        print(f"[Vercel ERROR] Status: {response.status_code}, Response: {response.text}")
        raise Exception(f"Vercel deployment failed: {response.text}")

# Deploy static HTML directly to Netlify via REST API
def deploy_to_netlify(site_name, index_html_content, token):
    import zipfile
    import io
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 1. Create a site (or look it up)
    create_url = "https://api.netlify.com/api/v1/sites"
    site_payload = {
        "name": site_name
    }
    print(f"[Netlify] Creating/looking up site '{site_name}'...")
    response = requests.post(create_url, headers=headers, json=site_payload)
    
    site_id = None
    demo_url = None
    if response.status_code in [200, 201]:
        site_data = response.json()
        site_id = site_data.get("id")
        demo_url = site_data.get("ssl_url") or site_data.get("url")
    elif response.status_code == 422: # Site name already taken
        print(f"[Netlify] Site name '{site_name}' already exists, creating random-named site instead...")
        response = requests.post(create_url, headers=headers, json={})
        if response.status_code in [200, 201]:
            site_data = response.json()
            site_id = site_data.get("id")
            demo_url = site_data.get("ssl_url") or site_data.get("url")
            
    if not site_id:
        print(f"[Netlify ERROR] Failed to create site. Status: {response.status_code}, Response: {response.text}")
        raise Exception(f"Failed to create Netlify site: {response.text}")
        
    # 2. Create in-memory ZIP of index.html
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('index.html', index_html_content)
        
    zip_buffer.seek(0)
    
    # 3. Upload ZIP file to deploy
    print(f"[Netlify] Uploading build contents to site '{site_id}'...")
    deploy_url = f"https://api.netlify.com/api/v1/sites/{site_id}/deploys"
    deploy_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/zip"
    }
    deploy_response = requests.post(deploy_url, headers=deploy_headers, data=zip_buffer.getvalue())
    if deploy_response.status_code in [200, 201, 211]:
        deploy_data = deploy_response.json()
        return deploy_data.get("ssl_url") or deploy_data.get("url") or demo_url
    else:
        print(f"[Netlify ERROR] Status: {deploy_response.status_code}, Response: {deploy_response.text}")
        raise Exception(f"Netlify deploy failed: {deploy_response.text}")

# Main process loop
def run_pipeline(mock_mode_flag):
    print("Checking database for new leads...")
    
    # Query leads with status 'new_lead'
    leads = run_team_db("SELECT id, business_name, address, phone, category, photos FROM leads WHERE status = 'new_lead'")
    if not leads:
        print("No new leads to process.")
        return
        
    print(f"Found {len(leads)} new lead(s) to process.")
    for lead in leads:
        lead_id = lead["id"]
        business_name = lead["business_name"]
        print(f"\n--- Processing Lead #{lead_id}: '{business_name}' ---")
        
        # 1. Generate unique directory slug
        # Sanitize name to make a safe directory slug
        sanitized_name = "".join(c if c.isalnum() else "-" for c in business_name.lower())
        sanitized_name = "-".join(filter(None, sanitized_name.split("-")))
        slug = f"siteforge-demo-{lead_id}-{sanitized_name}"
        output_dir = f"/home/team/shared/builder/output/{slug}"
        
        print(f"Generating site in local directory: {output_dir}")
        
        # 2. Call generator.py to build the static site files
        cmd = [
            sys.executable,
            "/home/team/shared/builder/generator.py",
            "--name", business_name,
            "--category", lead.get("category") or "Local Business",
            "--address", lead.get("address") or "Local Area",
            "--phone", lead.get("phone") or "Call Us Today",
            "--output", output_dir
        ]
        
        # Handle photos list
        photos = []
        if lead.get("photos"):
            try:
                photos = json.loads(lead["photos"])
            except Exception:
                photos = []
        if photos:
            cmd.extend(["--photos"] + photos)
            
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to generate site for {business_name}: {e}")
            continue
            
        # Verify index.html was created
        index_html_path = os.path.join(output_dir, "index.html")
        if not os.path.exists(index_html_path):
            print(f"[ERROR] Generated index.html not found for {business_name}")
            continue
            
        # 3. Read generated HTML content
        with open(index_html_path, "r") as f:
            html_content = f.read()
            
        # 4. Determine deployment target and execute
        vercel_token = os.environ.get("VERCEL_TOKEN")
        netlify_token = os.environ.get("NETLIFY_AUTH_TOKEN")
        
        demo_url = None
        
        if mock_mode_flag or (not vercel_token and not netlify_token):
            # Mock Deploy Mode
            print("[DEPLOY] Running in MOCK deploy mode.")
            print(f"[DEPLOY] Mock deploying static site for '{business_name}'...")
            # We host output files locally on port 3000 static server
            demo_url = f"http://localhost:3000/{slug}/index.html"
            print(f"[DEPLOY] Mock deployment completed successfully. Local URL: {demo_url}")
        else:
            # Real Deploy Mode
            try:
                if vercel_token:
                    print("[DEPLOY] Vercel token detected, deploying to Vercel...")
                    demo_url = deploy_to_vercel(f"siteforge-demo-{lead_id}", html_content, vercel_token)
                elif netlify_token:
                    print("[DEPLOY] Netlify token detected, deploying to Netlify...")
                    demo_url = deploy_to_netlify(f"siteforge-demo-{lead_id}", html_content, netlify_token)
                print(f"[DEPLOY] Production deployment completed successfully. URL: {demo_url}")
            except Exception as e:
                print(f"[DEPLOY ERROR] Production deployment failed: {e}")
                print("[DEPLOY] Falling back to local mock server deployment...")
                demo_url = f"http://localhost:3000/{slug}/index.html"
                
        # 5. Record deployment URL and update status to 'demo_ready'
        if demo_url:
            print(f"Updating database lead #{lead_id} status to 'demo_ready' with demo_url...")
            sql = f"UPDATE leads SET demo_url = '{demo_url}', status = 'demo_ready', updated_at = datetime('now') WHERE id = {lead_id}"
            run_team_db(sql)
            print(f"Lead #{lead_id} updated successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto Deploy Pipeline — Generate and Deploy Leads Automatically")
    parser.add_argument("--run-once", action="store_true", help="Run the pipeline once and exit")
    parser.add_argument("--interval", type=int, default=60, help="Interval in seconds between database checks")
    parser.add_argument("--mock", action="store_true", help="Force mock deployment mode (skip Vercel/Netlify API)")
    args = parser.parse_args()
    
    print("============================================================")
    print("  SiteForge Auto Deploy Pipeline Active")
    print(f"  Mode: {'MOCK ONLY' if args.mock else 'PRODUCTION / MOCK FALLBACK'}")
    print(f"  Looping: {'No (Run-Once)' if args.run_once else f'Yes (Every {args.interval}s)'}")
    print("============================================================")
    
    if args.run_once:
        run_pipeline(args.mock)
    else:
        while True:
            try:
                run_pipeline(args.mock)
            except Exception as e:
                print(f"[LOOP ERROR] Pipeline execution failed: {e}")
            time.sleep(args.interval)
