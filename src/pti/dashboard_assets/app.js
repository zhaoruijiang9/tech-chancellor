var state = { summary: null, view: 'home', capabilities: [], documents: [], activity: [], detailId: null, librarySection: 'mine' };
var app = document.querySelector('#app');
var VIEW_LABELS = {home:'总览',capabilities:'能力库',activity:'最近动态',system:'系统状态',documents:'文档'};
var NAME_MAP = {'tt-a1i/archify':'Archify','github/spec-kit':'Spec Kit','bmad-code-org/BMAD-METHOD':'BMAD Method','langchain-ai/langchain':'LangChain','coleam00/archon':'Archon','TauricResearch/TradingAgents':'TradingAgents','nieledran/backtesting-engine':'backtesting-engine','sentrux/sentrux':'Sentrux'};
var CATEGORY_MAP = {'AI_AGENT':'AI / 智能体','AI_EXPERIENCE':'AI / 体验','QUANT_DATA':'量化 / 数据','WATCHLIST':'观察清单','DEVELOPER_TOOL':'开发工具','KNOWLEDGE':'知识与方法','GENERAL':'其他'};
var STATUS_MAP = {'USED':'已经实际使用','USABLE':'现在可以使用','ADOPTED_METHOD':'已采用的方法','WAITING_VALIDATION':'已批准，等待验证','VALIDATING':'正在验证','HUMAN_DECISION':'需要你决定','WATCHLIST':'继续观察','NOT_ADOPTED':'暂不采用','VALIDATION_FAILED':'验证未通过','ARCHIVED':'已归档','TRIAL_ENABLED':'可直接使用','ACTIVE_PATTERN':'知识参考','REFERENCE_ONLY':'知识参考','QUARANTINE_READY':'等待验证','CANDIDATE_FOR_QUARANTINE':'进入验证','BLOCKED_HUMAN':'需要你决定','FAILED_VALIDATION':'验证未通过','REVIEWED':'已完成判断','SCAN_SUCCESS':'扫描完成','SCAN_NOT_EVALUATED':'扫描需要注意','CHANCELLOR_SUCCESS':'处理完成','CHANCELLOR_SUCCESS_NO_PENDING':'处理完成，无待办','RUNNING':'运行中','COMPLETED':'已完成','SUCCESS':'正常','DEGRADED':'有运行提醒','DEGRADED_HISTORY_ONLY':'有历史提醒','NOT_EVALUATED':'需要注意'};
var FEEDBACK_LABELS = {'APPROVE_FOR_REVIEW':'可继续隔离评估','WATCH':'继续观察','NOT_USEFUL':'暂不采用','TOO_RISKY':'风险过高，暂不采用'};
var DELTA_LABELS = {'NO_RELEVANT_CHANGE':'变化不影响原判断','REVIEW_STILL_VALID':'原判断仍适用','REVIEW_UPDATED':'判断已更新','REVALIDATION_REQUIRED':'需要重新验证','OWNER_DECISION_MAY_CHANGE':'可能需要重新决定'};

