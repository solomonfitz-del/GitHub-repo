import os
import json
import argparse
from pathlib import Path

def generate_site(lead_data, template_path, output_dir):
    with open(template_path, 'r') as f:
        template = f.read()

    # Simple placeholder replacement
    # For photos, we'll do a simple loop replacement
    
    business_name = lead_data.get('name', 'Your Business')
    category = lead_data.get('category', 'Local Business')
    address = lead_data.get('address', '123 Main St, Your Town')
    phone = lead_data.get('phone', '(555) 000-0000')
    photos = lead_data.get('photos', [])

    html = template.replace('{{ business_name }}', business_name)
    html = html.replace('{{ category }}', category)
    html = html.replace('{{ address }}', address)
    html = html.replace('{{ phone }}', phone)

    # Handle the photo loop (very basic)
    photo_html = ""
    for photo in photos:
        photo_html += f'<img src="{photo}" alt="{business_name} photo">\n'
    
    if not photos:
        photo_html = "<p>No photos available yet.</p>"

    # This is a bit hacky but works for a basic generator without Jinja2
    start_tag = '{% for photo in photos %}'
    end_tag = '{% endfor %}'
    
    if start_tag in html and end_tag in html:
        before = html.split(start_tag)[0]
        after = html.split(end_tag)[1]
        
        # Check for the 'if not photos' block too
        if '{% if not photos %}' in after:
            after = after.split('{% endif %}')[1]
            
        html = before + photo_html + after

    output_path = Path(output_dir) / 'index.html'
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"Generated site for {business_name} at {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate a demo site for a lead.')
    parser.add_argument('--data', type=str, help='Path to lead JSON data')
    parser.add_argument('--name', type=str, help='Business name')
    parser.add_argument('--category', type=str, help='Business category')
    parser.add_argument('--address', type=str, help='Business address')
    parser.add_argument('--phone', type=str, help='Business phone')
    parser.add_argument('--photos', nargs='*', help='List of photo URLs')
    parser.add_argument('--output', type=str, default='output', help='Output directory')

    args = parser.parse_args()

    lead_data = {}
    if args.data:
        with open(args.data, 'r') as f:
            lead_data = json.load(f)
    else:
        lead_data = {
            'name': args.name,
            'category': args.category,
            'address': args.address,
            'phone': args.phone,
            'photos': args.photos or []
        }

    template_path = Path(__file__).parent / 'templates' / 'index.html'
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    generate_site(lead_data, template_path, output_dir)
