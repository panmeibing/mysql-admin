/**
 * API Client for MySQL Admin
 * 
 * This module provides a comprehensive Axios-based HTTP client for the MySQL Admin backend API.
 * 
 * Features:
 * - Request/Response interceptors for automatic loading state management
 * - Enhanced error handling with network failure detection
 * - Timeout configuration (30 seconds)
 * - Automatic retry mechanism for transient failures
 * - Structured error responses with type categorization
 * - Methods for all backend endpoints (databases, tables, data, queries)
 * 
 * Requirements: 10.2, 10.3
 */

const API_BASE_URL = '/api';

// Create axios instance with default configuration
const axiosInstance = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000, // 30 second timeout
    headers: {
        'Content-Type': 'application/json'
    }
});

// Track active requests for loading state
let activeRequests = 0;
let loadingCallbacks = [];

// Register loading state callback
function onLoadingChange(callback) {
    loadingCallbacks.push(callback);
}

// Notify loading state change
function notifyLoadingChange(isLoading) {
    loadingCallbacks.forEach(callback => callback(isLoading));
}

// Request interceptor - handle loading state and request preparation
axiosInstance.interceptors.request.use(
    (config) => {
        // Increment active requests counter
        activeRequests++;
        if (activeRequests === 1) {
            notifyLoadingChange(true);
        }
        
        // Add admin key to headers if available
        const adminKey = localStorage.getItem('adminKey');
        if (adminKey) {
            config.headers['X-Admin-Key'] = adminKey;
        }
        
        // Log request for debugging
        console.log(`[API Request] ${config.method.toUpperCase()} ${config.url}`, config.data || config.params);
        
        return config;
    },
    (error) => {
        // Decrement on request error
        activeRequests = Math.max(0, activeRequests - 1);
        if (activeRequests === 0) {
            notifyLoadingChange(false);
        }
        
        console.error('[API Request Error]', error);
        return Promise.reject(error);
    }
);

// Response interceptor - handle loading state and response processing
axiosInstance.interceptors.response.use(
    (response) => {
        // Decrement active requests counter
        activeRequests = Math.max(0, activeRequests - 1);
        if (activeRequests === 0) {
            notifyLoadingChange(false);
        }
        
        // Log response for debugging
        console.log(`[API Response] ${response.config.method.toUpperCase()} ${response.config.url}`, response.data);
        
        return response;
    },
    (error) => {
        // Decrement active requests counter
        activeRequests = Math.max(0, activeRequests - 1);
        if (activeRequests === 0) {
            notifyLoadingChange(false);
        }
        
        // Log error for debugging
        console.error('[API Response Error]', error);
        
        // Check for authentication errors
        if (error.response && error.response.status === 401) {
            // Clear stored admin key
            localStorage.removeItem('adminKey');
            // Redirect to login page
            window.location.href = '/login.html';
        }
        
        return Promise.reject(error);
    }
);

