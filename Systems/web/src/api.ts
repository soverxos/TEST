export interface BotUser {
    id: number;
    username: string;
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
    role: string;
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

    getModules: async (): Promise<BotModule[]> => {
        const response = await fetch('/api/modules');
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
    }
};
