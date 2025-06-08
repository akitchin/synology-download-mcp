import axios, { AxiosInstance } from 'axios';
import { Logger } from 'winston';

export interface SynologyConfig {
  host: string;
  port: number;
  username: string;
  password: string;
  https?: boolean;
}

export interface ApiInfo {
  path: string;
  minVersion: number;
  maxVersion: number;
}

export interface Task {
  id: string;
  type: string;
  username: string;
  title: string;
  size: string;
  status: string;
  status_extra?: any;
  additional?: {
    detail?: TaskDetail;
    transfer?: TaskTransfer;
    file?: TaskFile[];
    tracker?: TaskTracker[];
    peer?: TaskPeer[];
  };
}

export interface TaskDetail {
  destination: string;
  uri: string;
  create_time: string;
  priority: string;
  total_peers: number;
  connected_seeders: number;
  connected_leechers: number;
}

export interface TaskTransfer {
  size_downloaded: string;
  size_uploaded: string;
  speed_download: number;
  speed_upload: number;
}

export interface TaskFile {
  filename: string;
  size: string;
  size_downloaded: string;
  priority: string;
}

export interface TaskTracker {
  url: string;
  status: string;
  update_timer: number;
  seeds: number;
  peers: number;
}

export interface TaskPeer {
  address: string;
  agent: string;
  progress: number;
  speed_download: number;
  speed_upload: number;
}

export interface SearchResult {
  title: string;
  size: string;
  date: string;
  download_uri: string;
  external_link: string;
  peers: number;
  seeds: number;
  leechs: number;
  module_id: string;
  module_title: string;
}

export interface SearchModule {
  id: string;
  title: string;
  enabled: boolean;
}

export interface Statistics {
  speed_download: number;
  speed_upload: number;
  emule_speed_download?: number;
  emule_speed_upload?: number;
}

export class SynologyClient {
  private axios: AxiosInstance;
  private config: SynologyConfig;
  private sid?: string;
  private apiInfo: Record<string, ApiInfo> = {};
  private logger: Logger;

  constructor(config: SynologyConfig, logger: Logger) {
    this.config = config;
    this.logger = logger;
    
    const protocol = config.https ? 'https' : 'http';
    const baseURL = `${protocol}://${config.host}:${config.port}/webapi`;
    
    this.axios = axios.create({
      baseURL,
      timeout: 30000,
      validateStatus: () => true, // Don't throw on HTTP errors
    });
  }

  async connect(): Promise<void> {
    this.logger.info('Connecting to Synology Download Station...');
    
    // Get API info
    await this.getApiInfo();
    
    // Login
    await this.login();
    
    this.logger.info('Successfully connected to Synology Download Station');
  }

  async disconnect(): Promise<void> {
    if (this.sid) {
      await this.logout();
    }
  }

  private async getApiInfo(): Promise<void> {
    const apis = [
      'SYNO.API.Auth',
      'SYNO.DownloadStation.Info',
      'SYNO.DownloadStation.Schedule',
      'SYNO.DownloadStation.Task',
      'SYNO.DownloadStation.Statistic',
      'SYNO.DownloadStation.RSS.Site',
      'SYNO.DownloadStation.RSS.Feed',
      'SYNO.DownloadStation.BTSearch'
    ];

    const response = await this.axios.get('/query.cgi', {
      params: {
        api: 'SYNO.API.Info',
        version: 1,
        method: 'query',
        query: apis.join(',')
      }
    });

    if (response.data.success) {
      this.apiInfo = response.data.data;
      this.logger.debug('Retrieved API info', { apis: Object.keys(this.apiInfo) });
    } else {
      throw new Error(`Failed to get API info: ${JSON.stringify(response.data)}`);
    }
  }

  private async login(): Promise<void> {
    const authInfo = this.apiInfo['SYNO.API.Auth'];
    if (!authInfo) {
      throw new Error('Auth API not available');
    }

    const response = await this.axios.get(`/${authInfo.path}`, {
      params: {
        api: 'SYNO.API.Auth',
        version: Math.min(3, authInfo.maxVersion),
        method: 'login',
        account: this.config.username,
        passwd: this.config.password,
        session: 'DownloadStation',
        format: 'sid'
      }
    });

    if (response.data.success) {
      this.sid = response.data.data.sid;
      this.logger.debug('Login successful');
    } else {
      const errorMessages: Record<number, string> = {
        400: 'No such account or incorrect password',
        401: 'Account disabled',
        402: 'Permission denied',
        403: '2-step verification code required',
        404: 'Failed to authenticate 2-step verification code'
      };
      
      const error = response.data.error;
      const errorCode = typeof error === 'object' ? error.code : error;
      const errorMsg = errorMessages[errorCode] || `Unknown error: ${errorCode}`;
      throw new Error(`Login failed: ${errorMsg}`);
    }
  }

