// Main Vue.js Application
const { createApp } = Vue;
const { ElMessage, ElMessageBox } = ElementPlus;

const app = createApp({
    data() {
        return {
            // Connection state
            connectionStatus: 'disconnected',
            
            // Loading states
            loading: false,
            globalLoading: false,
            
            // Database data
            databases: [],
            databaseTree: [],
            
            // Selected items
            selectedDatabase: null,
            selectedTable: null,
            currentDatabase: null, // Currently active database (for USE statement)
            
            // UI state
            activeTab: 'table',
            showCreateDatabaseDialog: false,
            
            // Forms
            newDatabase: {
                name: ''
            },
            
            // Context menu
            showContextMenu: false,
            contextMenuStyle: {
                position: 'fixed',
                left: '0px',
                top: '0px',
                zIndex: 9999
            },
            contextMenuType: null,
            contextMenuData: null,
            
            // Tree props
            treeProps: {
                children: 'children',
                label: 'label'
            },
            
            // Query editor
            sqlEditor: null,
            queryResults: null,
            queryLoading: false,
            
            // Table viewer
            tableData: {
                columns: [],
                rows: [],
                total: 0
            },
            tableStructure: [],
            currentPage: 1,
            pageSize: 50,
            tableLoading: false,
            
            // Row editing
            editingRow: null,
            editingRowIndex: -1,
            editingRowData: {},
            selectedRows: [],
            
            // Add row dialog
            showAddRowDialog: false,
            newRowData: {},
            
            // Filter
            filterCondition: '',
            activeFilter: null
        };
    },
    
    async mounted() {
        // Check authentication first
        const adminKey = localStorage.getItem('adminKey');
        if (!adminKey) {
            // No admin key, redirect to login
            window.location.href = '/login.html';
            return;
        }
        
        // Initialize Ace Editor
        this.initializeSqlEditor();
        
        // Check connection and load databases
        await this.checkConnection();
        
        // Set up axios interceptors for loading states
        this.setupAxiosInterceptors();
        
        // Add global click listener to hide context menu
        document.addEventListener('click', this.hideContextMenu);
    },
    
    beforeUnmount() {
        // Clean up event listeners
        document.removeEventListener('click', this.hideContextMenu);
    },
    
    methods: {
        // Initialize SQL Editor
        initializeSqlEditor() {
            this.sqlEditor = ace.edit('sql-editor');
            this.sqlEditor.setTheme('ace/theme/monokai');
            this.sqlEditor.session.setMode('ace/mode/sql');
            this.sqlEditor.setOptions({
                fontSize: '14px',
                showPrintMargin: false,
                enableBasicAutocompletion: true,
                enableLiveAutocompletion: true
            });
            this.sqlEditor.setValue('-- 在此输入您的 SQL 查询\n-- use 数据库名;\nSELECT * FROM table_name LIMIT 10;', -1);
        },
        
        // Update SQL editor hint based on current database
        updateSqlEditorHint() {
            if (!this.sqlEditor) return;
            
            // Only update if the editor contains the default hint
            const currentValue = this.sqlEditor.getValue();
            const isDefaultHint = currentValue.includes('-- 在此输入您的 SQL 查询') && 
                                  currentValue.includes('SELECT * FROM');
            
            if (!isDefaultHint) {
                // User has modified the SQL, don't update
                return;
            }
            
            let newHint;
            if (this.currentDatabase) {
                newHint = `-- 在此输入您的 SQL 查询\n-- use ${this.currentDatabase};\nSELECT * FROM ${this.currentDatabase}.table_name LIMIT 10;`;
            } else {
                newHint = '-- 在此输入您的 SQL 查询\n-- use 数据库名;\nSELECT * FROM table_name LIMIT 10;';
            }
            
            this.sqlEditor.setValue(newHint, -1);
        },
        
        // Setup Axios interceptors
        setupAxiosInterceptors() {
            axios.interceptors.request.use(
                config => {
                    this.loading = true;
                    return config;
                },
                error => {
                    this.loading = false;
                    return Promise.reject(error);
                }
            );
            
            axios.interceptors.response.use(
                response => {
                    this.loading = false;
                    return response;
                },
                error => {
                    this.loading = false;
                    return Promise.reject(error);
                }
            );
        },
        
        // Check database connection
        async checkConnection() {
            try {
                await apiClient.checkHealth();
                this.connectionStatus = 'connected';
                await this.loadDatabases();
            } catch (error) {
                this.connectionStatus = 'disconnected';
                this.handleApiError(error, () => this.checkConnection());
            }
        },
        
        // Load databases
        async loadDatabases() {
            try {
                const response = await apiClient.listDatabases();
                this.databases = response.databases || response;
                this.buildDatabaseTree();
            } catch (error) {
                this.handleApiError(error, () => this.loadDatabases());
            }
        },
        
        // Build tree structure for database explorer
        buildDatabaseTree() {
            this.databaseTree = this.databases.map(db => ({
                id: `db-${db}`,
                label: db,
                type: 'database',
                name: db,
                children: [],
                isLeaf: false
            }));
        },
        
        // Handle tree node click
        async handleNodeClick(data, node) {
            if (data.type === 'database') {
                // Toggle expand/collapse and load tables if expanding
                if (!node.expanded && data.children.length === 0) {
                    await this.loadTables(data.name);
                }
            } else if (data.type === 'table') {
                // Check if we need to switch database
                if (this.currentDatabase !== data.database) {
                    await this.switchDatabase(data.database);
                }
                
                // Reset pagination and filter when switching to a different table
                const isDifferentTable = this.selectedDatabase !== data.database || this.selectedTable !== data.name;
                if (isDifferentTable) {
                    this.currentPage = 1;
                    this.pageSize = 50;
                    this.filterCondition = '';
                    this.activeFilter = null;
                }
                
                // Load table data
                this.selectedDatabase = data.database;
                this.selectedTable = data.name;
                this.activeTab = 'table';
                await this.loadTableData();
                
                // Update SQL editor hint with current database
                this.updateSqlEditorHint();
            }
        },
        
        // Handle tree node context menu (right-click)
        handleNodeContextMenu(event, data) {
            event.preventDefault();
            event.stopPropagation();
            
            this.contextMenuType = data.type;
            this.contextMenuData = data;
            this.showContextMenu = true;
            
            // Position the context menu at cursor location
            this.$nextTick(() => {
                this.contextMenuStyle = {
                    position: 'fixed',
                    left: event.clientX + 'px',
                    top: event.clientY + 'px',
                    zIndex: 9999
                };
            });
        },
        
        // Hide context menu
        hideContextMenu() {
            this.showContextMenu = false;
        },
        
        // Switch to a different database
        async switchDatabase(database) {
            try {
                // Execute USE statement
                const sql = `USE \`${database}\``;
                const response = await apiClient.executeQuery(sql);
                
                if (response.success) {
                    this.currentDatabase = database;
                    this.showInfo(`已切换到数据库：${database}`);
                    console.log(`Switched to database: ${database}`);
                    
                    // Update SQL editor hint with new database
                    this.updateSqlEditorHint();
                } else {
                    this.showError(`切换数据库失败：${response.error}`);
                }
            } catch (error) {
                this.handleApiError(error, () => this.switchDatabase(database));
            }
        },
        
        // Load tables for a database
        async loadTables(database) {
            try {
                const response = await apiClient.listTables(database);
                const tables = response.tables || response;
                
                // Update tree with tables
                const dbNode = this.databaseTree.find(db => db.name === database);
                if (dbNode) {
                    dbNode.children = tables.map(table => ({
                        id: `table-${database}-${table}`,
                        label: table,
                        type: 'table',
                        name: table,
                        database: database,
                        isLeaf: true
                    }));
                    
                    // Force Vue to update the tree
                    this.$forceUpdate();
                }
            } catch (error) {
                this.handleApiError(error, () => this.loadTables(database));
            }
        },
        
        // Load table data
        async loadTableData() {
            if (!this.selectedDatabase || !this.selectedTable) {
                return;
            }
            
            this.tableLoading = true;
            
            try {
                // Load table structure and data in parallel
                const [structureResponse, dataResponse] = await Promise.all([
                    apiClient.getTableStructure(this.selectedDatabase, this.selectedTable),
                    apiClient.getTableData(
                        this.selectedDatabase, 
                        this.selectedTable, 
                        this.activeFilter, 
                        this.currentPage, 
                        this.pageSize
                    )
                ]);
                
                // Set table structure
                this.tableStructure = structureResponse.columns || structureResponse;
                
                // Set table data with pagination info
                this.tableData = {
                    columns: dataResponse.columns || [],
                    rows: dataResponse.rows || [],
                    total: dataResponse.total || 0,
                    page: dataResponse.page || 1,
                    page_size: dataResponse.page_size || this.pageSize,
                    total_pages: dataResponse.total_pages || 1
                };
                
            } catch (error) {
                this.handleApiError(error, () => this.loadTableData());
                this.tableData = { columns: [], rows: [], total: 0 };
                this.tableStructure = [];
            } finally {
                this.tableLoading = false;
            }
        },
        
        // Get paginated table rows (now returns all rows since backend handles pagination)
        getPaginatedRows() {
            return this.tableData.rows;
        },
        
        // Handle page change
        async handlePageChange(page) {
            this.currentPage = page;
            await this.loadTableData();
        },
        
        // Handle page size change
        async handlePageSizeChange(size) {
            this.pageSize = size;
            this.currentPage = 1;
            await this.loadTableData();
        },
        
        // Get column type display
        getColumnTypeDisplay(column) {
            if (!column) return '';
            return column.type || '';
        },
        
        // Check if column is required (NOT NULL and no default value)
        isColumnRequired(column) {
            if (!column) return false;
            
            // Find the full column info from tableStructure
            const fullColumnInfo = this.tableStructure.find(col => col.name === column.name);
            if (!fullColumnInfo) return false;
            
            // Column is required if it's NOT NULL and has no default value and is not auto-increment
            const isNotNull = fullColumnInfo.nullable === false || fullColumnInfo.nullable === 'NO';
            const hasNoDefault = !fullColumnInfo.default && fullColumnInfo.default !== 0;
            const isNotAutoIncrement = !fullColumnInfo.extra || !fullColumnInfo.extra.includes('auto_increment');
            
            return isNotNull && hasNoDefault && isNotAutoIncrement;
        },
        
        // Get validation rules for a column
        getColumnValidationRules(column) {
            if (!this.isColumnRequired(column)) {
                return [];
            }
            
            return [
                {
                    required: true,
                    message: `${column.name} 不能为空`,
                    trigger: 'blur'
                }
            ];
        },
        
        // Validate required fields in editing row
        validateEditingRow() {
            const errors = [];
            
            for (const column of this.tableData.columns) {
                if (this.isColumnRequired(column)) {
                    const value = this.editingRowData[column.name];
                    if (value === null || value === undefined || value === '') {
                        errors.push(column.name);
                    }
                }
            }
            
            return errors;
        },
        
        // Validate required fields in new row
        validateNewRow() {
            const errors = [];
            
            for (const column of this.tableData.columns) {
                if (this.isColumnRequired(column)) {
                    const value = this.newRowData[column.name];
                    if (value === null || value === undefined || value === '') {
                        errors.push(column.name);
                    }
                }
            }
            
            return errors;
        },
        
        // Handle row double-click for editing
        handleRowDoubleClick(row, column, event) {
            this.startEditingRow(row);
        },
        
        // Start editing a row
        startEditingRow(row) {
            // Find the actual row index in the full dataset
            this.editingRowIndex = this.tableData.rows.findIndex(r => r === row);
            this.editingRow = row;
            
            // Create a copy of the row data for editing
            this.editingRowData = { ...row };
        },
        
        // Save edited row
        async saveEditedRow() {
            if (!this.editingRow || this.editingRowIndex === -1) {
                return;
            }
            
            // Validate required fields
            const validationErrors = this.validateEditingRow();
            if (validationErrors.length > 0) {
                this.showError(`以下必填字段不能为空：${validationErrors.join(', ')}`);
                return;
            }
            
            try {
                // Find primary key column
                const pkColumn = this.tableStructure.find(col => col.key === 'PRI');
                
                if (!pkColumn) {
                    this.showError('无法更新行：表中未找到主键');
                    return;
                }
                
                const pkValue = this.editingRow[pkColumn.name];
                
                // Prepare update data (only changed fields)
                const updateData = {};
                for (const key in this.editingRowData) {
                    if (this.editingRowData[key] !== this.editingRow[key]) {
                        updateData[key] = this.editingRowData[key];
                    }
                }
                
                if (Object.keys(updateData).length === 0) {
                    this.showInfo('没有需要保存的更改');
                    this.cancelEditingRow();
                    return;
                }
                
                // Call API to update row
                await apiClient.updateRow(
                    this.selectedDatabase,
                    this.selectedTable,
                    pkColumn.name,
                    pkValue,
                    updateData
                );
                
                // Update the row in the local data
                Object.assign(this.tableData.rows[this.editingRowIndex], this.editingRowData);
                
                this.showSuccess('行更新成功');
                this.cancelEditingRow();
                
            } catch (error) {
                this.handleApiError(error, () => this.saveEditedRow());
            }
        },
        
        // Cancel editing
        cancelEditingRow() {
            this.editingRow = null;
            this.editingRowIndex = -1;
            this.editingRowData = {};
        },
        
        // Check if a row is being edited
        isRowEditing(row) {
            return this.editingRow === row;
        },
        
        // Handle row selection
        handleSelectionChange(selection) {
            this.selectedRows = selection;
        },
        
        // Open add row dialog
        openAddRowDialog() {
            // Initialize new row data with empty values
            this.newRowData = {};
            this.tableData.columns.forEach(col => {
                this.newRowData[col.name] = '';
            });
            this.showAddRowDialog = true;
        },
        
        // Add new row
        async addNewRow() {
            // Validate required fields
            const validationErrors = this.validateNewRow();
            if (validationErrors.length > 0) {
                this.showError(`以下必填字段不能为空：${validationErrors.join(', ')}`);
                return;
            }
            
            try {
                // Remove empty string values (let database use defaults)
                const insertData = {};
                for (const key in this.newRowData) {
                    if (this.newRowData[key] !== '') {
                        insertData[key] = this.newRowData[key];
                    }
                }
                
                if (Object.keys(insertData).length === 0) {
                    this.showWarning('请至少输入一个值');
                    return;
                }
                
                // Call API to insert row
                await apiClient.insertRow(
                    this.selectedDatabase,
                    this.selectedTable,
                    insertData
                );
                
                this.showSuccess('行添加成功');
                this.showAddRowDialog = false;
                this.newRowData = {};
                
                // Reload table data
                await this.loadTableData();
                
            } catch (error) {
                this.handleApiError(error, () => this.addNewRow());
            }
        },
        
        // Delete selected rows
        async deleteSelectedRows() {
            if (this.selectedRows.length === 0) {
                this.showWarning('请选择要删除的行');
                return;
            }
            
            try {
                // Find primary key column
                const pkColumn = this.tableStructure.find(col => col.key === 'PRI');
                
                if (!pkColumn) {
                    this.showError('无法删除行：表中未找到主键');
                    return;
                }
                
                // Confirm deletion
                await ElMessageBox.confirm(
                    `确定要删除 ${this.selectedRows.length} 行吗？此操作无法撤销。`,
                    '确认删除行',
                    {
                        confirmButtonText: '删除',
                        cancelButtonText: '取消',
                        type: 'warning',
                        confirmButtonClass: 'el-button--danger'
                    }
                );
                
                // Delete each selected row
                const deletePromises = this.selectedRows.map(row => {
                    const pkValue = row[pkColumn.name];
                    return apiClient.deleteRow(
                        this.selectedDatabase,
                        this.selectedTable,
                        pkColumn.name,
                        pkValue
                    );
                });
                
                await Promise.all(deletePromises);
                
                this.showSuccess(`成功删除 ${this.selectedRows.length} 行`);
                this.selectedRows = [];
                
                // Reload table data
                await this.loadTableData();
                
            } catch (error) {
                if (error !== 'cancel') {
                    this.handleApiError(error, () => this.deleteSelectedRows());
                }
            }
        },
        
        // Apply filter to table data
        async applyFilter() {
            const filter = this.filterCondition.trim();
            
            if (!filter) {
                this.showWarning('请输入过滤条件');
                return;
            }
            
            // Store active filter and reset to first page
            this.activeFilter = filter;
            this.currentPage = 1;
            
            // Reload table data with filter
            await this.loadTableData();
            
            this.showSuccess(`过滤已应用：匹配 ${this.tableData.total} 行`);
        },
        
        // Clear filter
        async clearFilter() {
            this.filterCondition = '';
            this.activeFilter = null;
            this.currentPage = 1;
            
            // Reload table data without filter
            await this.loadTableData();
            
            this.showInfo('过滤已清除');
        },
        
        // Get icon for tree node based on type and state
        getNodeIcon(data, node) {
            if (data.type === 'database') {
                return node.expanded ? 'el-icon-folder-opened' : 'el-icon-folder';
            } else if (data.type === 'table') {
                return 'el-icon-document';
            }
            return 'el-icon-document';
        },
        
        // Create database
        async createDatabase() {
            const dbName = this.newDatabase.name.trim();
            
            // Validation
            if (!dbName) {
                this.showWarning('请输入数据库名称');
                return;
            }
            
            // Validate database name format (alphanumeric, underscore, max 64 chars)
            const validNamePattern = /^[a-zA-Z0-9_]+$/;
            if (!validNamePattern.test(dbName)) {
                this.showWarning('数据库名称只能包含字母、数字和下划线');
                return;
            }
            
            if (dbName.length > 64) {
                this.showWarning('数据库名称不能超过 64 个字符');
                return;
            }
            
            // Check if database already exists
            if (this.databases.includes(dbName)) {
                this.showWarning(`数据库 "${dbName}" 已存在`);
                return;
            }
            
            try {
                await apiClient.createDatabase(dbName);
                this.showSuccess(`数据库 "${dbName}" 创建成功`);
                this.showCreateDatabaseDialog = false;
                this.newDatabase.name = '';
                await this.loadDatabases();
            } catch (error) {
                this.handleApiError(error, () => this.createDatabase());
            }
        },
        
        // View database DDL
        async viewDatabaseDDL() {
            this.hideContextMenu();
            
            if (!this.contextMenuData) return;
            
            try {
                const response = await apiClient.getDatabaseDDL(this.contextMenuData.name);
                
                // Display DDL in a message box with monospace font
                ElMessageBox.alert(
                    `<pre style="max-height: 400px; overflow-y: auto; text-align: left; white-space: pre-wrap; word-wrap: break-word;">${response.ddl || '无可用 DDL'}</pre>`,
                    `数据库 DDL: ${this.contextMenuData.name}`,
                    {
                        confirmButtonText: '确定',
                        dangerouslyUseHTMLString: true,
                        customClass: 'ddl-dialog'
                    }
                );
            } catch (error) {
                this.handleApiError(error, () => this.viewDatabaseDDL());
            }
        },
        
        // Confirm and delete database
        async confirmDeleteDatabase() {
            this.hideContextMenu();
            
            if (!this.contextMenuData) return;
            
            const dbName = this.contextMenuData.name;
            
            try {
                await ElMessageBox.confirm(
                    `确定要删除数据库 "${dbName}" 吗？此操作无法撤销。`,
                    '确认删除数据库',
                    {
                        confirmButtonText: '删除',
                        cancelButtonText: '取消',
                        type: 'warning',
                        confirmButtonClass: 'el-button--danger'
                    }
                );
                
                await this.deleteDatabase(dbName);
            } catch (error) {
                // User cancelled or error occurred
                if (error !== 'cancel') {
                    console.error('Delete database error:', error);
                }
            }
        },
        
        // Delete database (actual deletion)
        async deleteDatabase(dbName) {
            try {
                await apiClient.deleteDatabase(dbName);
                this.showSuccess(`数据库 "${dbName}" 删除成功`);
                
                // Clear selection if deleted database was selected
                if (this.selectedDatabase === dbName) {
                    this.selectedDatabase = null;
                    this.selectedTable = null;
                }
                
                await this.loadDatabases();
            } catch (error) {
                this.handleApiError(error, () => this.deleteDatabase(dbName));
            }
        },
        
        // Confirm and delete table
        async confirmDeleteTable() {
            this.hideContextMenu();
            
            if (!this.contextMenuData) return;
            
            const tableName = this.contextMenuData.name;
            const dbName = this.contextMenuData.database;
            
            try {
                await ElMessageBox.confirm(
                    `确定要删除表 "${tableName}" 吗？此操作无法撤销。`,
                    '确认删除表',
                    {
                        confirmButtonText: '删除',
                        cancelButtonText: '取消',
                        type: 'warning',
                        confirmButtonClass: 'el-button--danger'
                    }
                );
                
                await this.deleteTable(dbName, tableName);
            } catch (error) {
                // User cancelled or error occurred
                if (error !== 'cancel') {
                    console.error('Delete table error:', error);
                }
            }
        },
        
        // Delete table (actual deletion)
        async deleteTable(dbName, tableName) {
            try {
                await apiClient.deleteTable(dbName, tableName);
                this.showSuccess(`表 "${tableName}" 删除成功`);
                
                // Clear selection if deleted table was selected
                if (this.selectedTable === tableName && this.selectedDatabase === dbName) {
                    this.selectedTable = null;
                }
                
                await this.loadTables(dbName);
            } catch (error) {
                this.handleApiError(error, () => this.deleteTable(dbName, tableName));
            }
        },
        
        // Execute SQL query
        async executeQuery() {
            const sql = this.sqlEditor.getValue().trim();
            if (!sql) {
                this.showWarning('请输入 SQL 查询');
                return;
            }
            
            this.queryLoading = true;
            
            try {
                const response = await apiClient.executeQuery(sql);
                this.queryResults = response;
                
                if (response.success) {
                    if (response.rows && response.rows.length > 0) {
                        this.showSuccess(`查询执行成功。返回 ${response.rows.length} 行。`);
                    } else if (response.rows && response.rows.length === 0) {
                        this.showInfo('查询执行成功。未返回任何行。');
                    } else if (response.affected_rows !== undefined) {
                        this.showSuccess(`查询执行成功。影响 ${response.affected_rows} 行。`);
                    } else {
                        this.showSuccess('查询执行成功。');
                    }
                } else {
                    // Error response from backend
                    this.showError('查询失败：' + (response.error || '未知错误'));
                }
            } catch (error) {
                // Network or other error
                this.handleApiError(error, () => this.executeQuery());
                
                // Set error in query results for display
                this.queryResults = {
                    success: false,
                    error: error.message || '执行查询失败'
                };
            } finally {
                this.queryLoading = false;
            }
        },
        
        // Clear SQL query
        clearQuery() {
            this.sqlEditor.setValue('', -1);
            this.queryResults = null;
        },
        
        // Handle tab click
        handleTabClick(tab) {
            // Handle tab switching logic if needed
        },
        
        // Handle logout
        async handleLogout() {
            try {
                await ElMessageBox.confirm(
                    '确定要退出登录吗？',
                    '确认退出',
                    {
                        confirmButtonText: '退出',
                        cancelButtonText: '取消',
                        type: 'warning',
                        confirmButtonClass: 'el-button--danger'
                    }
                );
                
                // Clear admin key
                localStorage.removeItem('adminKey');
                
                // Redirect to login page
                window.location.href = '/login.html';
            } catch (error) {
                // User cancelled
            }
        },
        
        // Notification methods
        showSuccess(message) {
            ElMessage({
                message: message,
                type: 'success',
                duration: 3000,
                showClose: true
            });
        },
        
        showError(message, options = {}) {
            const { retryable = false, onRetry = null } = options;
            
            // For retryable errors, show with retry action
            if (retryable && onRetry) {
                ElMessage({
                    message: message,
                    type: 'error',
                    duration: 0, // Don't auto-dismiss for retryable errors
                    showClose: true,
                    dangerouslyUseHTMLString: true,
                    customClass: 'error-with-retry',
                    onClose: () => {
                        // Clean up any retry handlers
                    }
                });
                
                // Show a separate notification with retry button
                this.$nextTick(() => {
                    ElMessageBox.confirm(
                        message,
                        '网络错误',
                        {
                            confirmButtonText: '重试',
                            cancelButtonText: '取消',
                            type: 'error',
                            distinguishCancelAndClose: true
                        }
                    ).then(() => {
                        // User clicked retry
                        if (onRetry) {
                            onRetry();
                        }
                    }).catch((action) => {
                        // User cancelled or closed
                        console.log('User cancelled retry:', action);
                    });
                });
            } else {
                // Regular error without retry
                ElMessage({
                    message: message,
                    type: 'error',
                    duration: 5000,
                    showClose: true
                });
            }
        },
        
        showWarning(message) {
            ElMessage({
                message: message,
                type: 'warning',
                duration: 3000,
                showClose: true
            });
        },
        
        showInfo(message) {
            ElMessage({
                message: message,
                type: 'info',
                duration: 3000,
                showClose: true
            });
        },
        
        // Enhanced error handler that processes API errors
        handleApiError(error, retryCallback = null) {
            console.log('[Error Handler]', error); // Debug log
            
            // If error is already processed by API client
            if (error.type && error.message) {
                const isRetryable = error.retryable && retryCallback !== null;
                
                // Show appropriate notification based on error type
                if (error.type === 'network') {
                    this.showError(error.message, {
                        retryable: isRetryable,
                        onRetry: retryCallback
                    });
                } else if (error.type === 'server') {
                    // For server errors, show the message directly (it already contains detail)
                    this.showError(error.message, {
                        retryable: isRetryable,
                        onRetry: retryCallback
                    });
                } else if (error.type === 'client') {
                    // For client errors (400, 422, etc.), show the message directly
                    this.showError(error.message);
                } else {
                    this.showError(error.message);
                }
            } else if (error.response && error.response.data) {
                // Fallback: try to extract error from response directly
                const data = error.response.data;
                const message = data.detail || data.error || data.message || '发生意外错误';
                this.showError(message);
            } else {
                // Fallback for unprocessed errors
                this.showError(error.message || '发生意外错误');
            }
        }
    }
});

// Use Element Plus
app.use(ElementPlus);

// Mount the app
app.mount('#app');
