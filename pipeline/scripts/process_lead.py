import os
import json
import subprocess
import argparse

def process_lead(lead_id, business_name, category, address, phone):
    """
    Complete pipeline for a single lead:
    1. Generate site
    2. Deploy site
    3. Return demo_url
    """
    # 1. Generate Site
    project_slug = business_name.lower().replace(' ', '-').replace("'", "")
    # Add a bit of randomness or lead_id to ensure uniqueness
    project_name = f"siteflow-{project_slug}-{lead_id[:8]}"
    dist_dir = f"dist/{project_name}"
    
    os.makedirs(dist_dir, exist_ok=True)
    
    business_data = {
        "business_name": business_name,
        "category": category,
        "address": address,
        "phone": phone
    }
    
    data_json = json.dumps(business_data)
    
    print(f"Generating site for {business_name}...")
    subprocess.run([
        "python3", "scripts/generate_site.py",
        "--data", data_json,
        "--output", dist_dir
    ], check=True)
    
    # 2. Deploy Site
    print(f"Deploying site to Cloudflare Pages as {project_name}...")
    # In a real scenario, this would call the actual deployment script
    # For now, we use our scaffolded script which mocks the deployment
    result = subprocess.run([
        "./scripts/deploy_site.sh",
        project_name,
        dist_dir
    ], capture_output=True, text=True, check=True)
    
    # Extract URL from the mock output
    # Our mock script writes the URL to deploy_url.txt
    with open("deploy_url.txt", "r") as f:
        demo_url = f.read().strip()
    
    print(f"Lead processed! Demo URL: {demo_url}")
    return demo_url

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process a lead through the SiteFlow pipeline.')
    parser.add_argument('--id', required=True, help='Lead ID')
    parser.add_argument('--name', required=True, help='Business Name')
    parser.add_argument('--category', required=True, help='Category')
    parser.add_argument('--address', required=True, help='Address')
    parser.add_argument('--phone', required=True, help='Phone')
    
    args = parser.parse_args()
    
    process_lead(args.id, args.name, args.category, args.address, args.phone)