function esc(value) { return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
function date(value, technical) { if (!value) return '暂无'; var d = new Date(value); if (isNaN(d.getTime())) return String(value); return d.toLocaleString('zh-CN', technical ? {hour12:false} : {year:'numeric',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}); }
function displayName(repo) { return NAME_MAP[repo] || String(repo || '未命名能力').split('/').pop().replace(/[-_]+/g, ' '); }
function category(value) { return CATEGORY_MAP[value] || String(value || '其他').replace(/_/g, ' '); }
function humanStatus(value) { return STATUS_MAP[value] || String(value || '暂无').replace(/_/g, ' '); }
function statusClass(value) { var s = String(value || ''); if (['USED','USABLE','ADOPTED_METHOD','TRIAL_ENABLED','SUCCESS','正常'].indexOf(s) >= 0) return 'ok'; if (s.indexOf('FAIL') >= 0 || s.indexOf('NOT_ADOPTED') >= 0 || s === '异常' || s === 'NOT_EVALUATED') return 'bad'; if (s.indexOf('BLOCKED') >= 0 || s === 'HUMAN_DECISION' || s.indexOf('DEGRADED') >= 0 || s.indexOf('NEED') >= 0 || s.indexOf('提醒') >= 0) return 'warn'; if (s.indexOf('QUARANTINE') >= 0 || s.indexOf('CANDIDATE') >= 0 || s === 'VALIDATING' || s === 'RUNNING') return 'info'; return 'neutral'; }
function chip(value, label) { return '<span class="status-chip ' + statusClass(value) + '"><span class="status-dot" aria-hidden="true"></span>' + esc(label || humanStatus(value)) + '</span>'; }
function tag(label, cls) { return '<span class="tag ' + (cls || '') + '">' + esc(label) + '</span>'; }
function getJSON(url) { return fetch(url, {cache:'no-store'}).then(function (response) { if (!response.ok) throw new Error(response.statusText); return response.json(); }); }
function postJSON(url, payload) { return fetch(url, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).then(function (response) { return response.json().then(function (body) { if (!response.ok) throw new Error(body.error || response.statusText); return body; }); }); }
function issueLabel(value) { if (value === 'PIPELINE_STALLED') return '候选评审交接停滞'; if (String(value).indexOf('UPSTREAM_CHECK_') === 0) return '上游变化监测未完成'; return {'UPSTREAM_REVIEW_NEEDS_ATTENTION':'上游增量复审需要检查','ACTIVE_PENDING_PACKETS':'Chancellor 尚有待重试项目','TASK_LAST_RESULT_NONZERO':'计划任务上次未完整结束','STALE_OR_MALFORMED_LOCK':'后台锁需要检查','INCOMPLETE_SCAN_RUN':'存在未完成扫描记录'}[value] || humanStatus(value); }
function issueDetail(value) { if (String(value).indexOf('UPSTREAM_CHECK_') === 0) return value.indexOf('RATE_LIMIT') >= 0 ? 'GitHub API 配额不足，本轮监测未完成；不会把失败误判为无更新。' : value.indexOf('NETWORK') >= 0 ? '网络请求失败，本轮监测未完成；下次运行会重试。' : '上游监测遇到异常，已有指纹与判断不会被覆盖。'; return {'UPSTREAM_REVIEW_NEEDS_ATTENTION':'有变化已排队，但自动复审多次未完成；旧判断仍标记为待复审。','ACTIVE_PENDING_PACKETS':'这是后台判断队列，不需要你手动处理；Chancellor 会在下次运行继续尝试。','TASK_LAST_RESULT_NONZERO':'上次后台判断未完整结束，证据已保留；若后续运行恢复正常，无需你操作。','STALE_OR_MALFORMED_LOCK':'后台锁可能需要检查，系统不会在锁状态不明时继续写入。','INCOMPLETE_SCAN_RUN':'最近一次扫描没有形成完整结论，不能据此判断为没有项目。'}[value] || '该提醒来自已有健康检查，不影响能力库读取。'; }
function formLabel(item) { return item.capability_id ? '能力' : item.method_id ? '方法' : item.item_kind === 'METHOD_SOURCE' ? '方法来源' : item.entity_kind === 'SOURCE' ? '来源项目' : item.item_kind === 'CANDIDATE' ? '候选项目' : item.item_kind === 'PROJECT' ? '项目' : '知识参考'; }
function primaryStatusLabel(item) { return item.human_category_label || humanStatus(item.human_category) || item.lifecycle_status || humanStatus(item.activation_state); }
function taskResultLabel(value, status) { if (status === 'NOT_INSTALLED') return '未安装（可选）'; if (value === 0 || value === '0') return '上次运行正常'; if (value == null || value === '' || value === 'UNKNOWN') return '暂无运行记录'; return '上次运行需检查'; }
function collectionReason(item) { return item.classification_reason || 'TechChancellor 已完成项目判断并保留记录，便于后续追踪和重新评估。'; }
function artPosition(value) { var hash = 0; String(value || '').split('').forEach(function (char) { hash = ((hash << 5) - hash) + char.charCodeAt(0); hash |= 0; }); return Math.abs(hash % 5) * 25; }
function chineseFirst(value, fallback) { return /[\u3400-\u9fff]/.test(String(value || '')) ? value : fallback; }
function quietState(title, detail) { return '<div class="quiet-state"><span class="quiet-mark">✓</span><div><strong>' + esc(title) + '</strong><p>' + esc(detail) + '</p></div></div>'; }
function viewHeader(kicker, title, subtitle, extra) { return '<div class="page-head"><div><span class="kicker">' + esc(kicker) + '</span><h1>' + esc(title) + '</h1><p>' + esc(subtitle) + '</p></div>' + (extra || '') + '</div>'; }
function bulletList(items, emptyText) { var values = (items || []).filter(Boolean); return values.length ? '<ul class="clean-list">' + values.map(function (item) { return '<li>' + esc(item) + '</li>'; }).join('') + '</ul>' : '<p class="muted">' + esc(emptyText) + '</p>'; }
function decisionPanel(item) {
  if (!item.human_action_required) return '';
  var selected = item.human_decision && item.human_decision.label || '';
  var intro = selected ? '当前已记录“' + (FEEDBACK_LABELS[selected] || humanStatus(selected)) + '”。你可以重新选择，最后一次记录为准。' : '这项能力触及较高风险或较重集成边界，需要你明确选择后续方向。';
  function option(label, copy, primary) { return '<button class="decision-button' + (primary ? ' primary' : '') + '" data-feedback-label="' + label + '" data-feedback-repository="' + esc(item.repository) + '" aria-pressed="' + (selected === label ? 'true' : 'false') + '">' + copy + '</button>'; }
  return '<section class="detail-section decision-panel"><span class="section-label">需要你的决定</span><h2>下一步怎么处理</h2><p>' + esc(intro) + '</p><div class="decision-actions">' + option('APPROVE_FOR_REVIEW','可继续隔离评估',true) + option('WATCH','继续观察',false) + option('NOT_USEFUL','暂不采用',false) + '</div><small class="decision-safety">这里只记录你的处理意见，不会自动安装、运行，也不会接入 受保护项目。</small><p class="decision-message" aria-live="polite"></p></section>';
}

function capabilityCard(item, index) {
  var position = Number.isInteger(index) ? (index % 5) * 25 : artPosition(item.repository);
  return '<article class="capability-card"><a class="card-open" href="#capability/' + encodeURIComponent(item.repository) + '" aria-label="查看 ' + esc(displayName(item.repository)) + ' 详情"></a><div class="card-visual" style="--art-pos:' + position + '%"><span>' + esc(category(item.best_route)) + '</span></div><div class="card-content"><div class="card-top">' + chip(item.human_category || item.activation_state, primaryStatusLabel(item)) + '</div><div class="card-title"><h3>' + esc(displayName(item.repository)) + '</h3><span>' + esc(item.repository || '') + '</span></div><p>' + esc(item.human_summary || item.capability_name) + '</p><div class="card-foot"><span>' + esc(formLabel(item)) + '</span><strong>查看详情 →</strong></div></div></article>';
}

function entityName(item) { return item.name || displayName(item.repository); }
function entityRoute(item) { return item.capability_id ? '#ability/' + encodeURIComponent(item.capability_id) : item.method_id ? '#method/' + encodeURIComponent(item.method_id) : '#capability/' + encodeURIComponent(item.repository); }
function entityStatus(item) { return item.method_id ? 'ADOPTED_METHOD' : item.capability_id ? ((item.personal_states || []).indexOf('USED') >= 0 ? 'USED' : 'USABLE') : item.human_category; }
function entityCard(item, index) {
  if (item.repository) return capabilityCard(item, index);
  var source = item.method_id ? item.source_name : (item.implementations || []).map(function (entry) { return entry.source_name; }).filter(Boolean).join(' · ');
  return '<article class="capability-card"><a class="card-open" href="' + entityRoute(item) + '" aria-label="查看 ' + esc(entityName(item)) + ' 详情"></a><div class="card-visual" style="--art-pos:' + (index % 5) * 25 + '%"><span>' + esc(formLabel(item)) + '</span></div><div class="card-content"><div class="card-top">' + chip(entityStatus(item)) + '</div><div class="card-title"><h3>' + esc(entityName(item)) + '</h3><span>' + esc(source || '') + '</span></div><p>' + esc(item.description || '') + '</p><div class="card-foot"><span>' + esc(formLabel(item)) + '</span><strong>查看详情 →</strong></div></div></article>';
}

function listRow(item, status) { return '<div class="compact-row"><div class="compact-symbol">' + esc(displayName(item.repository).charAt(0).toUpperCase()) + '</div><div class="compact-copy"><strong>' + esc(displayName(item.repository)) + '</strong><span>' + esc(item.repository || '') + '</span><p>' + esc(item.summary || item.human_summary || item.detail || '') + '</p></div>' + (status ? chip(status, humanStatus(status)) : '<time>' + esc(date(item.time || item.updated_at)) + '</time>') + '</div>'; }

function renderHome() {
  var s = state.summary || {counts:{},recent_discoveries:[],my_capabilities_cards:[],method_cards:[],health:{}};
  var c = s.counts || {}; var h = s.health || {}; var issueCount = (h.issues || []).length;
  var discovery = (s.recent_discoveries || [])[0] || {};
  var discoverySummary = chineseFirst(discovery.summary, '这是 Radar 最新捕捉到的高相关项目，已经进入技术丞相的判断范围。打开动态可查看来源与处理记录。');
  var cards = (s.my_capabilities_cards || []).concat(s.method_cards || []).slice(0,5);
  var featured = cards.map(function (x, index) { return '<a class="gallery-card" href="' + entityRoute(x) + '"><span class="gallery-art" style="--art-pos:' + (index * 25) + '%"></span><span class="gallery-copy"><strong>' + esc(entityName(x)) + '</strong><small>' + esc(formLabel(x)) + '</small></span></a>'; }).join('');
  var stale = (s.stale_reviews || []).slice(0,3);
  var stalePanel = stale.length ? '<section class="surface history-panel"><div class="section-head"><div><h2>需要复审 ' + (s.stale_reviews || []).length + '</h2><p>上游出现可能影响旧判断的变化</p></div></div><div class="history-list">' + stale.map(function (x) { return '<div class="history-row"><span class="timeline-dot warn"></span><div><a href="#capability/' + encodeURIComponent(x.source_name) + '"><strong>' + esc(displayName(x.source_name)) + '</strong></a><p>' + esc(x.trigger_reason || '上游变化待复核') + '</p></div></div>'; }).join('') + '</div></section>' : '';
  var healthCopy = issueCount ? issueCount + ' 项运行提醒' : '后台运行正常';
  var metrics = [['可用能力',c.usable],['已采用方法',c.adopted_methods],['等待验证',c.waiting_validation],['观察清单',c.watchlist]].map(function (metric) { return '<div><strong>' + (metric[1] || 0) + '</strong><span>' + metric[0] + '</span></div>'; }).join('');
  app.innerHTML = '<section class="home-stage deskmat-stage"><div class="home-status ' + (issueCount ? 'warn' : 'ok') + '"><span class="pulse-dot"></span><span>' + esc(healthCopy) + '</span><time>' + esc(date(new Date().toISOString())) + '</time></div><section class="home-focus intelligence-veil"><span class="kicker">今日重点情报</span><p class="focus-repo">' + esc(discovery.repository || 'TECHCHANCELLOR') + '</p><h1>' + esc(discovery.repository ? displayName(discovery.repository) : '让值得关注的技术浮出水面') + '</h1><p class="focus-summary">' + esc(discovery.repository ? discoverySummary : 'Radar 下一次完成扫描后，这里只会保留最值得你关注的一项发现。') + '</p><div class="home-metrics">' + metrics + '</div><div class="focus-actions"><a class="primary-button" href="#activity">查看判断 <span>→</span></a><span>已评审项目总数 ' + (c.reviewed_projects || c.total || 0) + '</span></div></section><section class="capability-gallery glass-panel"><div class="gallery-head"><div><span class="section-label">能力与方法</span><h2>现在真正可复用的资产</h2></div><a class="text-button" href="#capabilities" aria-label="浏览能力库">浏览全部 →</a></div><div class="gallery-grid">' + (featured || quietState('还没有可复用能力','通过验证或明确采用后，项目才会出现在这里。')) + '</div></section>' + stalePanel + '</section>';
}

var LIBRARY_SECTIONS = {
  mine: {label:'我的能力', categories:['USED','USABLE'], empty:'还没有可直接使用的能力', detail:'只有通过验证并可调用或已经真实使用的能力会出现在这里。'},
  methods: {label:'方法库', categories:['ADOPTED_METHOD'], empty:'还没有已采用的方法', detail:'只有已经提炼并进入当前工作方式的方法会出现在这里。'},
  pending: {label:'待处理', categories:['WAITING_VALIDATION','VALIDATING','HUMAN_DECISION'], empty:'当前没有待处理项目', detail:'区分已批准等待验证、正在验证和确实需要你决定的项目。'},
  archive: {label:'观察与归档', categories:['WATCHLIST','NOT_ADOPTED','VALIDATION_FAILED','ARCHIVED'], empty:'当前没有观察或归档记录', detail:'参考过但未采用、继续观察或验证未通过的项目会保留在这里。'}
};

function renderCapabilities() {
  var routes = {}; state.capabilities.forEach(function (item) { routes[item.best_route] = true; });
  var tabs = Object.keys(LIBRARY_SECTIONS).map(function (key) { var section = LIBRARY_SECTIONS[key]; var count = libraryItems(key).length; return '<button class="library-tab' + (state.librarySection === key ? ' active' : '') + '" data-library-section="' + key + '"><span>' + section.label + '</span><strong>' + count + '</strong></button>'; }).join('');
  app.innerHTML = viewHeader('能力资产','能力库','区分真正可用的能力、已经采用的方法，以及仍在评估或仅供观察的项目。','<div class="page-count"><strong>' + state.capabilities.length + '</strong><span>已评审项目总数</span></div>') + '<div class="library-tabs" role="tablist" aria-label="能力库分区">' + tabs + '</div><div class="library-toolbar"><label class="search-field"><span>⌕</span><input id="cap-search" placeholder="搜索名称、用途或仓库" aria-label="搜索能力库"></label><select id="cap-route" aria-label="按类别筛选"><option value="">全部类别</option>' + Object.keys(routes).map(function (route) { return '<option value="' + esc(route) + '">' + esc(category(route)) + '</option>'; }).join('') + '</select><span id="filter-count" class="filter-count"></span></div><div id="library-section-copy" class="library-section-copy"></div><div id="cap-list" class="capability-grid"></div>';
  document.querySelector('#cap-search').addEventListener('input', filterCapabilities);
  document.querySelector('#cap-route').addEventListener('change', filterCapabilities);
  document.querySelectorAll('[data-library-section]').forEach(function (button) { button.addEventListener('click', function () { state.librarySection = button.dataset.librarySection; renderCapabilities(); }); });
  filterCapabilities();
}

function libraryItems(key) { if (key === 'mine') return state.summary && state.summary.capability_entities || []; if (key === 'methods') return state.summary && state.summary.method_entities || []; var section = LIBRARY_SECTIONS[key] || LIBRARY_SECTIONS.mine; return state.capabilities.filter(function (item) { return section.categories.indexOf(item.human_category) >= 0; }); }
function filterCapabilities() { var q = document.querySelector('#cap-search').value.toLowerCase(); var route = document.querySelector('#cap-route').value; var section = LIBRARY_SECTIONS[state.librarySection] || LIBRARY_SECTIONS.mine; var list = libraryItems(state.librarySection).filter(function (item) { return (!q || (entityName(item) + ' ' + JSON.stringify(item)).toLowerCase().indexOf(q) >= 0) && (!route || item.best_route === route || item.domain === route); }); document.querySelector('#filter-count').textContent = list.length + ' 项'; document.querySelector('#library-section-copy').innerHTML = '<strong>' + esc(section.label) + '</strong><span>' + esc(section.detail) + '</span>'; document.querySelector('#cap-list').innerHTML = list.length ? list.map(entityCard).join('') : quietState(section.empty,section.detail); }

function sourceInsight(item) {
  var mappings = item.capability_mappings || []; var freshness = item.source_freshness || {};
  var review = item.latest_delta_review || {};
  var linked = mappings.map(function (entry) { var owned = (state.summary && state.summary.capability_entities || []).some(function (x) { return x.capability_id === entry.capability_id; }); return '<li>' + (owned ? '<a href="#ability/' + encodeURIComponent(entry.capability_id) + '">' + esc(entry.name) + '</a>' : esc(entry.name)) + '<span> · ' + esc(entry.implementation_name) + '</span></li>'; }).join('');
  var reviewState = freshness.review_freshness === 'STALE' ? '上游已变化，等待重新判断' : freshness.review_freshness === 'CURRENT' ? '已对当前版本完成复审' : freshness.last_upstream_check ? '已建立监测基线，旧评审版本未核对' : '尚未检查上游';
  return '<section class="surface history-panel"><div class="section-head"><div><h2>来源与版本</h2><p>上游变化不会自动改动本地能力</p></div></div><dl class="clean-list"><div><dt>对应能力</dt><dd><ul>' + (linked || '<li>暂无结构化映射</li>') + '</ul></dd></div><div><dt>当前发布</dt><dd>' + esc(freshness.current_release_tag || '无发布记录') + '</dd></div><div><dt>评审时发布</dt><dd>' + esc(freshness.reviewed_release_tag || '待核对') + '</dd></div><div><dt>最近检查</dt><dd>' + esc(date(freshness.last_upstream_check)) + '</dd></div><div><dt>最近变化</dt><dd>' + esc(date(freshness.last_upstream_change)) + '</dd></div><div><dt>评审状态</dt><dd>' + esc(reviewState) + '</dd></div>' + (review.review_outcome ? '<div><dt>最新复审</dt><dd>' + esc(DELTA_LABELS[review.review_outcome] || review.review_outcome) + '</dd></div>' : '') + '</dl></section>';
}

var READINESS_LABELS = {READY_WITH_EXISTING_ADAPTER:'现有适配器可继续',NEEDS_SAFE_ADAPTER:'需要安全适配器',REQUIRES_OS_SANDBOX:'需要系统级隔离',HUMAN_GATE:'需要人工决定',NO_MEANINGFUL_DELTA:'暂无明确增益',WAITING_UPSTREAM_CHANGE:'等待上游变化',NOT_WORTH_ACTIVATING:'当前不值得激活'};
function operationInsight(item) {
  var readiness = item.activation_readiness || {}; var usage = item.capability_usage || {};
  if (!readiness.category && !usage.consumer) return '';
  var health = usage.health || {}; var result = usage.last_material_summary || {};
  var useText = usage.last_material_use_at ? '新增 ' + (result.new_count || 0) + ' 个候选，初步语义筛选 ' + (result.semantic_reviewed_count || 0) + ' 个；不代表最终采用' : '尚无有效生产使用';
  return '<section class="surface history-panel"><div class="section-head"><div><h2>调用与阻断</h2></div></div><dl class="clean-list">' +
    '<div><dt>激活准备度</dt><dd>' + esc(READINESS_LABELS[readiness.category] || readiness.category || (item.activation_state === 'USED' ? '已实际使用' : '尚未审计')) + '</dd></div>' +
    (readiness.blocker ? '<div><dt>当前阻断</dt><dd>' + esc(readiness.blocker) + '</dd></div>' : '') +
    '<div><dt>生产使用方</dt><dd>' + esc(usage.consumer === 'RADAR_DISCOVERY' ? 'Radar 发现流程' : usage.consumer || '尚无') + '</dd></div>' +
    '<div><dt>最近真实使用</dt><dd>' + esc(usage.last_material_use_at ? date(usage.last_material_use_at) : '尚无') + '</dd></div>' +
    '<div><dt>使用结果</dt><dd>' + esc(useText) + '</dd></div>' +
    '<div><dt>调用健康</dt><dd>' + esc(health.consecutive_failures ? '连续失败 ' + health.consecutive_failures + ' 次' : usage.consumer ? '正常' : '尚无调用') + '</dd></div></dl></section>';
}

function candidatePipelineInsight(item) {
  var pipeline = item.candidate_pipeline;
  if (!pipeline) return '';
  var sources = (pipeline.source_provenance || []).map(function (source) {
    return source.source_type === 'CAPABILITY' ? 'Skill 生态发现 · ' + (source.implementation_id || source.source_id) : 'GitHub Radar';
  }).filter(function (value, index, values) { return values.indexOf(value) === index; }).join('；');
  return '<section class="surface history-panel"><div class="section-head"><h2>候选处理进度</h2></div><dl class="clean-list">' +
    '<div><dt>来源</dt><dd>' + esc(sources || '历史来源待核对') + '</dd></div>' +
    '<div><dt>当前阶段</dt><dd>' + esc(pipeline.stage_label) + '</dd></div>' +
    '<div><dt>初步语义筛选</dt><dd>已完成，只作为证据与排序参考</dd></div>' +
    '<div><dt>最终 Chancellor 决定</dt><dd>' + esc(pipeline.final_decision ? humanStatus(pipeline.final_decision) : '尚未作出') + '</dd></div></dl></section>';
}

function renderEntityDetail(item) {
  var isMethod = !!item.method_id; var title = entityName(item); var entries = item.implementations || [];
  var sourceLinks = isMethod ? (item.source_name ? '<li><a href="#capability/' + encodeURIComponent(item.source_name) + '">' + esc(displayName(item.source_name)) + '</a></li>' : '') : entries.map(function (entry) { return '<li><a href="#capability/' + encodeURIComponent(entry.source_name) + '">' + esc(entry.name) + '</a><span> · ' + esc(entry.source_name) + '</span></li>'; }).join('');
  state.detailId = item.capability_id || item.method_id;
  document.querySelector('#current-view-label').textContent = isMethod ? '方法详情' : '能力详情';
  app.innerHTML = '<div class="breadcrumb"><a href="#capabilities">能力库</a><span>›</span><strong>' + esc(title) + '</strong></div><section class="detail-hero"><div class="detail-identity"><span class="detail-monogram">' + esc(title.charAt(0)) + '</span><div><span class="kicker">' + esc(isMethod ? '已采用方法' : '我的能力') + '</span><h1>' + esc(title) + '</h1><p>' + esc(item.domain || item.source_name || '') + '</p></div></div><div class="detail-status">' + chip(entityStatus(item)) + '</div></section><div class="detail-layout"><div class="detail-main"><section class="detail-section"><span class="section-label">这是什么</span><h2>' + esc(title) + '</h2><p class="detail-copy">' + esc(item.description || '') + '</p></section><section class="detail-section"><span class="section-label">' + esc(isMethod ? '来源项目' : '可用实现与来源') + '</span><ul class="clean-list">' + (sourceLinks || '<li>暂无来源记录</li>') + '</ul></section></div><aside class="detail-aside"><section class="aside-card"><span class="section-label">当前状态</span><h3>' + esc(humanStatus(entityStatus(item))) + '</h3><dl><div><dt>条目类型</dt><dd>' + esc(formLabel(item)) + '</dd></div>' + (isMethod ? '<div><dt>采用依据</dt><dd>已记录方法机制和实际使用证据</dd></div>' : '<div><dt>个人状态</dt><dd>' + esc((item.personal_states || []).map(humanStatus).join('、')) + '</dd></div>') + '</dl></section></aside></div>';
  if (!isMethod && entries.length) {
    var source = state.capabilities.find(function (card) { return card.repository === entries[0].source_name; });
    if (source) app.insertAdjacentHTML('beforeend', operationInsight(source));
  }
  restartViewEntrance();
}

function renderCapabilityDetail(item) {
  var ask = (item.how_to_ask_codex || [])[0] || '直接描述你的目标，Codex 会判断是否适合使用这项能力。';
  var events = state.activity.filter(function (event) { return event.repository === item.repository; }).slice(0,6);
  var eventHtml = events.map(function (event) { return '<div class="history-row"><span class="timeline-dot ' + statusClass(event.machine_status) + '"></span><div><strong>' + esc(event.title) + '</strong><p>' + esc(event.detail) + '</p><time>' + esc(date(event.time)) + '</time></div></div>'; }).join('');
  state.detailId = item.repository;
  document.querySelector('#current-view-label').textContent = '能力详情';
  app.innerHTML = '<div class="breadcrumb"><a href="#capabilities">能力库</a><span>›</span><strong>' + esc(displayName(item.repository)) + '</strong></div><section class="detail-hero"><div class="detail-identity"><span class="detail-monogram">' + esc(displayName(item.repository).charAt(0).toUpperCase()) + '</span><div><span class="kicker">' + esc(category(item.best_route)) + '</span><h1>' + esc(displayName(item.repository)) + '</h1><p>' + esc(item.repository) + '</p></div></div><div class="detail-status">' + chip(item.human_category || item.activation_state, primaryStatusLabel(item)) + '<span>更新于 ' + esc(date(item.updated_at)) + '</span></div></section><div class="detail-layout"><div class="detail-main"><section class="detail-section"><span class="section-label">这是什么</span><h2>' + esc(item.human_summary || item.capability_name) + '</h2><p class="detail-copy">' + esc(item.problem_solved || '') + '</p></section><section class="detail-section"><span class="section-label">为什么在这里</span><p class="detail-copy">' + esc(collectionReason(item)) + '</p><div class="next-step"><strong>下一步</strong><span>' + esc(item.next_step || '等待新的证据。') + '</span></div></section>' + decisionPanel(item) + '<section class="detail-section"><span class="section-label">什么时候该用</span>' + bulletList(item.when_to_use, '当前没有额外的适用场景说明。') + '</section><section class="codex-callout"><div><span class="section-label">' + (item.human_category === 'USED' || item.human_category === 'USABLE' || item.human_category === 'ADOPTED_METHOD' ? '让 Codex 使用' : '与 Codex 讨论') + '</span><p>' + esc(ask) + '</p></div><button class="copy-button" data-copy="' + esc(ask) + '">复制调用语句</button></section><section class="detail-section"><span class="section-label">限制与边界</span>' + bulletList(item.main_limitations, '当前没有额外限制说明。') + '</section></div><aside class="detail-aside"><section class="aside-card"><span class="section-label">当前状态</span><h3>' + esc(primaryStatusLabel(item)) + '</h3><dl><div><dt>条目类型</dt><dd>' + esc(formLabel(item)) + '</dd></div><div><dt>已经安装</dt><dd>' + (item.installed ? '是' : '否') + '</dd></div><div><dt>当前可运行</dt><dd>' + (item.runnable ? '是' : '否') + '</dd></div><div><dt>证据成熟度</dt><dd>' + esc(humanStatus(item.evidence_maturity)) + '</dd></div></dl></section><section class="aside-card"><span class="section-label">来源</span><a class="source-link" href="' + esc(item.url || '#') + '" target="_blank" rel="noreferrer"><strong>GitHub 仓库</strong><span>' + esc(item.repository) + '</span><b>↗</b></a></section></aside></div><section class="surface history-panel"><div class="section-head"><div><h2>过去发生了什么</h2><p>与这项能力相关的本地判断记录</p></div></div><div class="history-list">' + (eventHtml || quietState('暂无单独动态','当前状态来自能力库记录；后续判断会按时间排列在这里。')) + '</div></section><details class="technical-details"><summary>查看技术字段</summary><dl><div><dt>human_category</dt><dd>' + esc(item.human_category) + '</dd></div><div><dt>activation_state</dt><dd>' + esc(item.activation_state) + '</dd></div><div><dt>activation_tier</dt><dd>' + esc(item.activation_tier) + '</dd></div><div><dt>semantic_action</dt><dd>' + esc(item.semantic_action) + '</dd></div></dl></details>';
  app.insertAdjacentHTML('beforeend', sourceInsight(item));
  app.insertAdjacentHTML('beforeend', candidatePipelineInsight(item) + operationInsight(item));
  restartViewEntrance();
}

function renderActivity() {
  var rows = state.activity.map(function (item) { return '<article class="activity-row"><div class="activity-track"><span class="timeline-dot ' + statusClass(item.machine_status) + '"></span></div><div class="activity-body"><div class="activity-title"><strong>' + esc(item.title) + '</strong>' + (item.repository ? '<a href="#capability/' + encodeURIComponent(item.repository) + '">' + esc(displayName(item.repository)) + '</a>' : '') + '</div><p>' + esc(item.detail) + '</p><details><summary>内部记录</summary><span class="machine">' + esc(item.machine_status || '') + '</span></details></div><div class="activity-meta">' + chip(item.machine_status,item.status || humanStatus(item.machine_status)) + '<time>' + esc(date(item.time)) + '</time></div></article>'; }).join('');
  app.innerHTML = viewHeader('运行记录','最近动态','Radar、Chancellor 与能力生命周期的统一时间线。','') + '<section class="surface activity-feed">' + (rows || quietState('当前没有动态','下一次扫描或判断完成后，记录会出现在这里。')) + '</section>';
}

function renderSystem() {
  var h = state.summary && state.summary.health || {}; var issues = h.issues || []; var scan = h.latest_scan_run || {}; var stage = h.latest_stage_b_run || {};
  var upstream = h.latest_upstream_run || {};
  var tasks = (h.tasks || []).map(function (task) { return '<div class="runtime-row"><span class="runtime-icon">⌁</span><div><strong>计划任务</strong><p>' + esc(task.name) + '</p></div><span class="runtime-result">' + esc(taskResultLabel(task.last_result, task.status)) + '</span></div>'; }).join('');
  var issueRows = issues.map(function (issue) { return '<div class="issue-row"><span>!</span><div><strong>' + esc(issueLabel(issue)) + '</strong><p>' + esc(issueDetail(issue)) + '</p></div><details><summary>技术字段</summary><span class="machine">' + esc(issue) + '</span></details></div>'; }).join('');
  app.innerHTML = viewHeader('本地运行','系统状态','查看后台是否按预期工作，以及是否有需要关注的事项。',chip(state.summary && state.summary.status || '正常')) + '<div class="system-grid"><section class="surface runtime-panel"><div class="section-head"><div><h2>后台组件</h2><p>最近一次运行情况</p></div></div><div class="runtime-row"><span class="runtime-icon">R</span><div><strong>Radar · 项目发现</strong><p>最近运行 ' + esc(date(scan.started_at)) + '</p></div>' + chip(scan.status || '暂无运行') + '</div><div class="runtime-row"><span class="runtime-icon">C</span><div><strong>Chancellor · 项目判断</strong><p>最近处理 ' + esc(date(stage.started_at)) + '</p></div>' + chip(stage.status || '暂无运行') + '</div>' + tasks + '</section><aside class="system-summary"><div><span>后台待重试</span><strong>' + (h.active_pending || 0) + '</strong><small>Chancellor 队列</small></div><div><span>判断记录</span><strong>' + (h.decision_history_count || 0) + '</strong><small>已经留存</small></div><div><span>涉及项目</span><strong>' + (h.unique_decision_repositories || 0) + '</strong><small>不同仓库</small></div></aside></div><section class="surface issue-panel"><div class="section-head"><div><h2>需要注意</h2><p>系统允许没有告警；安静本身就是正常状态</p></div></div>' + (issueRows || quietState('没有需要处理的提醒','Radar、Chancellor 和计划任务都处于预期状态。')) + '</section>';
  var monitor = '<div class="runtime-row"><span class="runtime-icon">U</span><div><strong>上游变化监测</strong><p>最近检查 ' + esc(date(upstream.started_at)) + ' · 待复核 ' + (state.summary && state.summary.stale_reviews || []).length + ' 项</p></div>' + chip(upstream.status || '暂无运行') + '</div>';
  document.querySelector('.runtime-panel').insertAdjacentHTML('beforeend', monitor);
  var sandbox = state.summary && state.summary.secure_execution || {};
  document.querySelector('.runtime-panel').insertAdjacentHTML('beforeend', '<div class="runtime-row"><span class="runtime-icon">S</span><div><strong>第三方代码隔离执行</strong><p>' + (sandbox.status === 'VERIFIED_RECEIPT' ? 'Docker / WSL2 · 已留存隔离验证；执行前再次检查运行状态' : '可选组件 · 未通过验证时禁止执行第三方代码') + '</p></div>' + chip(sandbox.label || '未配置') + '</div>');
}

function renderDocuments() {
  var rows = state.documents.map(function (item) { return '<a class="document-row" href="#document/' + encodeURIComponent(item.path) + '"><span class="document-glyph">§</span><span class="document-copy"><strong>' + esc(item.title) + '</strong><small>' + esc(item.path) + '</small></span>' + tag(item.category || '项目文档') + '<time>' + esc(date(item.modified)) + '</time><b>→</b></a>'; }).join('');
  app.innerHTML = viewHeader('项目资料','文档','在本地阅读设计记录、运行报告与项目说明。','<div class="page-count"><strong>' + state.documents.length + '</strong><span>份文档</span></div>') + '<section class="surface document-library">' + (rows || quietState('还没有可阅读文档','项目文档进入允许目录后会自动出现在这里。')) + '</section>';
}

function openDocument(path) { getJSON('/api/document?path=' + encodeURIComponent(path)).then(function (doc) { document.querySelector('#current-view-label').textContent = '文档阅读'; app.innerHTML = '<div class="reader-bar"><a class="text-button" href="#documents">← 返回文档</a><span>' + esc(path) + '</span></div><article class="markdown-reader"><header><span class="kicker">本地文档</span><h1>' + esc(path.split('/').pop()) + '</h1><p>' + esc(path) + '</p></header><div class="markdown">' + doc.html + '</div></article>'; restartViewEntrance(); }); }
function submitFeedback(repository, label, button) {
  var panel = button.closest('.decision-panel'); var message = panel.querySelector('.decision-message');
  panel.querySelectorAll('[data-feedback-label]').forEach(function (item) { item.disabled = true; });
  message.className = 'decision-message'; message.textContent = '正在记录你的选择…';
  postJSON('/api/feedback', {repository:repository,label:label,note:'Recorded from the local TechChancellor Control Center.'}).then(function () {
    return Promise.all([getJSON('/api/summary'), getJSON('/api/capabilities')]);
  }).then(function (values) {
    state.summary = values[0]; state.capabilities = values[1].items || []; updateHealth();
    var updated = state.capabilities.find(function (item) { return item.repository === repository; });
    if (updated) renderCapabilityDetail(updated);
  }).catch(function (error) {
    panel.querySelectorAll('[data-feedback-label]').forEach(function (item) { item.disabled = false; });
    message.className = 'decision-message error'; message.textContent = '记录失败：' + error.message;
  });
}

function setView(view) { state.view = view; state.detailId = null; document.querySelectorAll('.nav-item').forEach(function (item) { item.classList.toggle('active', item.dataset.view === view); }); document.querySelector('#current-view-label').textContent = VIEW_LABELS[view] || '总览'; render(); window.scrollTo(0,0); }
function routeFromHash() {
  var route = window.location.hash.replace(/^#/, '');
  if (route.indexOf('ability/') === 0 || route.indexOf('method/') === 0) {
    var isMethod = route.indexOf('method/') === 0;
    var id = decodeURIComponent(route.slice(isMethod ? 'method/'.length : 'ability/'.length));
    var items = state.summary && state.summary[isMethod ? 'method_entities' : 'capability_entities'] || [];
    var entity = items.find(function (candidate) { return candidate[isMethod ? 'method_id' : 'capability_id'] === id; });
    if (entity) { state.view = 'capabilities'; document.body.dataset.currentView = state.view; document.querySelectorAll('.nav-item').forEach(function (nav) { nav.classList.toggle('active', nav.dataset.view === state.view); }); renderEntityDetail(entity); window.scrollTo(0,0); return true; }
  }
  if (route.indexOf('capability/') === 0) {
    var repository = decodeURIComponent(route.slice('capability/'.length));
    var item = state.capabilities.find(function (candidate) { return candidate.repository === repository; });
    if (item) { state.view = 'capabilities'; document.body.dataset.currentView = state.view; document.querySelectorAll('.nav-item').forEach(function (nav) { nav.classList.toggle('active', nav.dataset.view === state.view); }); renderCapabilityDetail(item); window.scrollTo(0,0); return true; }
  }
  if (route.indexOf('document/') === 0) {
    state.view = 'documents'; document.body.dataset.currentView = state.view; document.querySelectorAll('.nav-item').forEach(function (nav) { nav.classList.toggle('active', nav.dataset.view === state.view); }); openDocument(decodeURIComponent(route.slice('document/'.length))); window.scrollTo(0,0); return true;
  }
  if (VIEW_LABELS[route]) { setView(route); return true; }
  return false;
}
function restartViewEntrance() { app.classList.remove('view-enter'); void app.offsetWidth; app.classList.add('view-enter'); }
function render() { document.body.dataset.currentView = state.view; if (state.view === 'home') renderHome(); if (state.view === 'capabilities') renderCapabilities(); if (state.view === 'activity') renderActivity(); if (state.view === 'system') renderSystem(); if (state.view === 'documents') renderDocuments(); restartViewEntrance(); }
function applyTheme(value) { if (value === 'system') document.documentElement.removeAttribute('data-theme'); else document.documentElement.setAttribute('data-theme', value); localStorage.setItem('techchancellor-theme', value); }
function initTheme() { var select = document.querySelector('#theme-select'); var saved = localStorage.getItem('techchancellor-theme') || 'system'; select.value = saved; applyTheme(saved); select.addEventListener('change', function () { applyTheme(select.value); }); }
function updateHealth() { var health = state.summary && state.summary.health || {}; var count = (health.issues || []).length; var node = document.querySelector('#global-health'); node.className = 'rail-health ' + (count ? 'has-warning' : 'is-ok'); node.querySelector('span:last-child').textContent = count ? count + ' 项提醒' : '系统运行正常'; }
function load() { app.innerHTML = '<div class="loading-state"><span></span><strong>正在读取本地情报库</strong></div>'; Promise.all([getJSON('/api/summary'),getJSON('/api/capabilities'),getJSON('/api/activity'),getJSON('/api/documents')]).then(function (values) { state.summary=values[0]; state.capabilities=values[1].items||[]; state.activity=values[2].items||[]; state.documents=values[3].items||[]; document.querySelector('#last-refresh').textContent='更新于 '+new Date().toLocaleTimeString('zh-CN',{hour12:false}); updateHealth(); if (!routeFromHash()) render(); }).catch(function (error) { app.innerHTML='<div class="error-state"><strong>控制中心暂时无法读取数据</strong><p>'+esc(error.message)+'。请确认本地服务仍在运行。</p></div>'; }); }

app.addEventListener('click', function (event) {
  var feedback = event.target.closest('[data-feedback-label]'); if (feedback) { submitFeedback(feedback.dataset.feedbackRepository, feedback.dataset.feedbackLabel, feedback); return; }
  var copy = event.target.closest('[data-copy]'); if (copy && navigator.clipboard) navigator.clipboard.writeText(copy.dataset.copy).then(function () { var old = copy.textContent; copy.textContent='已复制'; setTimeout(function () { copy.textContent=old; },1200); });
});
window.addEventListener('hashchange', routeFromHash);
document.querySelector('[data-action=refresh]').addEventListener('click',load);
initTheme(); load();