  private async logout(): Promise<void> {
    const authInfo = this.apiInfo['SYNO.API.Auth'];
    if (!authInfo || !this.sid) return;

    await this.axios.get(`/${authInfo.path}`, {
      params: {
        api: 'SYNO.API.Auth',
        version: 1,
        method: 'logout',
        session: 'DownloadStation',
        _sid: this.sid
      }
    });

    this.sid = undefined;
    this.logger.debug('Logout successful');
  }

  private ensureAuthenticated(): void {
    if (!this.sid) {
      throw new Error('Not authenticated. Please call connect() first.');
    }
  }

  // Task operations
  async listTasks(offset = 0, limit = -1, additional?: string[]): Promise<{ total: number; tasks: Task[] }> {
    this.ensureAuthenticated();
    
    const taskInfo = this.apiInfo['SYNO.DownloadStation.Task'];
    if (!taskInfo) throw new Error('Task API not available');

    const params: any = {
      api: 'SYNO.DownloadStation.Task',
      version: 1,
      method: 'list',
      offset,
      limit,
      _sid: this.sid
    };

    if (additional) {
      params.additional = additional.join(',');
    }

    const response = await this.axios.get(`/${taskInfo.path}`, { params });

    if (response.data.success) {
      return response.data.data;
    } else {
      throw new Error(`Failed to list tasks: ${JSON.stringify(response.data)}`);
    }
  }

  async getTaskInfo(ids: string[], additional?: string[]): Promise<Task[]> {
    this.ensureAuthenticated();
    
    const taskInfo = this.apiInfo['SYNO.DownloadStation.Task'];
    if (!taskInfo) throw new Error('Task API not available');

    const params: any = {
      api: 'SYNO.DownloadStation.Task',
      version: 1,
      method: 'getinfo',
      id: ids.join(','),
      _sid: this.sid
    };

    if (additional) {
      params.additional = additional.join(',');
    }

    const response = await this.axios.get(`/${taskInfo.path}`, { params });

    if (response.data.success) {
      return response.data.data.tasks;
    } else {
      throw new Error(`Failed to get task info: ${JSON.stringify(response.data)}`);
    }
  }

  async createTask(uri: string, destination?: string): Promise<void> {
    this.ensureAuthenticated();
    
    const taskInfo = this.apiInfo['SYNO.DownloadStation.Task'];
    if (!taskInfo) throw new Error('Task API not available');

    const params: any = {
      api: 'SYNO.DownloadStation.Task',
      version: 1,
      method: 'create',
      uri,
      _sid: this.sid
    };

    if (destination) {
      params.destination = destination;
    }

    const response = await this.axios.get(`/${taskInfo.path}`, { params });

    if (!response.data.success) {
      const errorMessages: Record<number, string> = {
        400: 'File upload failed',
        401: 'Max number of tasks reached',
        402: 'Destination denied',
        403: 'Destination does not exist',
        406: 'No default destination',
        408: 'File does not exist'
      };
      
      const error = response.data.error;
      const errorCode = typeof error === 'object' ? error.code : error;
      const errorMsg = errorMessages[errorCode] || `Unknown error: ${errorCode}`;
      throw new Error(`Failed to create task: ${errorMsg}`);
    }
  }

  async pauseTasks(ids: string[]): Promise<void> {
    this.ensureAuthenticated();
    
    const taskInfo = this.apiInfo['SYNO.DownloadStation.Task'];
    if (!taskInfo) throw new Error('Task API not available');

    const response = await this.axios.get(`/${taskInfo.path}`, {
      params: {
        api: 'SYNO.DownloadStation.Task',
        version: 1,
        method: 'pause',
        id: ids.join(','),
        _sid: this.sid
      }
    });

    if (!response.data.success) {
      throw new Error(`Failed to pause tasks: ${JSON.stringify(response.data)}`);
    }
  }

  async resumeTasks(ids: string[]): Promise<void> {
    this.ensureAuthenticated();
    
    const taskInfo = this.apiInfo['SYNO.DownloadStation.Task'];
    if (!taskInfo) throw new Error('Task API not available');

    const response = await this.axios.get(`/${taskInfo.path}`, {
      params: {
        api: 'SYNO.DownloadStation.Task',
        version: 1,
        method: 'resume',
        id: ids.join(','),
        _sid: this.sid
      }
    });

    if (!response.data.success) {
      throw new Error(`Failed to resume tasks: ${JSON.stringify(response.data)}`);
    }
  }

