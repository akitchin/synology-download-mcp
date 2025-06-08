import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError
} from '@modelcontextprotocol/sdk/types.js';
import { SynologyClient, SynologyConfig } from './synology-client.js';
import winston from 'winston';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Configure logger - use stderr for all logs to avoid interfering with MCP protocol
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    // Use stderr for all logs to keep stdout clean for MCP protocol
    new winston.transports.Stream({
      stream: process.stderr,
      format: winston.format.simple()
    })
  ]
});

// Create Synology client
const config: SynologyConfig = {
  host: process.env.SYNOLOGY_HOST || '',
  port: parseInt(process.env.SYNOLOGY_PORT || '5000'),
  username: process.env.SYNOLOGY_USERNAME || '',
  password: process.env.SYNOLOGY_PASSWORD || '',
  https: process.env.SYNOLOGY_HTTPS === 'true'
};

if (!config.host || !config.username || !config.password) {
  logger.error('Missing required Synology configuration. Please set SYNOLOGY_HOST, SYNOLOGY_USERNAME, and SYNOLOGY_PASSWORD environment variables.');
  process.exit(1);
}

const synologyClient = new SynologyClient(config, logger);

// Define available tools
const TOOLS = [
  {
    name: 'list_downloads',
    description: 'List all download tasks with their status',
    inputSchema: {
      type: 'object',
      properties: {
        offset: {
          type: 'number',
          description: 'Starting position for results',
          default: 0
        },
        limit: {
          type: 'number',
          description: 'Maximum number of results (-1 for all)',
          default: 50
        },
        includeDetails: {
          type: 'boolean',
          description: 'Include detailed information about each task',
          default: false
        }
      }
    }
  },
  {
    name: 'get_download_info',
    description: 'Get detailed information about specific download tasks',
    inputSchema: {
      type: 'object',
      properties: {
        ids: {
          type: 'array',
          items: { type: 'string' },
          description: 'Task IDs to get info for'
        }
      },
      required: ['ids']
    }
  },
  {
    name: 'create_download',
    description: 'Create a new download task from URL, magnet link, or torrent',
    inputSchema: {
      type: 'object',
      properties: {
        uri: {
          type: 'string',
          description: 'URL, magnet link, or file path to download'
        },
        destination: {
          type: 'string',
          description: 'Optional destination folder'
        }
      },
      required: ['uri']
    }
  },
  {
    name: 'pause_downloads',
    description: 'Pause one or more download tasks',
    inputSchema: {
      type: 'object',
      properties: {
        ids: {
          type: 'array',
          items: { type: 'string' },
          description: 'Task IDs to pause'
        }
      },
      required: ['ids']
    }
  },
  {
    name: 'resume_downloads',
    description: 'Resume one or more paused download tasks',
    inputSchema: {
      type: 'object',
      properties: {
        ids: {
          type: 'array',
          items: { type: 'string' },
          description: 'Task IDs to resume'
        }
      },
      required: ['ids']
    }
  },
  {
    name: 'delete_downloads',
    description: 'Delete one or more download tasks',
    inputSchema: {
      type: 'object',
      properties: {
        ids: {
          type: 'array',
          items: { type: 'string' },
          description: 'Task IDs to delete'
        },
        forceComplete: {
          type: 'boolean',
          description: 'Force move incomplete files to destination',
          default: false
        }
      },
      required: ['ids']
    }
  },
  {
    name: 'search_torrents',
    description: 'Search for torrents using enabled search modules. Polls for results and resets timeout when new results arrive.',
    inputSchema: {
      type: 'object',
      properties: {
        keyword: {
          type: 'string',
          description: 'Search keyword'
        },
        waitForResults: {
          type: 'boolean',
          description: 'Wait for search to complete before returning',
          default: true
        },
        maxWaitTime: {
          type: 'number',
          description: 'Maximum total time to wait for search completion (seconds). Timeout resets when new results arrive.',
          default: 30
        }
      },
      required: ['keyword']
    }
  },
  {
    name: 'get_search_modules',
    description: 'Get list of available torrent search modules',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  },
  {
    name: 'check_search_status',
    description: 'Check the status of an ongoing search without waiting',
    inputSchema: {
      type: 'object',
      properties: {
        taskId: {
          type: 'string',
          description: 'Search task ID returned from search_torrents'
        },
        cleanAfterCheck: {
          type: 'boolean',
          description: 'Clean up the search task after checking',
          default: false
        }
      },
      required: ['taskId']
    }
  },
  {
    name: 'get_statistics',
    description: 'Get current download/upload statistics',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  }
];

