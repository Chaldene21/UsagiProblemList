// API 基础路径
const API_BASE = '/api';

// 状态管理
let currentProblemSets = [];
let currentCategory = 'all';
let currentUser = null;
let authToken = localStorage.getItem('token');

// 工具函数：获取难度等级样式
function getDifficultyClass(difficulty) {
    if (difficulty < 1300) return 'difficulty-easy';
    if (difficulty < 1700) return 'difficulty-medium';
    return 'difficulty-hard';
}

// 工具函数：获取难度等级文本
function getDifficultyLabel(difficulty) {
    if (difficulty < 1300) return '简单';
    if (difficulty < 1700) return '中等';
    return '困难';
}

// API 请求封装
async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
    });
    
    const result = await response.json();
    
    if (result.code === 401) {
        // Token过期，清除登录状态
        logout();
    }
    
    return result;
}

// 检查登录状态
async function checkAuth() {
    if (!authToken) return false;
    
    try {
        const result = await apiRequest('/user');
        if (result.code === 0) {
            currentUser = result.data;
            return true;
        }
    } catch (e) {
        console.error('Auth check failed:', e);
    }
    return false;
}

// 登出
function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('token');
    updateNavbar();
    navigateTo('/');
}

// 更新导航栏
function updateNavbar() {
    const navMenu = document.querySelector('.nav-menu');
    if (!navMenu) return;
    
    if (currentUser) {
        navMenu.innerHTML = `
            <span class="nav-user">
                <i class="fas fa-user"></i>
                ${currentUser.nickname || currentUser.username}
            </span>
            <button class="nav-btn" onclick="showStats()" title="我的进度">
                <i class="fas fa-chart-bar"></i>
            </button>
            <button class="nav-btn" onclick="logout()" title="退出登录">
                <i class="fas fa-sign-out-alt"></i>
            </button>
        `;
    } else {
        navMenu.innerHTML = `
            <button class="nav-btn" onclick="showLogin()" title="登录">
                <i class="fas fa-sign-in-alt"></i>
            </button>
            <button class="nav-btn" onclick="showRegister()" title="注册">
                <i class="fas fa-user-plus"></i>
            </button>
        `;
    }
}

// 导航函数
function navigateTo(path) {
    history.pushState({}, '', path);
    handleRoute();
}

// 路由处理
async function handleRoute() {
    const path = window.location.pathname;
    const content = document.getElementById('content');

    // 检查登录状态
    await checkAuth();
    updateNavbar();

    if (path === '/' || path === '') {
        renderProblemSetList();
    } else if (path.startsWith('/problemset/')) {
        const id = path.split('/')[2];
        renderProblemSetDetail(id);
    } else if (path === '/stats') {
        renderStatsPage();
    } else {
        content.innerHTML = '<div class="error">页面未找到</div>';
    }
}

// 获取题单列表
async function fetchProblemSets() {
    const result = await apiRequest('/problemsets');
    if (result.code === 0) {
        return result.data;
    }
    throw new Error(result.message);
}

// 获取题单详情
async function fetchProblemSet(id) {
    const result = await apiRequest(`/problemsets/${id}`);
    if (result.code === 0) {
        return result.data;
    }
    throw new Error(result.message);
}

// ==================== 登录/注册模态框 ====================

function showLogin() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.id = 'authModal';
    modal.innerHTML = `
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <h2 class="modal-title"><i class="fas fa-sign-in-alt"></i> 登录</h2>
            <form onsubmit="handleLogin(event)">
                <div class="form-group">
                    <label><i class="fas fa-user"></i> 用户名</label>
                    <input type="text" id="loginUsername" required placeholder="请输入用户名">
                </div>
                <div class="form-group">
                    <label><i class="fas fa-lock"></i> 密码</label>
                    <input type="password" id="loginPassword" required placeholder="请输入密码">
                </div>
                <button type="submit" class="btn-primary">登录</button>
            </form>
            <p class="modal-footer">
                还没有账号？<a href="#" onclick="showRegister()">立即注册</a>
            </p>
        </div>
    `;
    document.body.appendChild(modal);
}

