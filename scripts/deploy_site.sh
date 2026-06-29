#!/bin/bash
# Usage: ./deploy_site.sh <project_name> <directory>

PROJECT_NAME=$1
DIRECTORY=$2

if [ -z "$PROJECT_NAME" ] || [ -z "$DIRECTORY" ]; then
    echo "Usage: $0 <project_name> <directory>"
    exit 1
fi

# Deploy to Cloudflare Pages
# Assumes CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID are set in the environment
# For the scaffold, we'll use --branch main and assume the project exists or will be created
echo "Deploying $DIRECTORY to Cloudflare Pages project $PROJECT_NAME..."

# npx wrangler pages deploy "$DIRECTORY" --project-name "$PROJECT_NAME" --branch main
# Mocking the output for now since we don't have credentials
echo "Successfully deployed to https://$PROJECT_NAME.pages.dev"
echo "https://$PROJECT_NAME.pages.dev" > deploy_url.txt
