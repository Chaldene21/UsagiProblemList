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
            <button class="nav-btn" onclick="navigateTo('/search')" title="搜索用户">
                <i class="fas fa-search"></i>
            </button>
            <button class="nav-btn" onclick="navigateTo('/guide')" title="使用指南">
                <i class="fas fa-book-open"></i>
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
            <button class="nav-btn" onclick="navigateTo('/search')" title="搜索用户">
                <i class="fas fa-search"></i>
            </button>
            <button class="nav-btn" onclick="navigateTo('/guide')" title="使用指南">
                <i class="fas fa-book-open"></i>
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
    } else if (path === '/guide') {
        renderGuidePage();
    } else if (path === '/search') {
        renderUserSearchPage();
    } else if (path.startsWith('/user/')) {
        const parts = path.split('/');
        const userId = parts[2];
        if (parts[3] === 'followers') {
            renderFollowListPage(userId, 'followers');
        } else if (parts[3] === 'followings') {
            renderFollowListPage(userId, 'followings');
        } else {
            renderUserProfilePage(userId);
        }
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

// 从标题中提取章节编号（如 "§3.1 二分+贪心" -> "3.1"）
function extractSectionNumber(title) {
    const match = title.match(/§(\d+(?:\.\d+)*)/);
    return match ? match[1] : null;
}

// 计算章节层级深度（如 "3.1.1" -> 3）
function getSectionDepth(number) {
    if (!number) return 0;
    return number.split('.').length;
}

// 生成章节锚点 ID
function generateSectionId(sectionIndex, subsectionNumber) {
    if (subsectionNumber) {
        return `section-${subsectionNumber.replace(/\./g, '-')}`;
    }
    return `section-${sectionIndex}`;
}

// 生成目录结构
function generateTOC(sections) {
    const tocItems = [];
    
    sections.forEach((section, sectionIndex) => {
        // 添加顶级章节
        tocItems.push({
            title: section.title,
            id: generateSectionId(sectionIndex, null),
            depth: 0,
            isSection: true
        });
        
        // 遍历子章节
        section.content.forEach((item, itemIndex) => {
            if (item.type !== 'paragraph' && item.title) {
                const number = extractSectionNumber(item.title);
                const depth = getSectionDepth(number);
                tocItems.push({
                    title: item.title,
                    id: generateSectionId(sectionIndex, number),
                    depth: depth,
                    isSection: false
                });
            }
        });
    });
    
    return tocItems;
}

// 渲染目录
function renderTOC(tocItems) {
    if (tocItems.length === 0) return '';
    
    return `
        <div class="toc-container">
            <div class="toc-header">
                <i class="fas fa-list"></i>
                <span>目录</span>
                <button class="toc-toggle" onclick="toggleTOC()">
                    <i class="fas fa-chevron-up"></i>
                </button>
            </div>
            <div class="toc-content" id="tocContent">
                ${tocItems.map(item => `
                    <a href="#${item.id}" 
                       class="toc-item depth-${item.depth} ${item.isSection ? 'section-title' : ''}"
                       onclick="scrollToSection('${item.id}', event)">
                        ${item.title}
                    </a>
                `).join('')}
            </div>
        </div>
    `;
}

// 切换目录展开/折叠
function toggleTOC() {
    const tocContent = document.getElementById('tocContent');
    const toggleBtn = document.querySelector('.toc-toggle i');
    if (tocContent) {
        tocContent.classList.toggle('collapsed');
        if (tocContent.classList.contains('collapsed')) {
            toggleBtn.className = 'fas fa-chevron-down';
        } else {
            toggleBtn.className = 'fas fa-chevron-up';
        }
    }
}

// 滚动到指定章节
function scrollToSection(id, event) {
    event.preventDefault();
    const element = document.getElementById(id);
    if (element) {
        const offset = 100; // 顶部偏移量，避免被导航栏遮挡
        const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
        window.scrollTo({
            top: elementPosition - offset,
            behavior: 'smooth'
        });
        
        // 高亮当前章节
        document.querySelectorAll('.toc-item').forEach(item => item.classList.remove('active'));
        event.target.classList.add('active');
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
        
        // 生成目录
        const tocItems = generateTOC(problemSet.sections);

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

                ${renderTOC(tocItems)}

                <div class="sections">
                    ${problemSet.sections.map((section, sectionIndex) => renderSection(section, id, completedIds, sectionIndex)).join('')}
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
function renderSection(section, problemSetId, completedIds, sectionIndex) {
    const sectionId = generateSectionId(sectionIndex, null);
    return `
        <div class="section" id="${sectionId}">
            <h2 class="section-title">${section.title}</h2>
            <div class="section-content">
                ${section.content.map((item, itemIndex) => renderContentItem(item, problemSetId, completedIds, sectionIndex)).join('')}
            </div>
        </div>
    `;
}

// 渲染内容项
function renderContentItem(item, problemSetId, completedIds, sectionIndex) {
    if (item.type === 'paragraph') {
        return `<div class="paragraph">${item.text}</div>`;
    }

    // 子章节对象 - 添加锚点 ID
    const subsectionNumber = item.title ? extractSectionNumber(item.title) : null;
    const subsectionId = subsectionNumber ? generateSectionId(sectionIndex, subsectionNumber) : '';
    
    return `
        <div class="subsection" ${subsectionId ? `id="${subsectionId}"` : ''}>
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
    const tags = problem.tags || [];
    const hasDetails = tags.length > 0 || problem.note;
    const problemKey = `problem-${problem.id}`;

    return `
        <div class="problem-item ${isCompleted ? 'completed' : ''}" data-problem-id="${problem.id}">
            <div class="problem-main">
                <div class="problem-info">
                    <label class="problem-checkbox" onclick="event.stopPropagation()">
                        <input type="checkbox"
                               ${isCompleted ? 'checked' : ''}
                               onchange="toggleProblemProgress('${problem.id}', '${problemSetId}', this.checked)">
                        <span class="checkmark"></span>
                    </label>
                    <a href="${problem.url}" target="_blank" class="problem-link-main" onclick="event.stopPropagation()">
                        <span class="problem-id">#${problem.id}</span>
                        <span class="problem-name">${problem.name}</span>
                    </a>
                </div>
                <div class="problem-meta">
                    <span class="difficulty ${getDifficultyClass(problem.difficulty)}">${problem.difficulty}</span>
                    ${hasDetails ? `
                        <button class="details-toggle" onclick="toggleProblemDetails('${problemKey}', event)">
                            <i class="fas fa-chevron-down"></i>
                        </button>
                    ` : ''}
                </div>
            </div>
            ${hasDetails ? `
                <div class="problem-details" id="details-${problemKey}" style="display: none;">
                    ${tags.length > 0 ? `
                        <div class="problem-tags">
                            ${tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                        </div>
                    ` : ''}
                    ${problem.note ? `<div class="problem-note">${problem.note}</div>` : ''}
                </div>
            ` : ''}
        </div>
    `;
}

// 切换题目详情展开/折叠
function toggleProblemDetails(problemKey, event) {
    event.stopPropagation();
    const detailsContainer = document.getElementById(`details-${problemKey}`);
    const toggleBtn = event.currentTarget;
    const isExpanded = detailsContainer.style.display !== 'none';

    if (isExpanded) {
        detailsContainer.style.display = 'none';
        toggleBtn.innerHTML = '<i class="fas fa-chevron-down"></i>';
        toggleBtn.classList.remove('expanded');
    } else {
        detailsContainer.style.display = 'block';
        toggleBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
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

// 渲染新手指引页面
function renderGuidePage() {
    const content = document.getElementById('content');

    content.innerHTML = `
        <div class="guide-container">
            <!-- 页面头部 -->
            <div class="guide-header">
                <div class="guide-header-content">
                    <div class="guide-logo">
                        <i class="fas fa-mug-hot"></i>
                    </div>
                    <h1 class="guide-title">欢迎使用 Rabbit House</h1>
                    <p class="guide-subtitle">Codeforces 算法题单训练平台 · 新手指南</p>
                </div>
            </div>

            <!-- 快速开始卡片 -->
            <div class="guide-section">
                <div class="guide-card hero-card">
                    <div class="hero-content">
                        <div class="hero-text">
                            <h2><i class="fas fa-rocket"></i> 30秒快速上手</h2>
                            <p>跟随指引，快速开启你的刷题之旅</p>
                        </div>
                        <button class="hero-btn" onclick="navigateTo('/')">
                            开始刷题 <i class="fas fa-arrow-right"></i>
                        </button>
                    </div>
                </div>
            </div>

            <!-- 功能介绍 -->
            <div class="guide-section">
                <h2 class="section-title">
                    <i class="fas fa-star"></i>
                    核心功能
                </h2>
                <div class="guide-grid">
                    <div class="guide-card feature-card">
                        <div class="feature-icon pink">
                            <i class="fas fa-list-alt"></i>
                        </div>
                        <h3>精选题单</h3>
                        <p>精选 Codeforces 算法题单，涵盖基础到进阶，系统化提升算法能力</p>
                    </div>
                    <div class="guide-card feature-card">
                        <div class="feature-icon blue">
                            <i class="fas fa-tasks"></i>
                        </div>
                        <h3>进度追踪</h3>
                        <p>记录你的刷题进度，标记已完成题目，随时回顾学习状态</p>
                    </div>
                    <div class="guide-card feature-card">
                        <div class="feature-icon purple">
                            <i class="fas fa-chart-line"></i>
                        </div>
                        <h3>数据统计</h3>
                        <p>可视化刷题数据，热力图展示刷题频率，了解你的学习节奏</p>
                    </div>
                    <div class="guide-card feature-card">
                        <div class="feature-icon green">
                            <i class="fas fa-lightbulb"></i>
                        </div>
                        <h3>解题思路</h3>
                        <p>每道题目附带解题思路和代码模板，助力理解算法精髓</p>
                    </div>
                </div>
            </div>

            <!-- 使用步骤 -->
            <div class="guide-section">
                <h2 class="section-title">
                    <i class="fas fa-route"></i>
                    使用步骤
                </h2>
                <div class="steps-container">
                    <div class="step-card">
                        <div class="step-number">1</div>
                        <div class="step-content">
                            <h3>注册账号</h3>
                            <p>点击右上角「注册」按钮，创建你的专属账号，保存刷题进度</p>
                        </div>
                        <div class="step-icon">
                            <i class="fas fa-user-plus"></i>
                        </div>
                    </div>
                    <div class="step-arrow">
                        <i class="fas fa-chevron-down"></i>
                    </div>
                    <div class="step-card">
                        <div class="step-number">2</div>
                        <div class="step-content">
                            <h3>选择题单</h3>
                            <p>浏览题单列表，根据分类选择适合你当前水平的题单开始练习</p>
                        </div>
                        <div class="step-icon">
                            <i class="fas fa-book-open"></i>
                        </div>
                    </div>
                    <div class="step-arrow">
                        <i class="fas fa-chevron-down"></i>
                    </div>
                    <div class="step-card">
                        <div class="step-number">3</div>
                        <div class="step-content">
                            <h3>刷题练习</h3>
                            <p>点击题目链接跳转 Codeforces 提交代码，完成后勾选标记进度</p>
                        </div>
                        <div class="step-icon">
                            <i class="fas fa-code"></i>
                        </div>
                    </div>
                    <div class="step-arrow">
                        <i class="fas fa-chevron-down"></i>
                    </div>
                    <div class="step-card">
                        <div class="step-number">4</div>
                        <div class="step-content">
                            <h3>查看统计</h3>
                            <p>登录后点击「个人主页」查看刷题统计、热力图和进度分析</p>
                        </div>
                        <div class="step-icon">
                            <i class="fas fa-chart-bar"></i>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 难度说明 -->
            <div class="guide-section">
                <h2 class="section-title">
                    <i class="fas fa-layer-group"></i>
                    难度分级
                </h2>
                <div class="difficulty-cards">
                    <div class="difficulty-card easy">
                        <div class="diff-header">
                            <i class="fas fa-seedling"></i>
                            <span class="diff-range">Rating &lt; 1300</span>
                        </div>
                        <h3>简单</h3>
                        <p>适合入门选手，帮助建立编程思维和基础语法熟练度</p>
                    </div>
                    <div class="difficulty-card medium">
                        <div class="diff-header">
                            <i class="fas fa-fire"></i>
                            <span class="diff-range">1300 ≤ Rating &lt; 1700</span>
                        </div>
                        <h3>中等</h3>
                        <p>需要掌握一定算法思想，提升问题分析和解决能力</p>
                    </div>
                    <div class="difficulty-card hard">
                        <div class="diff-header">
                            <i class="fas fa-bolt"></i>
                            <span class="diff-range">Rating ≥ 1700</span>
                        </div>
                        <h3>困难</h3>
                        <p>挑战高难度问题，精进算法技巧，冲击更高 Rating</p>
                    </div>
                </div>
            </div>

            <!-- 常见问题 -->
            <div class="guide-section">
                <h2 class="section-title">
                    <i class="fas fa-question-circle"></i>
                    常见问题
                </h2>
                <div class="faq-container">
                    <div class="faq-item">
                        <div class="faq-question" onclick="toggleFaq(this)">
                            <i class="fas fa-plus-circle"></i>
                            <span>题目链接无法打开怎么办？</span>
                        </div>
                        <div class="faq-answer">
                            <p>题目链接指向 Codeforces 官网，请确保你能正常访问 Codeforces。如果网络不稳定，可以尝试使用代理或 VPN。</p>
                        </div>
                    </div>
                    <div class="faq-item">
                        <div class="faq-question" onclick="toggleFaq(this)">
                            <i class="fas fa-plus-circle"></i>
                            <span>进度数据会丢失吗？</span>
                        </div>
                        <div class="faq-answer">
                            <p>进度数据与你的账号绑定，存储在服务器数据库中。只要使用同一账号登录，进度就不会丢失。</p>
                        </div>
                    </div>
                    <div class="faq-item">
                        <div class="faq-question" onclick="toggleFaq(this)">
                            <i class="fas fa-plus-circle"></i>
                            <span>可以在手机上使用吗？</span>
                        </div>
                        <div class="faq-answer">
                            <p>网站采用响应式设计，支持手机、平板等移动设备访问，随时随地刷题学习。</p>
                        </div>
                    </div>
                    <div class="faq-item">
                        <div class="faq-question" onclick="toggleFaq(this)">
                            <i class="fas fa-plus-circle"></i>
                            <span>如何提高刷题效率？</span>
                        </div>
                        <div class="faq-answer">
                            <p>建议按照题单顺序系统学习，每道题先独立思考，遇到困难再参考解题思路。坚持每日刷题，保持手感！</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 底部行动按钮 -->
            <div class="guide-footer">
                <div class="footer-decor">
                    <i class="fas fa-heart"></i>
                    <i class="fas fa-coffee"></i>
                    <i class="fas fa-heart"></i>
                </div>
                <p class="footer-text">准备好了吗？开始你的算法之旅吧！</p>
                <button class="guide-start-btn" onclick="navigateTo('/')">
                    <i class="fas fa-play"></i>
                    立即开始
                </button>
            </div>
        </div>
    `;
}

// 切换FAQ展开/收起
function toggleFaq(element) {
    const faqItem = element.parentElement;
    const isExpanded = faqItem.classList.contains('expanded');
    
    // 关闭其他展开的FAQ
    document.querySelectorAll('.faq-item.expanded').forEach(item => {
        if (item !== faqItem) {
            item.classList.remove('expanded');
            item.querySelector('.faq-question i').className = 'fas fa-plus-circle';
        }
    });
    
    // 切换当前FAQ
    faqItem.classList.toggle('expanded');
    const icon = element.querySelector('i');
    icon.className = isExpanded ? 'fas fa-plus-circle' : 'fas fa-minus-circle';
}

// 渲染统计页面 - 力扣风格个人主页
async function renderStatsPage() {
    const content = document.getElementById('content');

    // 先尝试恢复登录状态（解决刷新页面时 currentUser 未恢复的问题）
    if (!currentUser && authToken) {
        await checkAuth(true);
    }

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

// ==================== 用户交互功能 ====================

// 搜索用户
async function searchUsers(keyword) {
    const result = await apiRequest(`/users/search?keyword=${encodeURIComponent(keyword)}`);
    if (result.code === 0) {
        return result.data;
    }
    return null;
}

// 获取用户资料
async function getUserProfile(userId) {
    const result = await apiRequest(`/users/${userId}`);
    if (result.code === 0) {
        return result.data;
    }
    return null;
}

// 关注用户
async function followUser(userId) {
    if (!currentUser) {
        alert('请先登录');
        showLogin();
        return false;
    }

    const result = await apiRequest(`/users/${userId}/follow`, {
        method: 'POST'
    });

    if (result.code === 0) {
        return true;
    }
    alert(result.message);
    return false;
}

// 取消关注
async function unfollowUser(userId) {
    if (!currentUser) {
        alert('请先登录');
        showLogin();
        return false;
    }

    const result = await apiRequest(`/users/${userId}/follow`, {
        method: 'DELETE'
    });

    if (result.code === 0) {
        return true;
    }
    alert(result.message);
    return false;
}

// 获取粉丝列表
async function getFollowers(userId) {
    const result = await apiRequest(`/users/${userId}/followers`);
    if (result.code === 0) {
        return result.data;
    }
    return null;
}

// 获取关注列表
async function getFollowings(userId) {
    const result = await apiRequest(`/users/${userId}/followings`);
    if (result.code === 0) {
        return result.data;
    }
    return null;
}

// 渲染用户搜索页面
async function renderUserSearchPage() {
    const content = document.getElementById('content');

    content.innerHTML = `
        <div class="search-page">
            <div class="page-header">
                <h1 class="page-title"><i class="fas fa-search"></i> 搜索用户</h1>
                <p class="page-subtitle">找到志同道合的刷题伙伴</p>
            </div>

            <div class="search-box">
                <input type="text" id="searchKeyword" placeholder="输入用户名或昵称搜索..."
                       onkeypress="if(event.key==='Enter') performUserSearch()">
                <button class="btn-primary" onclick="performUserSearch()">
                    <i class="fas fa-search"></i> 搜索
                </button>
            </div>

            <div id="searchResults" class="search-results"></div>
        </div>
    `;
}

// 执行用户搜索
async function performUserSearch() {
    const keyword = document.getElementById('searchKeyword').value.trim();
    const resultsContainer = document.getElementById('searchResults');

    if (!keyword) {
        resultsContainer.innerHTML = '<p class="search-hint">请输入搜索关键词</p>';
        return;
    }

    resultsContainer.innerHTML = '<div class="loading"><div class="spinner"></div><p>搜索中...</p></div>';

    const result = await searchUsers(keyword);

    if (!result || result.users.length === 0) {
        resultsContainer.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-user-slash"></i>
                <p>未找到匹配的用户</p>
            </div>
        `;
        return;
    }

    resultsContainer.innerHTML = `
        <div class="search-result-info">找到 ${result.total} 个用户</div>
        <div class="user-grid">
            ${result.users.map(user => renderUserCard(user)).join('')}
        </div>
    `;
}

// 渲染用户卡片
function renderUserCard(user) {
    // 使用 == 比较，避免类型问题
    const isSelf = currentUser && currentUser.id == user.id;

    return `
        <div class="user-card" onclick="navigateTo('/user/${user.id}')">
            <div class="user-card-avatar">
                ${(user.nickname || user.username).charAt(0).toUpperCase()}
            </div>
            <div class="user-card-info">
                <div class="user-card-name">${user.nickname || user.username}</div>
                <div class="user-card-username">@${user.username}</div>
                <div class="user-card-stats">
                    <span><i class="fas fa-code"></i> ${user.total_completed || 0} 题</span>
                </div>
            </div>
            <div class="user-card-actions" onclick="event.stopPropagation()">
                ${!isSelf && currentUser ? `
                    <button class="btn-follow ${user.is_following ? 'following' : ''}"
                            onclick="toggleFollow(${user.id}, ${user.is_following}, this)">
                        ${user.is_following ? '已关注' : '关注'}
                    </button>
                ` : ''}
            </div>
        </div>
    `;
}

// 切换关注状态
async function toggleFollow(userId, isFollowing, btn) {
    let success;
    if (isFollowing) {
        success = await unfollowUser(userId);
    } else {
        success = await followUser(userId);
    }

    if (success) {
        btn.classList.toggle('following');
        btn.textContent = isFollowing ? '关注' : '已关注';
        btn.onclick = (e) => {
            e.stopPropagation();
            toggleFollow(userId, !isFollowing, btn);
        };
    }
}

// 渲染用户主页
async function renderUserProfilePage(userId) {
    const content = document.getElementById('content');

    content.innerHTML = '<div class="loading"><div class="spinner"></div><p>加载中...</p></div>';

    const profile = await getUserProfile(userId);

    if (!profile) {
        content.innerHTML = `
            <div class="error">
                <p>用户不存在</p>
                <button onclick="navigateTo('/')" class="btn-primary" style="margin-top: 1rem;">
                    返回首页
                </button>
            </div>
        `;
        return;
    }

    // 使用 == 比较，避免类型问题
    const isSelf = currentUser && currentUser.id == profile.id;

    content.innerHTML = `
        <div class="profile-container">
            <!-- 左侧用户信息卡片 -->
            <div class="profile-sidebar">
                <div class="profile-card">
                    <div class="profile-avatar">
                        ${(profile.nickname || profile.username).charAt(0).toUpperCase()}
                    </div>
                    <div class="profile-name">${profile.nickname || profile.username}</div>
                    <div class="profile-username">@${profile.username}</div>

                    <div class="profile-stats-mini">
                        <div class="profile-stat-item clickable" onclick="navigateTo('/user/${profile.id}/followings')">
                            <div class="profile-stat-value">${profile.followings_count || 0}</div>
                            <div class="profile-stat-label">关注</div>
                        </div>
                        <div class="profile-stat-item clickable" onclick="navigateTo('/user/${profile.id}/followers')">
                            <div class="profile-stat-value">${profile.followers_count || 0}</div>
                            <div class="profile-stat-label">粉丝</div>
                        </div>
                    </div>

                    <div class="profile-stats-mini">
                        <div class="profile-stat-item">
                            <div class="profile-stat-value">${profile.total_completed || 0}</div>
                            <div class="profile-stat-label">已完成</div>
                        </div>
                        <div class="profile-stat-item">
                            <div class="profile-stat-value">${profile.current_streak || 0}</div>
                            <div class="profile-stat-label">连续天数</div>
                        </div>
                        <div class="profile-stat-item">
                            <div class="profile-stat-value">${profile.max_streak || 0}</div>
                            <div class="profile-stat-label">最长连续</div>
                        </div>
                    </div>

                    <div class="profile-days">
                        <div class="profile-days-value">${profile.created_at ? calculateDaysSince(profile.created_at) : '-'}</div>
                        <div class="profile-days-label">天加入社区</div>
                    </div>

                    ${!isSelf && currentUser ? `
                        <div class="profile-actions">
                            <button class="btn-follow-large ${profile.is_following ? 'following' : ''}"
                                    onclick="toggleProfileFollow(${profile.id}, ${profile.is_following})">
                                <i class="fas ${profile.is_following ? 'fa-check' : 'fa-plus'}"></i>
                                ${profile.is_following ? '已关注' : '关注'}
                            </button>
                        </div>
                    ` : ''}
                </div>

                <button class="btn-secondary" onclick="navigateTo('/')" style="width: 100%;">
                    <i class="fas fa-arrow-left"></i> 返回题单列表
                </button>
            </div>

            <!-- 右侧主内容 -->
            <div class="profile-main">
                <div class="stats-box">
                    <div class="stats-box-title">
                        <i class="fas fa-chart-bar"></i>
                        刷题统计
                    </div>
                    <div class="profile-stats-grid">
                        <div class="profile-stat-card">
                            <div class="stat-icon"><i class="fas fa-code"></i></div>
                            <div class="stat-info">
                                <div class="stat-value">${profile.total_completed || 0}</div>
                                <div class="stat-label">已完成题目</div>
                            </div>
                        </div>
                        <div class="profile-stat-card">
                            <div class="stat-icon"><i class="fas fa-fire"></i></div>
                            <div class="stat-info">
                                <div class="stat-value">${profile.current_streak || 0}</div>
                                <div class="stat-label">当前连续</div>
                            </div>
                        </div>
                        <div class="profile-stat-card">
                            <div class="stat-icon"><i class="fas fa-trophy"></i></div>
                            <div class="stat-info">
                                <div class="stat-value">${profile.max_streak || 0}</div>
                                <div class="stat-label">最长连续</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="stats-box">
                    <div class="stats-box-title">
                        <i class="fas fa-users"></i>
                        关注信息
                    </div>
                    <div class="follow-stats">
                        <div class="follow-stat-item" onclick="navigateTo('/user/${profile.id}/followings')">
                            <span class="follow-stat-count">${profile.followings_count || 0}</span>
                            <span class="follow-stat-label">关注</span>
                        </div>
                        <div class="follow-stat-item" onclick="navigateTo('/user/${profile.id}/followers')">
                            <span class="follow-stat-count">${profile.followers_count || 0}</span>
                            <span class="follow-stat-label">粉丝</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// 切换主页关注状态
async function toggleProfileFollow(userId, isFollowing) {
    let success;
    if (isFollowing) {
        success = await unfollowUser(userId);
    } else {
        success = await followUser(userId);
    }

    if (success) {
        // 重新渲染页面
        renderUserProfilePage(userId);
    }
}

// 计算加入天数
function calculateDaysSince(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    return Math.floor((now - date) / (1000 * 60 * 60 * 24)) + 1;
}

// 渲染关注/粉丝列表页面
async function renderFollowListPage(userId, type) {
    const content = document.getElementById('content');

    content.innerHTML = '<div class="loading"><div class="spinner"></div><p>加载中...</p></div>';

    // 获取用户资料用于显示标题
    const profile = await getUserProfile(userId);

    // 获取列表数据
    let result;
    if (type === 'followers') {
        result = await getFollowers(userId);
    } else {
        result = await getFollowings(userId);
    }

    if (!result) {
        content.innerHTML = `
            <div class="error">
                <p>加载失败</p>
                <button onclick="navigateTo('/user/${userId}')" class="btn-primary" style="margin-top: 1rem;">
                    返回用户主页
                </button>
            </div>
        `;
        return;
    }

    const title = type === 'followers' ? '粉丝列表' : '关注列表';
    const count = type === 'followers' ? (profile?.followers_count || 0) : (profile?.followings_count || 0);

    content.innerHTML = `
        <div class="follow-list-page">
            <div class="page-header">
                <div class="back-button" onclick="navigateTo('/user/${userId}')">
                    <i class="fas fa-arrow-left"></i>
                    返回主页
                </div>
                <h1 class="page-title">${title}</h1>
                <p class="page-subtitle">共 ${count} 人</p>
            </div>

            <div class="user-grid">
                ${result.users.length > 0 ? result.users.map(user => renderUserCard(user)).join('') : `
                    <div class="empty-state" style="grid-column: 1/-1;">
                        <i class="fas fa-users"></i>
                        <p>${type === 'followers' ? '暂无粉丝' : '暂无关注'}</p>
                    </div>
                `}
            </div>
        </div>
    `;
}

// 处理浏览器前进/后退
window.addEventListener('popstate', handleRoute);

// 页面加载完成后处理路由
document.addEventListener('DOMContentLoaded', () => {
    initBackground();
    handleRoute();
});