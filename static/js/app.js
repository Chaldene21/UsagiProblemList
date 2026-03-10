// API 基础路径
const API_BASE = '/api';

// 状态管理
let currentProblemSets = [];
let currentCategory = 'all';
let currentUser = null;
let authToken = localStorage.getItem('token');
let bgEnabled = localStorage.getItem('bgEnabled') !== 'false'; // 默认显示背景

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

// 检查登录状态（带缓存）
let lastAuthCheck = 0;
let authCheckInterval = 60000; // 1分钟内不重复检查

async function checkAuth(force = false) {
    if (!authToken) return false;
    
    // 如果非强制检查且在缓存时间内，直接返回当前状态
    if (!force && currentUser && (Date.now() - lastAuthCheck < authCheckInterval)) {
        return true;
    }
    
    try {
        const result = await apiRequest('/user');
        if (result.code === 0) {
            currentUser = result.data;
            lastAuthCheck = Date.now();
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

    const bgBtnClass = bgEnabled ? 'nav-btn active' : 'nav-btn';
    const bgBtnIcon = bgEnabled ? 'fa-image' : 'fa-image';

    if (currentUser) {
        navMenu.innerHTML = `
            <span class="nav-user">
                <i class="fas fa-user"></i>
                ${currentUser.nickname || currentUser.username}
            </span>
            <button class="${bgBtnClass}" onclick="toggleBackground()" title="切换背景">
                <i class="fas ${bgBtnIcon}"></i>
            </button>
            <button class="nav-btn" onclick="showStats()" title="个人主页">
                <i class="fas fa-home"></i>
            </button>
            <button class="nav-btn" onclick="logout()" title="退出登录">
                <i class="fas fa-sign-out-alt"></i>
            </button>
        `;
    } else {
        navMenu.innerHTML = `
            <button class="${bgBtnClass}" onclick="toggleBackground()" title="切换背景">
                <i class="fas ${bgBtnIcon}"></i>
            </button>
            <button class="nav-btn" onclick="showLogin()" title="登录">
                <i class="fas fa-sign-in-alt"></i>
            </button>
            <button class="nav-btn" onclick="showRegister()" title="注册">
                <i class="fas fa-user-plus"></i>
            </button>
        `;
    }
}

// 切换背景图片
function toggleBackground() {
    bgEnabled = !bgEnabled;
    localStorage.setItem('bgEnabled', bgEnabled);
    console.log('toggleBackground called, bgEnabled:', bgEnabled);
    updateBackgroundLayer();
    updateNavbar();
}

// 更新背景图层显示
function updateBackgroundLayer() {
    const bgLayer = document.getElementById('bgLayer');
    console.log('updateBackgroundLayer, bgLayer:', bgLayer, 'bgEnabled:', bgEnabled);
    if (bgLayer) {
        bgLayer.classList.toggle('visible', bgEnabled);
        console.log('bgLayer classes:', bgLayer.className);
    }
    // 同时更新body的类
    document.body.classList.toggle('bg-enabled', bgEnabled);
}

// 初始化背景图层
function initBackground() {
    console.log('initBackground called, bgEnabled:', bgEnabled);
    updateBackgroundLayer();
}

// 导航函数
function navigateTo(path) {
    history.pushState({}, '', path);
    handleRoute();
}

// 当前路由路径
let currentPath = '';
// 是否首次加载
let isFirstLoad = true;

// 路由处理
async function handleRoute() {
    const path = window.location.pathname;
    const content = document.getElementById('content');
    
    // 如果是同一路由且非首次加载，跳过
    if (path === currentPath && !isFirstLoad) {
        return;
    }
    currentPath = path;

    // 首次加载时先初始化导航栏
    if (isFirstLoad) {
        updateNavbar();
        isFirstLoad = false;
    }

    // 后台检查登录状态（不阻塞渲染）
    checkAuth().then(isLoggedIn => {
        // 登录状态变化时更新导航栏
        updateNavbar();
    });

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
// 题单列表进度数据缓存
let problemsetProgressData = {};

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
    
    // 如果已有缓存数据，直接渲染（避免闪烁）
    if (currentProblemSets.length > 0) {
        const categories = ['all', ...new Set(currentProblemSets.map(ps => ps.category))];
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
                ${renderProblemSetCards(currentProblemSets, problemsetProgressData)}
            </div>
        `;
        
        // 后台刷新数据（静默更新）
        refreshProblemSetData();
        return;
    }

    // 无缓存数据时显示加载状态
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>加载中...</p>
        </div>
    `;
    
    await refreshProblemSetData();
}

// 刷新题单数据（可静默执行）
async function refreshProblemSetData() {
    try {
        const data = await fetchProblemSets();
        currentProblemSets = data;
        
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
        // 缓存进度数据供分类切换使用
        problemsetProgressData = progressData;
        
        // 更新页面内容
        const content = document.getElementById('content');
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
        const content = document.getElementById('content');
        // 只有在没有数据时才显示错误
        if (currentProblemSets.length === 0) {
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

// 按分类筛选（仅更新卡片，不重新渲染整个页面）
function filterByCategory(category) {
    currentCategory = category;
    
    // 更新标签状态
    document.querySelectorAll('.category-tab').forEach(tab => {
        const tabText = tab.textContent.trim();
        const isActive = (category === 'all' && tabText === '全部') || 
                        (category !== 'all' && tabText === category);
        tab.classList.toggle('active', isActive);
    });
    
    // 仅更新卡片区域，使用缓存的进度数据
    const grid = document.getElementById('problemsetGrid');
    if (grid && currentProblemSets.length > 0) {
        grid.innerHTML = renderProblemSetCards(currentProblemSets, problemsetProgressData);
    }
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
    const maxVisibleTags = 3; // 默认显示的标签数量
    const tags = problem.tags || [];
    const hasMoreTags = tags.length > maxVisibleTags;
    const visibleTags = hasMoreTags ? tags.slice(0, maxVisibleTags) : tags;
    const hiddenTags = hasMoreTags ? tags.slice(maxVisibleTags) : [];
    const problemKey = `problem-${problem.id}`;

    return `
        <div class="problem-item ${isCompleted ? 'completed' : ''}" data-problem-id="${problem.id}">
            <div class="problem-main">
                <div class="problem-info">
                    <label class="problem-checkbox">
                        <input type="checkbox"
                               ${isCompleted ? 'checked' : ''}
                               onchange="toggleProblemProgress('${problem.id}', '${problemSetId}', this.checked)">
                        <span class="checkmark"></span>
                    </label>
                    <span class="problem-id">#${problem.id}</span>
                    <span class="problem-name">${problem.name}</span>
                </div>
                <div class="problem-meta">
                    <span class="difficulty ${getDifficultyClass(problem.difficulty)}">${problem.difficulty}</span>
                    <a href="${problem.url}" target="_blank" class="problem-link" title="前往 Codeforces" onclick="event.stopPropagation()">
                        <i class="fas fa-external-link-alt"></i>
                    </a>
                </div>
            </div>
            <div class="problem-tags-container">
                <div class="problem-tags" id="tags-${problemKey}">
                    ${visibleTags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
                ${hasMoreTags ? `
                    <div class="tags-hidden" id="tags-hidden-${problemKey}" style="display: none;">
                        ${hiddenTags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                    </div>
                    <button class="tags-toggle" id="toggle-${problemKey}" onclick="toggleTags('${problemKey}', ${hiddenTags.length})">
                        <i class="fas fa-ellipsis-h"></i>
                        <span>展开 ${hiddenTags.length} 个标签</span>
                    </button>
                ` : ''}
            </div>
            ${problem.note ? `<div class="problem-note">${problem.note}</div>` : ''}
        </div>
    `;
}

// 切换标签展开/折叠
function toggleTags(problemKey, hiddenCount) {
    const hiddenContainer = document.getElementById(`tags-hidden-${problemKey}`);
    const toggleBtn = document.getElementById(`toggle-${problemKey}`);
    const isExpanded = hiddenContainer.style.display !== 'none';

    if (isExpanded) {
        hiddenContainer.style.display = 'none';
        toggleBtn.innerHTML = '<i class="fas fa-ellipsis-h"></i><span>展开 ' + hiddenCount + ' 个标签</span>';
        toggleBtn.classList.remove('expanded');
    } else {
        hiddenContainer.style.display = 'flex';
        toggleBtn.innerHTML = '<i class="fas fa-chevron-up"></i><span>收起标签</span>';
        toggleBtn.classList.add('expanded');
    }
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

// 渲染统计页面 - 力扣风格个人主页
async function renderStatsPage() {
    const content = document.getElementById('content');

    if (!currentUser) {
        content.innerHTML = `
            <div class="error">
                <p>请先登录查看个人主页</p>
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
        // 并行获取所有数据
        const [heatmapResult, detailResult, categoryResult, problemsetResult] = await Promise.all([
            apiRequest('/progress/heatmap'),
            apiRequest('/progress/detail'),
            apiRequest('/progress/category'),
            apiRequest('/progress/problemset')
        ]);

        const heatmapData = heatmapResult.data || [];
        const detail = detailResult.data || {};
        const categories = categoryResult.data || [];
        const problemsets = problemsetResult.data || [];

        // 计算注册天数
        const createdDate = new Date(currentUser.created_at);
        const now = new Date();
        const daysSinceJoin = Math.floor((now - createdDate) / (1000 * 60 * 60 * 24)) + 1;

        // 计算难度分布角度
        const total = detail.total_completed || 1;
        const easyDeg = ((detail.easy_completed || 0) / total) * 360;
        const mediumDeg = easyDeg + ((detail.medium_completed || 0) / total) * 360;
        const hardDeg = mediumDeg + ((detail.hard_completed || 0) / total) * 360;

        content.innerHTML = `
            <div class="profile-container">
                <!-- 左侧用户信息卡片 -->
                <div class="profile-sidebar">
                    <div class="profile-card">
                        <div class="profile-avatar">
                            ${(currentUser.nickname || currentUser.username).charAt(0).toUpperCase()}
                        </div>
                        <div class="profile-name">${currentUser.nickname || currentUser.username}</div>
                        <div class="profile-username">@${currentUser.username}</div>
                        
                        <div class="profile-stats-mini">
                            <div class="profile-stat-item">
                                <div class="profile-stat-value">${detail.total_completed || 0}</div>
                                <div class="profile-stat-label">已完成</div>
                            </div>
                            <div class="profile-stat-item">
                                <div class="profile-stat-value">${detail.current_streak || 0}</div>
                                <div class="profile-stat-label">连续天数</div>
                            </div>
                            <div class="profile-stat-item">
                                <div class="profile-stat-value">${detail.max_streak || 0}</div>
                                <div class="profile-stat-label">最长连续</div>
                            </div>
                        </div>

                        <div class="profile-days">
                            <div class="profile-days-value">${daysSinceJoin}</div>
                            <div class="profile-days-label">天加入社区</div>
                        </div>
                    </div>

                    <button class="btn-secondary" onclick="navigateTo('/')" style="width: 100%;">
                        <i class="fas fa-arrow-left"></i> 返回题单列表
                    </button>
                </div>

                <!-- 右侧主内容 -->
                <div class="profile-main">
                    <!-- 进度卡片 -->
                    <div class="progress-cards">
                        <div class="progress-card all">
                            <div class="progress-card-icon"><i class="fas fa-code"></i></div>
                            <div class="progress-card-value">${detail.total_completed || 0}</div>
                            <div class="progress-card-label">已完成题目</div>
                            <div class="progress-card-sub">共 ${detail.total_problems || 0} 题</div>
                        </div>
                        <div class="progress-card easy">
                            <div class="progress-card-icon"><i class="fas fa-star"></i></div>
                            <div class="progress-card-value">${detail.easy_completed || 0}</div>
                            <div class="progress-card-label">简单</div>
                            <div class="progress-card-sub">共 ${detail.easy_total || 0} 题</div>
                        </div>
                        <div class="progress-card medium">
                            <div class="progress-card-icon"><i class="fas fa-star-half-alt"></i></div>
                            <div class="progress-card-value">${detail.medium_completed || 0}</div>
                            <div class="progress-card-label">中等</div>
                            <div class="progress-card-sub">共 ${detail.medium_total || 0} 题</div>
                        </div>
                        <div class="progress-card hard">
                            <div class="progress-card-icon"><i class="fas fa-bolt"></i></div>
                            <div class="progress-card-value">${detail.hard_completed || 0}</div>
                            <div class="progress-card-label">困难</div>
                            <div class="progress-card-sub">共 ${detail.hard_total || 0} 题</div>
                        </div>
                    </div>

                    <!-- 热力图 -->
                    <div class="heatmap-section">
                        <div class="heatmap-header">
                            <div class="heatmap-title">
                                <i class="fas fa-calendar-alt"></i>
                                刷题热力图
                            </div>
                            <div class="heatmap-legend">
                                <span>Less</span>
                                <span class="heatmap-legend-item level-0"></span>
                                <span class="heatmap-legend-item level-1"></span>
                                <span class="heatmap-legend-item level-2"></span>
                                <span class="heatmap-legend-item level-3"></span>
                                <span class="heatmap-legend-item level-4"></span>
                                <span>More</span>
                            </div>
                        </div>
                        <div class="heatmap-container">
                            ${renderHeatmap(heatmapData)}
                        </div>
                    </div>

                    <!-- 难度分布和最近活动 -->
                    <div class="stats-grid">
                        <div class="stats-box">
                            <div class="stats-box-title">
                                <i class="fas fa-chart-pie"></i>
                                难度分布
                            </div>
                            <div class="pie-chart-container">
                                <div class="pie-chart" style="--easy-deg: ${easyDeg}deg; --medium-deg: ${mediumDeg}deg; --hard-deg: ${hardDeg}deg;">
                                    <div class="pie-chart-center">
                                        <div class="pie-chart-total">${detail.total_completed || 0}</div>
                                        <div class="pie-chart-label">题目</div>
                                    </div>
                                </div>
                                <div class="pie-legend">
                                    <div class="pie-legend-item">
                                        <span class="pie-legend-color easy"></span>
                                        <span class="pie-legend-text">简单</span>
                                        <span class="pie-legend-value">${detail.easy_completed || 0}</span>
                                    </div>
                                    <div class="pie-legend-item">
                                        <span class="pie-legend-color medium"></span>
                                        <span class="pie-legend-text">中等</span>
                                        <span class="pie-legend-value">${detail.medium_completed || 0}</span>
                                    </div>
                                    <div class="pie-legend-item">
                                        <span class="pie-legend-color hard"></span>
                                        <span class="pie-legend-text">困难</span>
                                        <span class="pie-legend-value">${detail.hard_completed || 0}</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="difficulty-progress" style="margin-top: 1.5rem;">
                                ${renderDifficultyProgress(detail)}
                            </div>
                        </div>

                        <div class="stats-box">
                            <div class="stats-box-title">
                                <i class="fas fa-history"></i>
                                最近活动
                            </div>
                            <div class="activity-list">
                                ${renderRecentActivities(detail.recent_activities || [])}
                            </div>
                        </div>
                    </div>

                    <!-- 题单进度 -->
                    <div class="stats-box">
                        <div class="stats-box-title">
                            <i class="fas fa-list-check"></i>
                            题单进度
                        </div>
                        <div class="problemset-list">
                            ${renderProblemsetList(problemsets)}
                        </div>
                    </div>

                    <!-- 分类进度 -->
                    <div class="stats-box">
                        <div class="stats-box-title">
                            <i class="fas fa-folder"></i>
                            分类进度
                        </div>
                        <div class="category-progress-list">
                            ${renderCategoryList(categories)}
                        </div>
                    </div>
                </div>
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

// 渲染热力图
function renderHeatmap(data) {
    if (!data || data.length === 0) {
        return '<div class="empty-state"><i class="fas fa-calendar"></i><p>暂无刷题记录</p></div>';
    }

    // 按周分组
    const weeks = [];
    let currentWeek = [];

    data.forEach((day, index) => {
        const date = new Date(day.date);
        const dayOfWeek = date.getDay();

        // 如果是新的一周开始（周日）或者第一天
        if (dayOfWeek === 0 && currentWeek.length > 0) {
            weeks.push(currentWeek);
            currentWeek = [];
        }

        currentWeek.push(day);

        // 最后一天
        if (index === data.length - 1) {
            // 填充剩余天数
            while (currentWeek.length < 7) {
                currentWeek.push({ date: '', count: 0, level: 0 });
            }
            weeks.push(currentWeek);
        }
    });

    // 如果第一周不完整，前面补空
    if (weeks[0] && weeks[0].length < 7) {
        const padding = 7 - weeks[0].length;
        for (let i = 0; i < padding; i++) {
            weeks[0].unshift({ date: '', count: 0, level: 0 });
        }
    }

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    let lastMonth = -1;
    const monthLabels = [];

    weeks.forEach((week, weekIndex) => {
        const firstDay = week.find(d => d.date);
        if (firstDay && firstDay.date) {
            const date = new Date(firstDay.date);
            const month = date.getMonth();
            if (month !== lastMonth) {
                monthLabels.push({ month: months[month], weekIndex });
                lastMonth = month;
            }
        }
    });

    const html = `
        <div class="heatmap-grid">
            ${weeks.map(week => `
                <div class="heatmap-week">
                    ${week.map(day => day.date ? `
                        <div class="heatmap-day level-${day.level}"
                             data-date="${day.date}"
                             data-count="${day.count}"
                             onmouseenter="showHeatmapTooltip(event, '${day.date}', ${day.count})"
                             onmouseleave="hideHeatmapTooltip()">
                        </div>
                    ` : `
                        <div class="heatmap-day level-0"></div>
                    `).join('')}
                </div>
            `).join('')}
        </div>
        <div class="heatmap-months">
            ${months.map(m => `<span class="heatmap-month">${m}</span>`).join('')}
        </div>
    `;

    return html;
}

// 热力图提示框
let tooltipEl = null;

function showHeatmapTooltip(event, date, count) {
    if (!tooltipEl) {
        tooltipEl = document.createElement('div');
        tooltipEl.className = 'heatmap-tooltip';
        document.body.appendChild(tooltipEl);
    }

    const formattedDate = new Date(date).toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    tooltipEl.innerHTML = `${count} 题完成于 ${formattedDate}`;
    tooltipEl.style.left = event.clientX + 10 + 'px';
    tooltipEl.style.top = event.clientY - 30 + 'px';
    tooltipEl.style.display = 'block';
}

function hideHeatmapTooltip() {
    if (tooltipEl) {
        tooltipEl.style.display = 'none';
    }
}

// 渲染难度进度条
function renderDifficultyProgress(detail) {
    const difficulties = [
        { name: '简单', key: 'easy', completed: detail.easy_completed || 0, total: detail.easy_total || 0 },
        { name: '中等', key: 'medium', completed: detail.medium_completed || 0, total: detail.medium_total || 0 },
        { name: '困难', key: 'hard', completed: detail.hard_completed || 0, total: detail.hard_total || 0 }
    ];

    return difficulties.map(d => {
        const percentage = d.total > 0 ? Math.round((d.completed / d.total) * 100) : 0;
        return `
            <div class="difficulty-row">
                <div class="difficulty-label">
                    <span class="difficulty-dot ${d.key}"></span>
                    ${d.name}
                </div>
                <div class="difficulty-bar">
                    <div class="difficulty-bar-fill ${d.key}" style="width: ${percentage}%"></div>
                </div>
                <div class="difficulty-count">${d.completed} / ${d.total}</div>
            </div>
        `;
    }).join('');
}

// 渲染最近活动
function renderRecentActivities(activities) {
    if (!activities || activities.length === 0) {
        return `
            <div class="empty-state">
                <i class="fas fa-clock"></i>
                <p>暂无刷题记录</p>
            </div>
        `;
    }

    return activities.map(activity => {
        const diffClass = activity.difficulty < 1300 ? 'easy' : (activity.difficulty < 1700 ? 'medium' : 'hard');
        const timeAgo = formatTimeAgo(new Date(activity.completed_at));

        return `
            <div class="activity-item">
                <span class="activity-difficulty ${diffClass}">${activity.difficulty}</span>
                <div class="activity-info">
                    <div class="activity-name">#${activity.problem_id} ${activity.problem_name}</div>
                    <div class="activity-time">${timeAgo}</div>
                </div>
            </div>
        `;
    }).join('');
}

// 格式化时间
function formatTimeAgo(date) {
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes} 分钟前`;
    if (hours < 24) return `${hours} 小时前`;
    if (days < 7) return `${days} 天前`;
    return date.toLocaleDateString('zh-CN');
}

// 渲染题单列表
function renderProblemsetList(problemsets) {
    if (!problemsets || problemsets.length === 0) {
        return `
            <div class="empty-state">
                <i class="fas fa-book"></i>
                <p>暂无题单数据</p>
            </div>
        `;
    }

    return problemsets.map(ps => `
        <div class="problemset-item" onclick="navigateTo('/problemset/${ps.problemset_id}')">
            <div class="problemset-header">
                <span class="problemset-name">${ps.problemset_title}</span>
                <span class="problemset-category-badge">${ps.category}</span>
            </div>
            <div class="problemset-progress-info">
                <div class="problemset-progress-bar">
                    <div class="problemset-progress-fill" style="width: ${ps.percentage}%"></div>
                </div>
                <span class="problemset-progress-text">${ps.completed_problems}/${ps.total_problems}</span>
            </div>
        </div>
    `).join('');
}

// 渲染分类列表
function renderCategoryList(categories) {
    if (!categories || categories.length === 0) {
        return `
            <div class="empty-state">
                <i class="fas fa-folder-open"></i>
                <p>暂无分类数据</p>
            </div>
        `;
    }

    return categories.map(cat => `
        <div class="category-progress-item">
            <div class="category-info">
                <span class="category-name">${cat.category}</span>
                <span class="category-stats">${cat.completed_problems}/${cat.total_problems}</span>
            </div>
            <div class="category-progress-bar">
                <div class="category-bar">
                    <div class="category-bar-fill" style="width: ${cat.percentage}%"></div>
                </div>
                <span class="category-text">${cat.percentage}%</span>
            </div>
        </div>
    `).join('');
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
document.addEventListener('DOMContentLoaded', () => {
    initBackground();
    handleRoute();
});