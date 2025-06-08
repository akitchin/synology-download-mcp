#!/bin/bash

# Build and run Synology Download MCP in Docker

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building Synology Download MCP Docker image...${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}Please edit .env file with your Synology credentials before running.${NC}"
    exit 1
fi

# Build Docker image
docker build -t synology-download-mcp:latest .

echo -e "${GREEN}Docker image built successfully!${NC}"

# Ask if user wants to run the container
read -p "Do you want to start the MCP server now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Starting Synology Download MCP server...${NC}"
    docker-compose up -d
    
    echo -e "${GREEN}Server started successfully!${NC}"
    echo
    echo "To view logs: docker-compose logs -f"
    echo "To stop: docker-compose down"
    echo
    echo "Add this to your Claude Desktop config:"
    echo '
{
  "mcpServers": {
    "synology-download": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "--env-file", "'$(pwd)'/.env", "synology-download-mcp:latest"]
    }
  }
}'
fi
