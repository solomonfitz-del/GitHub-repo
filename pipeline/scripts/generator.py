import os
import json
import argparse
from pathlib import Path

def generate_site(lead_data, template_path, output_dir):
    with open(template_path, 'r') as f:
        template = f.read()

    # Data to replace
    business_name = lead_data.get('name', 'Your Business')
    category = lead_data.get('category', 'Local Business')
    address = lead_data.get('address', 'Local Area')
    phone = lead_data.get('phone', 'Call Us Today')
    photos = lead_data.get('photos', [])
    hero_image_url = lead_data.get('hero_image_url', "")

    # Basic replacements
    html = template
    replacements = {
        '{{ business_name }}': business_name,
        '{{ category }}': category,
        '{{ address }}': address,
        '{{ phone }}': phone,
        '{{ hero_image_url }}': hero_image_url if hero_image_url else "https://images.unsplash.com/photo-1581094794329-c8112a89af12?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80"
    }

    for key, value in replacements.items():
        html = html.replace(key, str(value))

    # Handle the photo loop
    start_tag = '{% for photo in photos %}'
    end_tag = '{% endfor %}'
    
    if start_tag in html and end_tag in html:
        parts = html.split(start_tag)
        before_loop = parts[0]
        loop_content_template = parts[1].split(end_tag)[0]
        after_loop = parts[1].split(end_tag)[1]
        
        loop_html = ""
        for photo in photos:
            loop_html += loop_content_template.replace('{{ photo }}', photo)
        
        html = before_loop + loop_html + after_loop

    # Handle the "if not photos" block
    if '{% if not photos %}' in html and '{% endif %}' in html:
        parts = html.split('{% if not photos %}')
        before_if = parts[0]
        if_content = parts[1].split('{% endif %}')[0]
        after_if = parts[1].split('{% endif %}')[1]
        
        if not photos:
            html = before_if + if_content + after_if
        else:
            html = before_if + after_if

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
    parser.add_argument('--hero', type=str, help='Hero image URL')
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
            'hero_image_url': args.hero,
            'photos': args.photos or []
        }

    template_path = Path(__file__).parent.parent / 'templates' / 'index.html'
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    generate_site(lead_data, template_path, output_dir)
