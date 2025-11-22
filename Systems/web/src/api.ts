export interface BotUser {
    id: number;
    username: string;
    first_name?: string;
    last_name?: string;
    role: string;
    avatar?: string;
    is_blocked: boolean;
}

export interface BotModule {
    name: string;
    status: 'active' | 'inactive';
    description?: string;
    display_name?: string;
    is_system_module?: boolean;
    version?: string | null;
}

export interface Profile {
    username: string;
    first_name?: string;
    last_name?: string;
    role: string;
}

export interface BotStats {
    uptime?: string;
    messages_today?: number;
    total_users?: number;
    active_modules?: number;
    total_modules?: number;
}

export interface BotLog {
    level: string;
    message: string;
    timestamp: string;
}

export interface SystemMetrics {
    cpu: number;
    ram: number;
    ramUsed: number;
    ramTotal: number;
    disk: number;
    diskUsed: number;
    diskTotal: number;
    redis: number;
    redisUsed: number;
    redisTotal: number;
    dbConnections: number;
}

export interface LiveMetrics {
    rps: number;
    responseTime: number;
    errorRate: number;
    activeUsers: number;
    newUsersToday: number;
    queueSize: number;
}

export interface Service {
    id: string;
    name: string;
    description: string;
    status: 'running' | 'stopped' | 'restarting';
    uptime: string;
    memory: string;
}

export interface FeatureFlag {
    name: string;
    enabled: boolean;
    description: string;
}

export interface Session {
    id: string;
    device: string;
    location: string;
    lastActivity: string;
    current: boolean;
    ip: string;
}

export interface Token {
    id: string;
    name: string;
    created: string;
    lastUsed: string | null;
    token?: string;
}

export interface CommandHistoryItem {
    id: number;
    command: string;
    date: string;
    status: string;
}

export interface FileItem {
    id: number;
    name: string;
    size: string;
    uploadDate: string;
}

export interface Ticket {
    id: string;
    subject: string;
    status: string;
    created: string;
    updated: string;
}

export interface CronJob {
    id: string;
    name: string;
    func: string;
    next_run_time: string | null;
    trigger: string | null;
}

export interface AuditLog {
    event_id: string;
    event_type: string;
    module_name: string;
    user_id: number | null;
    timestamp: number;
    severity: 'low' | 'medium' | 'high' | 'critical';
    details: Record<string, any>;
    ip_address: string | null;
    user_agent: string | null;
    success: boolean;
    error_message: string | null;
}

export interface AuditStats {
    total_events: number;
    events_by_type: Record<string, number>;
    events_by_severity: Record<string, number>;
    events_by_module: Record<string, number>;
    violations_count: number;
}

export interface ApiKey {
    name: string;
    permissions: string;
    created_at: string;
    expires_at: string | null;
    last_used: string | null;
    usage_count: number;
}

export interface Migration {
    revision: string;
    down_revision: string | null;
    branch_labels: string[];
    is_current: boolean;
    doc: string;
}

export interface CacheKey {
    key: string;
    ttl: number | null;
}

export interface Broadcast {
    id: string;
    message: string;
    target_type: 'all' | 'admins' | 'role' | 'active' | 'inactive' | 'new_users' | 'language' | 'active_status';
    target_count: number;
    sent_count?: number;
    error_count?: number;
    status: 'queued' | 'sending' | 'completed' | 'completed_with_errors' | 'failed';
    created_at: string;
    schedule_time?: string | null;
    note?: string;
}

export interface BroadcastProgress {
    sent: number;
    total: number;
    errors: number;
    status: 'sending' | 'completed' | 'failed' | 'unknown';
}

export const api = {
    loginWithToken: async (token: string) => {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token }),
        });
        if (!response.ok) throw new Error('Login failed');
        return response.json();
    },

    checkCloudPasswordSetup: async () => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/auth/cloud-password/check', {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Check failed');
        return response.json();
    },

    setupCloudPassword: async (password: string) => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/auth/cloud-password/setup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ password }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Setup failed' }));
            throw new Error(error.detail || 'Setup failed');
        }
        return response.json();
    },

    verifyCloudPassword: async (password: string) => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/auth/cloud-password/verify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ password }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Verification failed' }));
            throw new Error(error.detail || 'Verification failed');
        }
        return response.json();
    },

    logout: async () => {
        await fetch('/api/auth/logout', { method: 'POST' });
    }
