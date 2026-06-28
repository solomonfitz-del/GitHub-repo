import os
import json
import argparse
from pathlib import Path

def generate_site(business_data, template_path, output_dir):
    """
    Generates a static site from business data and a template.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the template
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Define placeholders and their values
    # In a real scenario, we might want to use a template engine like Jinja2
    replacements = {
        '{{business_name}}': business_data.get('business_name', 'Your Business'),
        '{{business_category}}': business_data.get('category', 'Professional Services'),
        '{{business_address}}': business_data.get('address', 'Your Address'),
        '{{business_phone}}': business_data.get('phone', 'Your Phone Number'),
        '{{hero_image_url}}': business_data.get('hero_image_url', 'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&q=80&w=1200'),
    }
    
    # Replace placeholders
    site_content = template_content
    for placeholder, value in replacements.items():
        site_content = site_content.replace(placeholder, value)
    
    # Write the generated site to index.html
    output_path = os.path.join(output_dir, 'index.html')
    with open(output_path, 'w') as f:
        f.write(site_content)
    
    print(f"Site generated successfully at {output_path}")
    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate a static site for a business.')
    parser.add_argument('--data', type=str, help='JSON string or path to JSON file containing business data')
    parser.add_argument('--template', type=str, default='templates/index.html', help='Path to the HTML template')
    parser.add_argument('--output', type=str, default='dist', help='Output directory')
    
    args = parser.parse_args()
    
    if args.data.startswith('{'):
        business_data = json.loads(args.data)
    else:
        with open(args.data, 'r') as f:
            business_data = json.load(f)
            
    generate_site(business_data, args.template, args.output)
