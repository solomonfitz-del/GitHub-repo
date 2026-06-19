# SiteForge Demo Site Generator

This tool generates static demo websites for local businesses based on lead data.

## Directory Structure

- `generator.py`: Python script to generate the site.
- `templates/`: Contains HTML/CSS templates.
- `output/`: Default directory for generated sites.

## Usage

You can generate a site by providing command line arguments:

```bash
python3 generator.py --name "Business Name" --category "Category" --address "Address" --phone "Phone" --photos "URL1" "URL2" --output output/business-name
```

Alternatively, you can provide a JSON file:

```bash
python3 generator.py --data lead.json --output output/business-name
```

Example `lead.json`:

```json
{
    "name": "Joe's Pizza",
    "category": "Restaurant",
    "address": "123 Pizza Way, New York, NY",
    "phone": "212-555-1234",
    "photos": [
        "https://images.unsplash.com/photo-1513104890138-7c749659a591",
        "https://images.unsplash.com/photo-1574129924497-cd718c698ee7"
    ]
}
```

## Deployment

To deploy the generated site, you can use Vercel or Netlify CLI.

### Vercel

1. Install Vercel CLI: `npm install -g vercel`
2. Navigate to the output directory: `cd output/business-name`
3. Deploy: `vercel --prod`

### Netlify

1. Install Netlify CLI: `npm install -g netlify-cli`
2. Navigate to the output directory: `cd output/business-name`
3. Deploy: `netlify deploy --prod --dir .`