// Create MCP server
const server = new Server(
  {
    name: 'synology-download-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {}
    },
  }
);

// Handle tool listing
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: TOOLS
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'list_downloads': {
        const offset = typeof args?.offset === 'number' ? args.offset : 0;
        const limit = typeof args?.limit === 'number' ? args.limit : 50;
        const includeDetails = args?.includeDetails === true;
        const additional = includeDetails ? ['detail', 'transfer'] : undefined;
        const result = await synologyClient.listTasks(offset, limit, additional);
        
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2)
            }
          ]
        };
      }

      case 'get_download_info': {
        const { ids } = args as { ids: string[] };
        if (!ids || !Array.isArray(ids)) {
          throw new McpError(ErrorCode.InvalidParams, 'ids array is required');
        }
        
        const tasks = await synologyClient.getTaskInfo(ids, ['detail', 'transfer', 'file', 'tracker', 'peer']);
        
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(tasks, null, 2)
            }
          ]
        };
      }

      case 'create_download': {
        const { uri, destination } = args as { uri: string; destination?: string };
        if (!uri) {
          throw new McpError(ErrorCode.InvalidParams, 'uri is required');
        }
        
        await synologyClient.createTask(uri, destination);
        
        return {
          content: [
            {
              type: 'text',
              text: `Successfully created download task for: ${uri}`
            }
          ]
        };
      }

      case 'pause_downloads': {
        const { ids } = args as { ids: string[] };
        if (!ids || !Array.isArray(ids)) {
          throw new McpError(ErrorCode.InvalidParams, 'ids array is required');
        }
        
        await synologyClient.pauseTasks(ids);
        
        return {
          content: [
            {
              type: 'text',
              text: `Successfully paused ${ids.length} task(s)`
            }
          ]
        };
      }

      case 'resume_downloads': {
        const { ids } = args as { ids: string[] };
        if (!ids || !Array.isArray(ids)) {
          throw new McpError(ErrorCode.InvalidParams, 'ids array is required');
        }
        
        await synologyClient.resumeTasks(ids);
        
        return {
          content: [
            {
              type: 'text',
              text: `Successfully resumed ${ids.length} task(s)`
            }
          ]
        };
      }

      case 'delete_downloads': {
        const { ids, forceComplete = false } = args as { ids: string[]; forceComplete?: boolean };
        if (!ids || !Array.isArray(ids)) {
          throw new McpError(ErrorCode.InvalidParams, 'ids array is required');
        }
        
        await synologyClient.deleteTasks(ids, forceComplete);
        
        return {
          content: [
            {
              type: 'text',
              text: `Successfully deleted ${ids.length} task(s)`
            }
          ]
        };
      }

      case 'search_torrents': {
        const { keyword, waitForResults = true, maxWaitTime = 30 } = args as { 
          keyword: string; 
          waitForResults?: boolean;
          maxWaitTime?: number;
        };
        
        if (!keyword) {
          throw new McpError(ErrorCode.InvalidParams, 'keyword is required');
        }
        
        const taskId = await synologyClient.startSearch(keyword);
        
        if (!waitForResults) {
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify({ taskId, status: 'searching' }, null, 2)
              }
            ]
          };
        }
        
        // Poll for results with progress tracking
        let results;
        let finished = false;
        let lastResultCount = 0;
        let lastProgressTime = Date.now();
        const startTime = Date.now();
        const pollInterval = 1000; // 1 second
        const progressTimeout = 10000; // 10 seconds without new results
        
        while (!finished) {
          // Check overall timeout
          if ((Date.now() - startTime) > maxWaitTime * 1000) {
            logger.warn(`Search timeout after ${maxWaitTime} seconds`);
            break;
          }
          
          // Check progress timeout
          if ((Date.now() - lastProgressTime) > progressTimeout) {
            logger.warn('Search stalled - no new results for 10 seconds');
            break;
          }
          
          // Wait before polling
          await new Promise(resolve => setTimeout(resolve, pollInterval));
          
          // Get current results
          try {
            results = await synologyClient.getSearchResults(taskId);
            finished = results.finished;
            
            // Check if we got new results
            if (results.total > lastResultCount) {
              logger.debug(`Search progress: ${results.total} results found`);
              lastResultCount = results.total;
              lastProgressTime = Date.now(); // Reset timeout on progress
            }
            
            // Log search status
            if (!finished && results.total > 0) {
              logger.debug(`Search in progress: ${results.total} results so far...`);
            }
          } catch (error) {
            logger.error('Error polling search results:', error);
            break;
          }
        }
        
        // Clean up search task
        try {
          await synologyClient.cleanSearch(taskId);
        } catch (error) {
          logger.error('Error cleaning search task:', error);
        }
        
        // Prepare response with search metadata
        const searchDuration = Math.round((Date.now() - startTime) / 1000);
        const response = {
          searchId: taskId,
          keyword: keyword,
          finished: finished,
          duration: searchDuration,
          total: results?.total || 0,
          items: results?.items || []
        };
        
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(response, null, 2)
            }
          ]
        };
      }

      case 'get_search_modules': {
        const modules = await synologyClient.getSearchModules();
        
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(modules, null, 2)
            }
          ]
        };
      }

      case 'check_search_status': {
        const { taskId, cleanAfterCheck = false } = args as { taskId: string; cleanAfterCheck?: boolean };
        
        if (!taskId) {
          throw new McpError(ErrorCode.InvalidParams, 'taskId is required');
        }
        
        try {
          const results = await synologyClient.getSearchResults(taskId);
          
          if (cleanAfterCheck && results.finished) {
            await synologyClient.cleanSearch(taskId);
          }
          
          const response = {
            taskId: taskId,
            finished: results.finished,
            total: results.total,
            itemCount: results.items.length
          };
          
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(response, null, 2)
              }
            ]
          };
        } catch (error) {
          throw new McpError(
            ErrorCode.InternalError,
            `Failed to check search status: ${error instanceof Error ? error.message : 'Unknown error'}`
          );
        }
      }

      case 'get_statistics': {
        const stats = await synologyClient.getStatistics();
        
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(stats, null, 2)
            }
          ]
        };
      }

      default:
        throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
    }
  } catch (error) {
    logger.error('Tool execution error:', error);
    
    if (error instanceof McpError) {
      throw error;
    }
    
    throw new McpError(
      ErrorCode.InternalError,
      error instanceof Error ? error.message : 'Unknown error occurred'
    );
  }
});

// Start server
async function main() {
  try {
    // Connect to Synology
    await synologyClient.connect();
    logger.info('Connected to Synology Download Station');

    // Start MCP server
    const transport = new StdioServerTransport();
    await server.connect(transport);
    logger.info('Synology Download MCP server started');

    // Handle shutdown
    process.on('SIGINT', async () => {
      logger.info('Shutting down...');
      await synologyClient.disconnect();
      await server.close();
      process.exit(0);
    });

  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
}

main().catch((error) => {
  logger.error('Fatal error:', error);
  process.exit(1);
});