,

    getUsers: async (): Promise<BotUser[]> => {
        const response = await fetch('/api/users');
        if (!response.ok) throw new Error('Failed to load users');
        return response.json();
    },

    toggleUserBlockStatus: async (userId: number, block: boolean) => {
        const response = await fetch(`/api/users/${userId}/block`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ block }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Toggle failed' }));
            throw new Error(error.detail || 'Toggle failed');
        }
        return response.json();
    },

    getModules: async (includeSystem: boolean = false): Promise<BotModule[]> => {
        const response = await fetch(`/api/modules?include_system=${includeSystem}`);
        if (!response.ok) throw new Error('Failed to load modules');
        return response.json();
    },

    toggleModuleStatus: async (moduleName: string, enable: boolean) => {
        const response = await fetch(`/api/modules/${moduleName}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enable }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Toggle failed' }));
            throw new Error(error.detail || 'Toggle failed');
        }
        return response.json();
    },

    getStats: async (): Promise<BotStats> => {
        const response = await fetch('/api/stats');
        if (!response.ok) throw new Error('Failed to load stats');
        return response.json();
    },

    getLogs: async (limit: number = 100, level?: string): Promise<BotLog[]> => {
        const params = new URLSearchParams();
        if (limit) params.append('limit', limit.toString());
        if (level) params.append('level', level);
        const response = await fetch(`/api/logs?${params.toString()}`);
        if (!response.ok) throw new Error('Failed to load logs');
        return response.json();
    },

    getSystemMetrics: async (): Promise<SystemMetrics> => {
        const response = await fetch('/api/metrics/system');
        if (!response.ok) throw new Error('Failed to load system metrics');
        return response.json();
    },

    getLiveMetrics: async (): Promise<LiveMetrics> => {
        const response = await fetch('/api/metrics/live');
        if (!response.ok) throw new Error('Failed to load live metrics');
        return response.json();
    },

    getServices: async (): Promise<Service[]> => {
        const response = await fetch('/api/services');
        if (!response.ok) throw new Error('Failed to load services');
        return response.json();
    },

    serviceAction: async (serviceId: string, action: 'start' | 'stop' | 'restart'): Promise<void> => {
        const response = await fetch(`/api/services/${serviceId}/${action}`, {
            method: 'POST',
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Action failed' }));
            throw new Error(error.detail || 'Action failed');
        }
    },

    getConfig: async (): Promise<{content: string}> => {
        const response = await fetch('/api/config');
        if (!response.ok) throw new Error('Failed to load config');
        return response.json();
    },

    updateConfig: async (content: string): Promise<void> => {
        const response = await fetch('/api/config', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Update failed' }));
            throw new Error(error.detail || 'Update failed');
        }
    },

    reloadConfig: async (): Promise<{success: boolean, message: string}> => {
        const response = await fetch('/api/config/reload', {
            method: 'POST',
        });
        if (!response.ok) throw new Error('Failed to reload config');
        return response.json();
    },

    getFeatureFlags: async (): Promise<FeatureFlag[]> => {
        const response = await fetch('/api/feature-flags');
        if (!response.ok) throw new Error('Failed to load feature flags');
        return response.json();
    },

    updateFeatureFlag: async (name: string, enabled: boolean): Promise<void> => {
        const response = await fetch(`/api/feature-flags/${name}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Update failed' }));
            throw new Error(error.detail || 'Update failed');
        }
    },

    getSessions: async (): Promise<Session[]> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/sessions', {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load sessions');
        return response.json();
    },

    terminateSession: async (sessionId: string): Promise<void> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch(`/api/sessions/${sessionId}/terminate`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Terminate failed' }));
            throw new Error(error.detail || 'Terminate failed');
        }
    },

    getTokens: async (): Promise<Token[]> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/tokens', {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load tokens');
        return response.json();
    },

    createToken: async (name: string): Promise<{token: string, id: string, name: string, created: string, lastUsed: string | null}> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/tokens', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ name }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Create failed' }));
            throw new Error(error.detail || 'Create failed');
        }
        return response.json();
    },

    revokeToken: async (tokenId: string): Promise<void> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch(`/api/tokens/${tokenId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Revoke failed' }));
            throw new Error(error.detail || 'Revoke failed');
        }
    },

    getCommandHistory: async (limit?: number): Promise<CommandHistoryItem[]> => {
        const token = localStorage.getItem('sdb_token');
        const params = limit ? `?limit=${limit}` : '';
        const response = await fetch(`/api/command-history${params}`, {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load command history');
        return response.json();
    },

    getFiles: async (): Promise<FileItem[]> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/files', {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load files');
        return response.json();
    },

    getTickets: async (): Promise<Ticket[]> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/tickets', {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load tickets');
        return response.json();
    },

    createTicket: async (subject: string, message: string): Promise<Ticket> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/tickets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ subject, message }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Create failed' }));
            throw new Error(error.detail || 'Create failed');
        }
        return response.json();
    },

    executeTerminalCommand: async (command: string): Promise<{output: string, success: boolean, timestamp: string}> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/terminal/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ command }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Execute failed' }));
            throw new Error(error.detail || 'Execute failed');
        }
        return response.json();
    },

    getCronJobs: async (): Promise<CronJob[]> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/cron-jobs', {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load cron jobs');
        return response.json();
    },

    streamLogs: async (limit?: number, level?: string): Promise<BotLog[]> => {
        const token = localStorage.getItem('sdb_token');
        const query = new URLSearchParams();
        if (limit) query.append('limit', limit.toString());
        if (level) query.append('level', level);
        const response = await fetch(`/api/logs/stream?${query.toString()}`, {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to stream logs');
        return response.json();
    },

    getAuditLogs: async (params?: {
        limit?: number;
        module_name?: string;
        event_type?: string;
        severity?: string;
        start_time?: number;
        end_time?: number;
    }): Promise<AuditLog[]> => {
        const token = localStorage.getItem('sdb_token');
        const query = new URLSearchParams();
        if (params) {
            if (params.limit) query.append('limit', params.limit.toString());
            if (params.module_name) query.append('module_name', params.module_name);
            if (params.event_type) query.append('event_type', params.event_type);
            if (params.severity) query.append('severity', params.severity);
            if (params.start_time) query.append('start_time', params.start_time.toString());
            if (params.end_time) query.append('end_time', params.end_time.toString());
        }
        const response = await fetch(`/api/audit-logs?${query.toString()}`, {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load audit logs');
        return response.json();
    },

    getAuditStats: async (): Promise<AuditStats> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/audit-stats', {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load audit stats');
        return response.json();
    },

    getApiKeys: async (): Promise<ApiKey[]> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/api-keys', {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load API keys');
        return response.json();
    },

    executeSqlQuery: async (query: string): Promise<{columns: string[], data: Record<string, any>[], row_count: number}> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/database/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ query }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Query failed' }));
            throw new Error(error.detail || 'Query failed');
        }
        return response.json();
    },

    getMigrations: async (): Promise<Migration[]> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/migrations', {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load migrations');
        return response.json();
    },

    migrationAction: async (action: 'upgrade' | 'downgrade', revision?: string): Promise<{success: boolean, message: string}> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch(`/api/migrations/${action}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ revision }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Migration action failed' }));
            throw new Error(error.detail || 'Migration action failed');
        }
        return response.json();
    },

    getCacheKeys: async (pattern?: string, limit?: number): Promise<CacheKey[]> => {
        const token = localStorage.getItem('sdb_token');
        const query = new URLSearchParams();
        if (pattern) query.append('pattern', pattern);
        if (limit) query.append('limit', limit.toString());
        const response = await fetch(`/api/cache/keys?${query.toString()}`, {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load cache keys');
        return response.json();
    },

    flushCache: async (): Promise<{success: boolean, message: string}> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/cache/flush', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Flush failed' }));
            throw new Error(error.detail || 'Flush failed');
        }
        return response.json();
    },

    getBroadcasts: async (): Promise<Broadcast[]> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/broadcasts', {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load broadcasts');
        return response.json();
    },

    createBroadcast: async (data: {
        message: string;
        target_type: 'all' | 'admins' | 'role' | 'active' | 'inactive' | 'new_users' | 'language' | 'active_status';
        target_value?: string | number;
        schedule_time?: string | null;
    }): Promise<Broadcast> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch('/api/broadcasts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Create failed' }));
            throw new Error(error.detail || 'Create failed');
        }
        return response.json();
    },

    getBroadcastProgress: async (broadcastId: string): Promise<BroadcastProgress> => {
        const token = localStorage.getItem('sdb_token');
        const response = await fetch(`/api/broadcasts/${broadcastId}/progress`, {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load progress');
        return response.json();
    }
};
