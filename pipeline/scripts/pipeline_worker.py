import os
import json
import subprocess
import time
import datetime

def run_sql(sql):
    try:
        result = subprocess.run(["team-db", sql], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running SQL: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None

def log_status(place_id, new_status, message):
    timestamp = datetime.datetime.now().isoformat()
    # Fetch current status_log
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

def process_new_leads():
    # Step 3 & 4: Monitor for 'contact_found' and generate/deploy demos
    leads = run_sql("SELECT * FROM leads WHERE status = 'contact_found'")
    if not leads:
        return

    for lead in leads:
        place_id = lead['place_id']
        business_name = lead['business_name']
        category = lead['category']
        address = lead['address']
        phone = lead['phone']
        
        print(f"Processing lead: {business_name} ({place_id})")
        
        try:
            # Call process_lead.py logic
            # Note: We are in scripts/ so we refer to sibling scripts
            # But the worker will run from pipeline/ root probably
            cmd = [
                "python3", "scripts/process_lead.py",
                "--id", place_id,
                "--name", business_name,
                "--category", category or "Business",
                "--address", address or "Contact for address",
                "--phone", phone or "Contact for phone"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Extract demo_url from stdout or a file
            # Our process_lead.py prints "Lead processed! Demo URL: ..."
            stdout = result.stdout
            demo_url = ""
            for line in stdout.split('\n'):
                if "Demo URL:" in line:
                    demo_url = line.split("Demo URL:")[1].strip()
                    break
            
            if demo_url:
                run_sql(f"UPDATE leads SET demo_url = '{demo_url}' WHERE place_id = '{place_id}'")
                log_status(place_id, "demo_deployed", f"Demo site deployed at {demo_url}")
            else:
                print(f"Failed to extract demo_url for {business_name}")
                log_status(place_id, "error_demo_gen", "Failed to extract demo_url from generation script")
                
        except Exception as e:
            print(f"Error processing lead {business_name}: {e}")
            log_status(place_id, "error_demo_gen", str(e))

def send_outreach_emails():
    # Step 6: Monitor for 'demo_deployed' and send cold email
    leads = run_sql("SELECT * FROM leads WHERE status = 'demo_deployed' AND email IS NOT NULL AND email != ''")
    if not leads:
        return

    for lead in leads:
        place_id = lead['place_id']
        business_name = lead['business_name']
        email = lead['email']
        demo_url = lead['demo_url']
        
        print(f"Sending outreach to: {business_name} <{email}>")
        
        try:
            # In a real scenario, we would call an Email API here (Resend/SendGrid)
            # For now, we mock it.
            
            # Load template
            with open("templates/outreach_email.txt", "r") as f:
                template = f.read()
            
            email_body = template.replace("[Business Name]", business_name) \
                                 .replace("[Demo URL]", demo_url)
            
            # Mock sending
            print(f"--- MOCK EMAIL START ---")
            print(f"To: {email}")
            print(f"Subject: Professional Website for {business_name}")
            print(f"Body:\n{email_body}")
            print(f"--- MOCK EMAIL END ---")
            
            # Update status
            log_status(place_id, "outreach_sent", f"Outreach email sent to {email}")
            
        except Exception as e:
            print(f"Error sending email to {business_name}: {e}")
            log_status(place_id, "error_outreach", str(e))

def main():
    print("Pipeline Worker started. Press Ctrl+C to stop.")
    while True:
        try:
            process_new_leads()
            send_outreach_emails()
        except Exception as e:
            print(f"Unexpected error in main loop: {e}")
        
        # Sleep for a bit before next poll
        time.sleep(30)

if __name__ == "__main__":
    main()
