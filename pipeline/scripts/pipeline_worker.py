import os
import json
import subprocess
import time
import datetime
import sys

# Add directories to path so we can import modules if needed
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PIPELINE_ROOT = os.path.join(REPO_ROOT, "pipeline")
sys.path.append(REPO_ROOT)

def run_sql(sql):
    try:
        result = subprocess.run(["team-db", sql], capture_output=True, text=True, check=True)
        return json.loads(result.stdout) if result.stdout.strip() else []
    except subprocess.CalledProcessError as e:
        print(f"Error running SQL: {e}")
        return None
    except json.JSONDecodeError:
        return []

def log_status(place_id, new_status, message):
    timestamp = datetime.datetime.now().isoformat()
    res = run_sql(f"SELECT status_log FROM leads WHERE place_id = '{place_id}'")
    if res and len(res) > 0:
        current_log_str = res[0].get('status_log') or "[]"
        try:
            current_log = json.loads(current_log_str)
        except:
            current_log = []
        
        current_log.append({
            "status": new_status,
            "timestamp": timestamp,
            "message": message
        })
        
        new_log_str = json.dumps(current_log).replace("'", "''")
        run_sql(f"UPDATE leads SET status = '{new_status}', status_log = '{new_log_str}' WHERE place_id = '{place_id}'")

def deploy_demo(lead):
    place_id = lead['place_id']
    business_name = lead['business_name']
    
    # Prepare project name
    sanitized_name = "".join(c if c.isalnum() else "-" for c in business_name.lower())
    project_name = f"siteflow-{sanitized_name}-{place_id[:8]}"
    dist_dir = os.path.join(REPO_ROOT, "dist", project_name)
    os.makedirs(dist_dir, exist_ok=True)
    
    print(f"Generating site for {business_name}...")
    try:
        # Call generator.py
        subprocess.run([
            "python3", os.path.join(PIPELINE_ROOT, "scripts/generator.py"),
            "--name", business_name,
            "--category", lead.get('category') or "Business",
            "--address", lead.get('address') or "Contact for address",
            "--phone", lead.get('phone') or "Contact for phone",
            "--output", dist_dir
        ], check=True)
        
        # Deploy using wrangler mock (or real if creds exist)
        deploy_script = os.path.join(PIPELINE_ROOT, "scripts/deploy_site.sh")
        result = subprocess.run([
            "bash", deploy_script,
            project_name,
            dist_dir
        ], capture_output=True, text=True, check=True)
        
        # Extract URL
        demo_url = f"https://{project_name}.pages.dev"
        # Check if deploy_url.txt was created in the current dir by the script
        if os.path.exists("deploy_url.txt"):
            with open("deploy_url.txt", "r") as f:
                demo_url = f.read().strip()
        
        run_sql(f"UPDATE leads SET demo_url = '{demo_url}' WHERE place_id = '{place_id}'")
        log_status(place_id, "demo_deployed", f"Demo site deployed at {demo_url}")
        return demo_url
        
    except Exception as e:
        print(f"Error deploying demo for {business_name}: {e}")
        log_status(place_id, "error_demo_gen", str(e))
        return None

def send_outreach(lead):
    place_id = lead['place_id']
    business_name = lead['business_name']
    email = lead['email']
    demo_url = lead['demo_url']
    
    if not email or not demo_url:
        return
    
    print(f"Sending outreach to {business_name} <{email}>...")
    try:
        # Load our custom outreach template
        template_path = os.path.join(PIPELINE_ROOT, "templates/outreach_email.txt")
        if not os.path.exists(template_path):
            # Fallback
            template_path = os.path.join(REPO_ROOT, "outreach/templates/outreach_email.txt")
            
        with open(template_path, "r") as f:
            template = f.read()
        
        # Replace placeholders
        email_body = template.replace("{{ business_name }}", business_name) \
                             .replace("{{ demo_url }}", demo_url)
        
        # Mock send or use outreach/email_sender.py logic
        # For now, we mock until keys are provided
        print(f"--- MOCK EMAIL START ---")
        print(f"To: {email}")
        print(f"Body:\n{email_body}")
        print(f"--- MOCK EMAIL END ---")
        
        log_status(place_id, "outreach_sent", f"Outreach email sent to {email}")
        
    except Exception as e:
        print(f"Error sending outreach for {business_name}: {e}")
        log_status(place_id, "error_outreach", str(e))

def main():
    print("SiteFlow Master Worker started.")
    while True:
        # Step 3: Demos
        leads_for_demo = run_sql("SELECT * FROM leads WHERE status = 'contact_found'")
        if leads_for_demo:
            for lead in leads_for_demo:
                deploy_demo(lead)
            
        # Step 6: Outreach
        leads_for_outreach = run_sql("SELECT * FROM leads WHERE status = 'demo_deployed' AND email IS NOT NULL AND email != ''")
        if leads_for_outreach:
            for lead in leads_for_outreach:
                send_outreach(lead)
            
        time.sleep(30)

if __name__ == "__main__":
    if "--run-once" in sys.argv:
        leads_for_demo = run_sql("SELECT * FROM leads WHERE status = 'contact_found'")
        for lead in leads_for_demo:
            deploy_demo(lead)
        leads_for_outreach = run_sql("SELECT * FROM leads WHERE status = 'demo_deployed' AND email IS NOT NULL AND email != ''")
        for lead in leads_for_outreach:
            send_outreach(lead)
    else:
        main()