function showRegister() {
    closeModal();
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.id = 'authModal';
    modal.innerHTML = `
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <h2 class="modal-title"><i class="fas fa-user-plus"></i> 注册</h2>
            <form onsubmit="handleRegister(event)">
                <div class="form-group">
                    <label><i class="fas fa-user"></i> 用户名</label>
                    <input type="text" id="regUsername" required minlength="3" placeholder="3-50个字符">
                </div>
                <div class="form-group">
                    <label><i class="fas fa-envelope"></i> 邮箱</label>
                    <input type="email" id="regEmail" required placeholder="请输入邮箱">
                </div>
                <div class="form-group">
                    <label><i class="fas fa-lock"></i> 密码</label>
                    <input type="password" id="regPassword" required minlength="6" placeholder="至少6个字符">
                </div>
                <div class="form-group">
                    <label><i class="fas fa-id-card"></i> 昵称（可选）</label>
                    <input type="text" id="regNickname" placeholder="显示名称">
                </div>
                <button type="submit" class="btn-primary">注册</button>
            </form>
            <p class="modal-footer">
                已有账号？<a href="#" onclick="showLogin()">立即登录</a>
            </p>
        </div>
    `;
    document.body.appendChild(modal);
}

function closeModal() {
    const modal = document.getElementById('authModal');
    if (modal) modal.remove();
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    
    const result = await apiRequest('/login', {
        method: 'POST',
        body: JSON.stringify({ username, password })
    });
    
    if (result.code === 0) {
        authToken = result.data.token;
        currentUser = result.data.user;
        localStorage.setItem('token', authToken);
        closeModal();
        updateNavbar();
        alert('登录成功！');
    } else {
        alert('登录失败：' + result.message);
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('regUsername').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;
    const nickname = document.getElementById('regNickname').value;
    
    const result = await apiRequest('/register', {
        method: 'POST',
        body: JSON.stringify({ username, email, password, nickname })
    });
    
    if (result.code === 0) {
        alert('注册成功！请登录');
        showLogin();
    } else {
        alert('注册失败：' + result.message);
    }
}

// ==================== 进度管理 ====================

// 进度缓存
let progressCache = {};

// 获取题单进度
async function fetchProblemSetProgress(problemSetId) {
    if (!authToken || !currentUser) return null;
    
    const cacheKey = `progress_${problemSetId}`;
    if (progressCache[cacheKey]) return progressCache[cacheKey];
    
    const result = await apiRequest(`/progress/problemset/${problemSetId}`);
    if (result.code === 0) {
        progressCache[cacheKey] = result.data;
        return result.data;
    }
    return null;
}

// 更新题目进度
async function updateProgress(problemId, problemSetId, isCompleted) {
    if (!authToken || !currentUser) {
        alert('请先登录');
        showLogin();
        return false;
    }
    
    const result = await apiRequest('/progress', {
        method: 'POST',
        body: JSON.stringify({
            problem_id: problemId,
            problemset_id: problemSetId,
            is_completed: isCompleted
        })
    });
    
    if (result.code === 0) {
        // 清除缓存
        progressCache = {};
        return true;
    }
    return false;
}

// 显示统计页面
async function showStats() {
    navigateTo('/stats');
}

// ==================== 页面渲染 ====================

// 渲染题单列表页
async function renderProblemSetList() {
    const content = document.getElementById('content');
    
    // 显示加载状态
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>加载中...</p>
        </div>
    `;

    try {
        currentProblemSets = await fetchProblemSets();
        
        // 获取所有分类
        const categories = ['all', ...new Set(currentProblemSets.map(ps => ps.category))];
        
        // 如果已登录，获取进度
        let progressData = {};
        if (currentUser) {
            const progressResult = await apiRequest('/progress/problemset');
            if (progressResult.code === 0 && progressResult.data) {
                progressResult.data.forEach(p => {
                    progressData[p.problemset_id] = p;
                });
            }
        }
        
        // 渲染页面
        content.innerHTML = `
            <div class="page-header">
                <h1 class="page-title">题单列表</h1>
                <p class="page-subtitle">精选算法题单，助你高效提升</p>
            </div>
            
            <div class="category-tabs" id="categoryTabs">
                ${categories.map(cat => `
                    <button class="category-tab ${cat === currentCategory ? 'active' : ''}" 
                            onclick="filterByCategory('${cat}')">
                        ${cat === 'all' ? '全部' : cat}
                    </button>
                `).join('')}
            </div>
            
            <div class="problemset-grid" id="problemsetGrid">
                ${renderProblemSetCards(currentProblemSets, progressData)}
            </div>
        `;
    } catch (error) {
        content.innerHTML = `
            <div class="error">
                <p>加载失败：${error.message}</p>
                <button onclick="renderProblemSetList()" class="btn-primary" style="margin-top: 1rem;">
                    重试
                </button>
            </div>
        `;
    }
}

// 渲染题单卡片
function renderProblemSetCards(problemSets, progressData = {}) {
    const filtered = currentCategory === 'all' 
        ? problemSets 
        : problemSets.filter(ps => ps.category === currentCategory);

    if (filtered.length === 0) {
        return '<p style="color: var(--text-secondary); text-align: center; grid-column: 1/-1;">暂无题单</p>';
    }

    return filtered.map(ps => {
        const progress = progressData[ps.id];
        const progressHtml = progress ? `
            <div class="card-progress">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress.percentage}%"></div>
                </div>
                <span class="progress-text">${progress.completed_problems}/${progress.total_problems}</span>
            </div>
        ` : '';
        
        return `
            <div class="problemset-card" onclick="navigateTo('/problemset/${ps.id}')">
                <span class="card-category">${ps.category}</span>
                <h3 class="card-title">${ps.title}</h3>
                <p class="card-description">${ps.description}</p>
                ${progressHtml}
            </div>
        `;
    }).join('');
}

// 按分类筛选
function filterByCategory(category) {
    currentCategory = category;
    
    // 更新标签状态
    document.querySelectorAll('.category-tab').forEach(tab => {
        tab.classList.toggle('active', tab.textContent.trim() === (category === 'all' ? '全部' : category));
    });
    
    // 重新渲染卡片（保持进度数据）
    renderProblemSetList();
}

// 渲染题单详情页
async function renderProblemSetDetail(id) {
    const content = document.getElementById('content');
    
    // 显示加载状态
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>加载中...</p>
        </div>
    `;

    try {
        const problemSet = await fetchProblemSet(id);
        
        // 获取进度
        const progress = await fetchProblemSetProgress(id);
        const completedIds = progress ? new Set(progress.completed_ids) : new Set();
        
        content.innerHTML = `
            <div class="problemset-detail">
                <div class="detail-header">
                    <div class="back-button" onclick="navigateTo('/')">
                        <i class="fas fa-arrow-left"></i>
                        返回列表
                    </div>
                    <h1 class="detail-title">${problemSet.title}</h1>
                    <span class="detail-category">${problemSet.category}</span>
                    <p class="detail-description">${problemSet.description}</p>
                    ${progress ? `
                        <div class="detail-progress">
                            <div class="progress-info">
                                <span>完成进度</span>
                                <span class="progress-stats">${progress.completed_problems}/${progress.total_problems}</span>
                            </div>
                            <div class="progress-bar-lg">
                                <div class="progress-fill" style="width: ${progress.percentage}%"></div>
                            </div>
                        </div>
                    ` : ''}
                </div>
                
                <div class="sections">
                    ${problemSet.sections.map(section => renderSection(section, id, completedIds)).join('')}
                </div>
            </div>
        `;
    } catch (error) {
        content.innerHTML = `
            <div class="error">
                <p>加载失败：${error.message}</p>
                <button onclick="navigateTo('/')" class="btn-primary" style="margin-top: 1rem;">
                    返回列表
                </button>
            </div>
        `;
    }
}