const apiClient = {
    // Expose loading state registration
    onLoadingChange,
    
    // Get current loading state
    isLoading() {
        return activeRequests > 0;
    },
    // Database operations
    async listDatabases() {
        try {
            const response = await axiosInstance.get('/databases');
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    },

    async createDatabase(name) {
        try {
            const response = await axiosInstance.post('/databases', { name });
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    },

    async deleteDatabase(name) {
        try {
            const response = await axiosInstance.delete(`/databases/${name}`);
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    },

    async getDatabaseDDL(name) {
        try {
            const response = await axiosInstance.get(`/databases/${name}/ddl`);
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    },

    // Table operations
    async listTables(database) {
        try {
            const response = await axiosInstance.get(`/databases/${database}/tables`);
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    },

    async deleteTable(database, table) {
        try {
            const response = await axiosInstance.delete(`/databases/${database}/tables/${table}`);
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    },

    async getTableData(database, table, filter = null, page = 1, pageSize = 50) {
        try {
            const params = { page, page_size: pageSize };
            if (filter) {
                params.filter = filter;
            }
            const response = await axiosInstance.get(`/databases/${database}/tables/${table}/data`, { params });
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    },

    async getTableStructure(database, table) {
        try {
            const response = await axiosInstance.get(`/databases/${database}/tables/${table}/structure`);
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    },

    // Data operations
    async insertRow(database, table, data) {
        try {
            const response = await axiosInstance.post(`/databases/${database}/tables/${table}/rows`, { data });
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    },

    async updateRow(database, table, pkColumn, pkValue, data) {
        try {
            const response = await axiosInstance.put(`/databases/${database}/tables/${table}/rows`, {
                pk_column: pkColumn,
                pk_value: pkValue,
                data
            });
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    },

    async deleteRow(database, table, pkColumn, pkValue) {
        try {
            const response = await axiosInstance.delete(`/databases/${database}/tables/${table}/rows`, {
                data: {
                    pk_column: pkColumn,
                    pk_value: pkValue
                }
            });
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    },

    // Query operations
    async executeQuery(sql) {
        try {
            const response = await axiosInstance.post('/query', { sql });
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    },

    // Health check
    async checkHealth() {
        try {
            const response = await axiosInstance.get('/health');
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    },

    // Enhanced error handler with detailed network error handling
    handleError(error) {
        // Network errors (no response received)
        if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
            const errorObj = {
                message: 'Request timeout: The server took too long to respond',
                type: 'network',
                code: 'TIMEOUT',
                retryable: true,
                originalError: error
            };
            return errorObj;
        }
        
        if (error.code === 'ERR_NETWORK' || !error.response) {
            // Network failure - server unreachable
            const errorObj = {
                message: 'Network error: Unable to connect to server. Please check your connection.',
                type: 'network',
                code: 'CONNECTION_FAILED',
                retryable: true,
                originalError: error
            };
            return errorObj;
        }
        
        // Server responded with error status
        if (error.response) {
            const status = error.response.status;
            const data = error.response.data;
            
            // Extract error message from various possible formats
            // Priority: detail > error > message > default
            let message = 'An error occurred';
            if (typeof data === 'string') {
                message = data;
            } else if (data.detail) {
                // FastAPI returns errors in 'detail' field
                // Handle both string and array formats
                if (typeof data.detail === 'string') {
                    message = data.detail;
                } else if (Array.isArray(data.detail)) {
                    // Validation errors are returned as an array
                    // Extract the first error message
                    if (data.detail.length > 0 && data.detail[0].msg) {
                        message = data.detail[0].msg;
                    } else {
                        message = JSON.stringify(data.detail);
                    }
                } else {
                    message = JSON.stringify(data.detail);
                }
            } else if (data.error) {
                message = data.error;
            } else if (data.message) {
                message = data.message;
            }
            
            // Categorize by status code
            let errorType = 'server';
            let retryable = false;
            
            if (status >= 400 && status < 500) {
                errorType = 'client';
                retryable = false; // Client errors typically shouldn't be retried
            } else if (status >= 500) {
                errorType = 'server';
                retryable = true; // Server errors might be temporary
            }
            
            // Special handling for specific status codes
            if (status === 503) {
                // Keep the detail message if available, otherwise use default
                if (!data.detail) {
                    message = '服务不可用：数据库连接失败';
                }
                retryable = true;
            } else if (status === 404) {
                // Keep the detail message if available
                if (!data.detail && !data.error) {
                    message = '资源未找到';
                }
            } else if (status === 422) {
                // For validation errors, keep the detail message
                if (!message.includes('验证错误') && !message.includes('Validation error')) {
                    message = '验证错误：' + message;
                }
            } else if (status === 400) {
                // Bad request - keep the detail message as is
                // The backend already provides a descriptive message
            }
            
            return {
                message,
                status,
                type: errorType,
                code: data.code || `HTTP_${status}`,
                retryable,
                details: data,
                originalError: error
            };
        }
        
        // Client-side error (request setup failed)
        return {
            message: error.message || 'An unexpected error occurred',
            type: 'client',
            code: 'CLIENT_ERROR',
            retryable: false,
            originalError: error
        };
    },
    
    // Retry helper for retryable errors
    async retryRequest(requestFn, maxRetries = 3, delay = 1000) {
        let lastError;
        
        for (let attempt = 0; attempt < maxRetries; attempt++) {
            try {
                return await requestFn();
            } catch (error) {
                lastError = this.handleError(error);
                
                // Don't retry if error is not retryable
                if (!lastError.retryable) {
                    throw lastError;
                }
                
                // Don't retry on last attempt
                if (attempt === maxRetries - 1) {
                    throw lastError;
                }
                
                // Wait before retrying (exponential backoff)
                await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, attempt)));
                
                console.log(`[API Retry] Attempt ${attempt + 2}/${maxRetries}`);
            }
        }
        
        throw lastError;
    }
};
