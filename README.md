# Synology Download Station MCP Server

A Model Context Protocol (MCP) server that provides tools for interacting with Synology Download Station. This server enables AI assistants to manage downloads, search for torrents, and monitor download statistics on your Synology NAS.

## Features

- **Download Management**: List, create, pause, resume, and delete download tasks
- **Torrent Search**: Search for torrents using multiple search engines
- **Statistics**: Monitor real-time download/upload speeds
- **Detailed Information**: Get comprehensive details about downloads including peers, trackers, and file lists

## Installation

### Using npm

```bash
npm install @akitchin/synology-download-mcp
```

### Using Docker

```bash
# Build the image
docker build -t synology-download-mcp .

# Run with docker-compose
docker-compose up -d
```

## Configuration

Create a `.env` file with your Synology credentials:

```env
SYNOLOGY_HOST=192.168.1.41
SYNOLOGY_PORT=5000
SYNOLOGY_USERNAME=your_username
SYNOLOGY_PASSWORD=your_password
SYNOLOGY_HTTPS=false
LOG_LEVEL=info
```

## Available Tools

### list_downloads
List all download tasks with their current status.

**Parameters:**
- `offset` (number, optional): Starting position for results (default: 0)
- `limit` (number, optional): Maximum number of results, -1 for all (default: 50)
- `includeDetails` (boolean, optional): Include detailed information (default: false)

### get_download_info
Get detailed information about specific download tasks.

**Parameters:**
- `ids` (string[], required): Array of task IDs to get info for

### create_download
Create a new download task from URL, magnet link, or torrent file.

**Parameters:**
- `uri` (string, required): URL, magnet link, or file path to download
- `destination` (string, optional): Destination folder on the NAS

### pause_downloads
Pause one or more download tasks.

**Parameters:**
- `ids` (string[], required): Array of task IDs to pause

### resume_downloads
Resume one or more paused download tasks.

**Parameters:**
- `ids` (string[], required): Array of task IDs to resume

### delete_downloads
Delete one or more download tasks.

**Parameters:**
- `ids` (string[], required): Array of task IDs to delete
- `forceComplete` (boolean, optional): Force move incomplete files to destination (default: false)

### search_torrents
Search for torrents using enabled search modules with intelligent timeout handling.

**Parameters:**
- `keyword` (string, required): Search keyword
- `waitForResults` (boolean, optional): Wait for search to complete (default: true)
- `maxWaitTime` (number, optional): Maximum total time to wait for search completion in seconds (default: 30)

**Features:**
- Polls for results every second
- Resets timeout when new results arrive (progress-based timeout)
- Stops if no new results for 10 seconds
- Returns partial results if search times out
- Includes search metadata (duration, total results, finish status)

### check_search_status
Check the status of an ongoing search without waiting.

**Parameters:**
- `taskId` (string, required): Search task ID returned from search_torrents
- `cleanAfterCheck` (boolean, optional): Clean up the search task after checking (default: false)

### get_search_modules
Get list of available torrent search modules and their status.

### get_statistics
Get current download/upload statistics.

## Usage with Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "synology-download": {
      "command": "docker",
      "args": ["run", "--rm", "-i", 
        "-e", "SYNOLOGY_HOST=192.168.1.41",
        "-e", "SYNOLOGY_PORT=5000",
        "-e", "SYNOLOGY_USERNAME=your_username",
        "-e", "SYNOLOGY_PASSWORD=your_password",
        "synology-download-mcp:latest"
      ]
    }
  }
}
```

Or if running locally:

```json
{
  "mcpServers": {
    "synology-download": {
      "command": "node",
      "args": ["/path/to/synology-download-mcp/dist/index.js"],
      "env": {
        "SYNOLOGY_HOST": "192.168.1.41",
        "SYNOLOGY_PORT": "5000",
        "SYNOLOGY_USERNAME": "your_username",
        "SYNOLOGY_PASSWORD": "your_password"
      }
    }
  }
}
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/akitchin/synology-download-mcp.git
cd synology-download-mcp

# Install dependencies
npm install

# Copy environment file
cp .env.example .env
# Edit .env with your Synology credentials

# Build TypeScript
npm run build

# Run in development mode
npm run dev
```

### Testing

```bash
# Run the test scripts
python3 test_synology_api.py
python3 test_bt_search.py
```

## Security Considerations

- Store credentials securely using environment variables
- Use HTTPS when connecting over untrusted networks
- Consider using a dedicated Synology user with limited permissions
- The Docker container runs as a non-root user for security

## Troubleshooting

### Connection Issues
- Verify your Synology NAS is accessible from the host
- Check that Download Station is installed and running
- Ensure the user has appropriate permissions in DSM

### Authentication Errors
- Verify username and password are correct
- Check if 2-factor authentication is enabled (not currently supported)
- Ensure the account is not disabled

### Search Not Working
- Verify BT search modules are enabled in Download Station
- Some search engines may require additional configuration

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
# synology-download-mcp