  async deleteTasks(ids: string[], forceComplete = false): Promise<void> {
    this.ensureAuthenticated();
    
    const taskInfo = this.apiInfo['SYNO.DownloadStation.Task'];
    if (!taskInfo) throw new Error('Task API not available');

    const params: any = {
      api: 'SYNO.DownloadStation.Task',
      version: 1,
      method: 'delete',
      id: ids.join(','),
      _sid: this.sid
    };

    if (forceComplete) {
      params.force_complete = true;
    }

    const response = await this.axios.get(`/${taskInfo.path}`, { params });

    if (!response.data.success) {
      throw new Error(`Failed to delete tasks: ${JSON.stringify(response.data)}`);
    }
  }

  // BT Search operations
  async getSearchModules(): Promise<SearchModule[]> {
    this.ensureAuthenticated();
    
    const btInfo = this.apiInfo['SYNO.DownloadStation.BTSearch'];
    if (!btInfo) throw new Error('BTSearch API not available');

    const response = await this.axios.get(`/${btInfo.path}`, {
      params: {
        api: 'SYNO.DownloadStation.BTSearch',
        version: 1,
        method: 'getModule',
        _sid: this.sid
      }
    });

    if (response.data.success) {
      return response.data.data.modules;
    } else {
      throw new Error(`Failed to get search modules: ${JSON.stringify(response.data)}`);
    }
  }

  async startSearch(keyword: string, module = 'enabled'): Promise<string> {
    this.ensureAuthenticated();
    
    const btInfo = this.apiInfo['SYNO.DownloadStation.BTSearch'];
    if (!btInfo) throw new Error('BTSearch API not available');

    const response = await this.axios.get(`/${btInfo.path}`, {
      params: {
        api: 'SYNO.DownloadStation.BTSearch',
        version: 1,
        method: 'start',
        keyword,
        module,
        _sid: this.sid
      }
    });

    if (response.data.success) {
      return response.data.data.taskid;
    } else {
      throw new Error(`Failed to start search: ${JSON.stringify(response.data)}`);
    }
  }

  async getSearchResults(
    taskId: string, 
    offset = 0, 
    limit = 50,
    sortBy = 'seeds',
    sortDirection = 'DESC'
  ): Promise<{
    finished: boolean;
    total: number;
    items: SearchResult[];
  }> {
    this.ensureAuthenticated();
    
    const btInfo = this.apiInfo['SYNO.DownloadStation.BTSearch'];
    if (!btInfo) throw new Error('BTSearch API not available');

    const response = await this.axios.get(`/${btInfo.path}`, {
      params: {
        api: 'SYNO.DownloadStation.BTSearch',
        version: 1,
        method: 'list',
        taskid: taskId,
        offset,
        limit,
        sort_by: sortBy,
        sort_direction: sortDirection,
        _sid: this.sid
      }
    });

    if (response.data.success) {
      return response.data.data;
    } else {
      throw new Error(`Failed to get search results: ${JSON.stringify(response.data)}`);
    }
  }

  async cleanSearch(taskId: string): Promise<void> {
    this.ensureAuthenticated();
    
    const btInfo = this.apiInfo['SYNO.DownloadStation.BTSearch'];
    if (!btInfo) throw new Error('BTSearch API not available');

    const response = await this.axios.get(`/${btInfo.path}`, {
      params: {
        api: 'SYNO.DownloadStation.BTSearch',
        version: 1,
        method: 'clean',
        taskid: taskId,
        _sid: this.sid
      }
    });

    if (!response.data.success) {
      throw new Error(`Failed to clean search: ${JSON.stringify(response.data)}`);
    }
  }

  // Statistics
  async getStatistics(): Promise<Statistics> {
    this.ensureAuthenticated();
    
    const statInfo = this.apiInfo['SYNO.DownloadStation.Statistic'];
    if (!statInfo) throw new Error('Statistic API not available');

    const response = await this.axios.get(`/${statInfo.path}`, {
      params: {
        api: 'SYNO.DownloadStation.Statistic',
        version: 1,
        method: 'getinfo',
        _sid: this.sid
      }
    });

    if (response.data.success) {
      return response.data.data;
    } else {
      throw new Error(`Failed to get statistics: ${JSON.stringify(response.data)}`);
    }
  }
}