// 渲染章节
function renderSection(section, problemSetId, completedIds) {
    return `
        <div class="section">
            <h2 class="section-title">${section.title}</h2>
            <div class="section-content">
                ${section.content.map(item => renderContentItem(item, problemSetId, completedIds)).join('')}
            </div>
        </div>
    `;
}

// 渲染内容项
function renderContentItem(item, problemSetId, completedIds) {
    if (item.type === 'paragraph') {
        return `<div class="paragraph">${item.text}</div>`;
    }
    
    // 子章节对象
    return `
        <div class="subsection">
            ${item.title ? `<h3 class="subsection-title">${item.title}</h3>` : ''}
            ${item.idea ? `
                <div class="subsection-idea">
                    <div class="idea-label">解题思路</div>
                    <div class="idea-content">${item.idea}</div>
                </div>
            ` : ''}
            ${item.code_template ? `
                <div class="code-template">
                    <div class="code-label">代码模板</div>
                    <div class="code-block">
                        <code>${escapeHtml(item.code_template)}</code>
                    </div>
                </div>
            ` : ''}
            ${item.problems && item.problems.length > 0 ? `
                <div class="problems-section">
                    <div class="problems-title">
                        相关题目
                        <span class="problems-count">${item.problems.length}</span>
                    </div>
                    <div class="problems-list">
                        ${item.problems.map(problem => renderProblem(problem, problemSetId, completedIds)).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

// 渲染题目
function renderProblem(problem, problemSetId, completedIds) {
    const isCompleted = completedIds.has(problem.id);
    
    return `
        <div class="problem-item ${isCompleted ? 'completed' : ''}" data-problem-id="${problem.id}">
            <div class="problem-info">
                <label class="problem-checkbox">
                    <input type="checkbox" 
                           ${isCompleted ? 'checked' : ''} 
                           onchange="toggleProblemProgress('${problem.id}', '${problemSetId}', this.checked)">
                    <span class="checkmark"></span>
                </label>
                <span class="problem-id">#${problem.id}</span>
                <span class="problem-name">${problem.name}</span>
                <div class="problem-tags">
                    ${problem.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
            </div>
            <div class="problem-meta">
                <span class="difficulty ${getDifficultyClass(problem.difficulty)}">${problem.difficulty}</span>
                <a href="${problem.url}" target="_blank" class="problem-link" title="前往 Codeforces" onclick="event.stopPropagation()">
                    <i class="fas fa-external-link-alt"></i>
                </a>
            </div>
            ${problem.note ? `<div class="problem-note">${problem.note}</div>` : ''}
        </div>
    `;
}

// 切换题目进度
async function toggleProblemProgress(problemId, problemSetId, isCompleted) {
    const success = await updateProgress(problemId, problemSetId, isCompleted);
    
    if (success) {
        // 更新UI
        const problemItem = document.querySelector(`[data-problem-id="${problemId}"]`);
        if (problemItem) {
            problemItem.classList.toggle('completed', isCompleted);
        }
        
        // 刷新进度显示
        const progress = await fetchProblemSetProgress(problemSetId);
        if (progress) {
            const progressInfo = document.querySelector('.detail-progress');
            if (progressInfo) {
                progressInfo.innerHTML = `
                    <div class="progress-info">
                        <span>完成进度</span>
                        <span class="progress-stats">${progress.completed_problems}/${progress.total_problems}</span>
                    </div>
                    <div class="progress-bar-lg">
                        <div class="progress-fill" style="width: ${progress.percentage}%"></div>
                    </div>
                `;
            }
        }
    }
}

// 渲染统计页面
async function renderStatsPage() {
    const content = document.getElementById('content');
    
    if (!currentUser) {
        content.innerHTML = `
            <div class="error">
                <p>请先登录查看进度</p>
                <button onclick="showLogin()" class="btn-primary" style="margin-top: 1rem;">
                    登录
                </button>
            </div>
        `;
        return;
    }
    
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>加载中...</p>
        </div>
    `;
    
    try {
        const [statsResult, categoryResult, problemsetResult] = await Promise.all([
            apiRequest('/progress/stats'),
            apiRequest('/progress/category'),
            apiRequest('/progress/problemset')
        ]);
        
        const stats = statsResult.data || { completed_problems: 0, completed_sets: 0, easy_count: 0, medium_count: 0, hard_count: 0 };
        const categories = categoryResult.data || [];
        const problemsets = problemsetResult.data || [];
        
        content.innerHTML = `
            <div class="stats-page">
                <div class="page-header">
                    <h1 class="page-title">我的进度</h1>
                    <p class="page-subtitle">追踪你的刷题进度</p>
                </div>
                
                <div class="stats-overview">
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-tasks"></i></div>
                        <div class="stat-value">${stats.completed_problems || 0}</div>
                        <div class="stat-label">已完成题目</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-book"></i></div>
                        <div class="stat-value">${stats.completed_sets || 0}</div>
                        <div class="stat-label">已完成题单</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon easy"><i class="fas fa-star"></i></div>
                        <div class="stat-value">${stats.easy_count || 0}</div>
                        <div class="stat-label">简单题</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon medium"><i class="fas fa-star-half-alt"></i></div>
                        <div class="stat-value">${stats.medium_count || 0}</div>
                        <div class="stat-label">中等题</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon hard"><i class="fas fa-bolt"></i></div>
                        <div class="stat-value">${stats.hard_count || 0}</div>
                        <div class="stat-label">困难题</div>
                    </div>
                </div>
                
                <div class="stats-section">
                    <h2 class="section-title"><i class="fas fa-folder"></i> 分类进度</h2>
                    <div class="category-progress-list">
                        ${categories.length > 0 ? categories.map(cat => `
                            <div class="category-progress-item">
                                <div class="category-info">
                                    <span class="category-name">${cat.category}</span>
                                    <span class="category-stats">${cat.completed_problems}/${cat.total_problems}</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${cat.percentage}%"></div>
                                </div>
                            </div>
                        `).join('') : '<p style="color: var(--text-light); text-align: center;">暂无数据</p>'}
                    </div>
                </div>
                
                <div class="stats-section">
                    <h2 class="section-title"><i class="fas fa-list"></i> 题单进度</h2>
                    <div class="problemset-progress-list">
                        ${problemsets.length > 0 ? problemsets.map(ps => `
                            <div class="problemset-progress-item" onclick="navigateTo('/problemset/${ps.problemset_id}')">
                                <div class="problemset-info">
                                    <span class="problemset-title">${ps.problemset_title}</span>
                                    <span class="problemset-category">${ps.category}</span>
                                </div>
                                <div class="problemset-progress-bar">
                                    <div class="progress-bar">
                                        <div class="progress-fill" style="width: ${ps.percentage}%"></div>
                                    </div>
                                    <span class="progress-text">${ps.completed_problems}/${ps.total_problems}</span>
                                </div>
                            </div>
                        `).join('') : '<p style="color: var(--text-light); text-align: center;">暂无数据</p>'}
                    </div>
                </div>
                
                <button class="btn-secondary" onclick="navigateTo('/')">
                    <i class="fas fa-arrow-left"></i> 返回题单列表
                </button>
            </div>
        `;
    } catch (error) {
        content.innerHTML = `
            <div class="error">
                <p>加载失败：${error.message}</p>
                <button onclick="renderStatsPage()" class="btn-primary" style="margin-top: 1rem;">
                    重试
                </button>
            </div>
        `;
    }
}

// HTML 转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 处理浏览器前进/后退
window.addEventListener('popstate', handleRoute);

// 页面加载完成后处理路由
document.addEventListener('DOMContentLoaded', handleRoute);