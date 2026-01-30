#!/bin/sh
set -e

# Create runtime .env file from environment variables if they exist
if [ ! -z "$VITE_COMPLIANCE_AGENT_API_URL" ]; then
  echo "VITE_COMPLIANCE_AGENT_API_URL=$VITE_COMPLIANCE_AGENT_API_URL" > .env
fi
# if [ ! -z "$VITE_MAPPER_API_URL" ]; then
#   echo "VITE_MAPPER_API_URL=$VITE_MAPPER_API_URL" >> .env
# fi
# if [ ! -z "$VITE_ALLOCATOR_API_URL" ]; then
#   echo "VITE_ALLOCATOR_API_URL=$VITE_ALLOCATOR_API_URL" >> .env
# fi
# if [ ! -z "$VITE_DEPLOYER_API_URL" ]; then
#   echo "VITE_DEPLOYER_API_URL=$VITE_DEPLOYER_API_URL" >> .env
# fi

# Rebuild with runtime environment variables
echo "Building UI with runtime environment variables..."
npm run build

# Serve the built application
echo "Starting UI server on port 3000..."
npx serve -s dist -l 3000