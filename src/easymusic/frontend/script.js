(function () {
  'use strict';

  /* ============================================
     Constants & Helpers
     ============================================ */

  var CLIENT_ID_KEY = 'easymusic_client_id';
  var BACKEND_URL_KEY = 'easymusic_backend_url';
  var LLM_PROVIDER_STORAGE = 'easymusic_llm_provider';
  var LLM_API_KEY_STORAGE = 'easymusic_llm_api_key';
  var LLM_BASE_URL_STORAGE = 'easymusic_llm_base_url';
  var LLM_MODEL_STORAGE = 'easymusic_llm_model';
  var LANG_KEY = 'easymusic_lang';
  var POLL_INTERVAL = 2000;

  function el(id) { return document.getElementById(id); }

  function getClientId() {
    var cid = localStorage.getItem(CLIENT_ID_KEY);
    if (!cid) {
      cid = 'em_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8);
      localStorage.setItem(CLIENT_ID_KEY, cid);
    }
    return cid;
  }

  var clientId = getClientId();

  function getBackendUrl() {
    return localStorage.getItem(BACKEND_URL_KEY) || window.location.origin;
  }

  function setBackendUrl(url) {
    if (url) { localStorage.setItem(BACKEND_URL_KEY, url); }
    else { localStorage.removeItem(BACKEND_URL_KEY); }
  }

  function getLlmConfig() {
    return {
      provider: localStorage.getItem(LLM_PROVIDER_STORAGE) || 'gpt',
      apiKey: localStorage.getItem(LLM_API_KEY_STORAGE) || '',
      baseUrl: localStorage.getItem(LLM_BASE_URL_STORAGE) || '',
      model: localStorage.getItem(LLM_MODEL_STORAGE) || 'gpt-4o'
    };
  }

  function setLlmConfig(cfg) {
    localStorage.setItem(LLM_PROVIDER_STORAGE, cfg.provider || 'gpt');
    localStorage.setItem(LLM_API_KEY_STORAGE, cfg.apiKey || '');
    localStorage.setItem(LLM_BASE_URL_STORAGE, cfg.baseUrl || '');
    localStorage.setItem(LLM_MODEL_STORAGE, cfg.model || 'gpt-4o');
  }

  function clearAllStorage() {
    localStorage.removeItem(LLM_PROVIDER_STORAGE);
    localStorage.removeItem(LLM_API_KEY_STORAGE);
    localStorage.removeItem(LLM_BASE_URL_STORAGE);
    localStorage.removeItem(LLM_MODEL_STORAGE);
    localStorage.removeItem(BACKEND_URL_KEY);
    localStorage.removeItem(CLIENT_ID_KEY);
    clientId = getClientId();
  }

  /* ============================================
     i18n
     ============================================ */

  var currentLang = localStorage.getItem(LANG_KEY) || 'zh';

  var i18n = {
    zh: {
      settings_title: '设置',
      settings_backend: '后端连接地址',
      settings_backend_desc: '配置后端 API 服务器地址',
      settings_llm: 'LLM API 接口配置',
      settings_llm_hint: '目前支持 GPT、DeepSeek 和 LM Studio',
      settings_llm_hint_gpt: '使用 OpenAI API，请填写 API Key',
      settings_llm_hint_deepseek: '使用 DeepSeek API，请填写 API Key',
      settings_llm_hint_lmstudio: '使用本地 LM Studio 服务。Base URL 需包含 /v1（如 http://127.0.0.1:1234/v1）。API Key 默认可为空（LM Studio 默认关闭认证），若开启了认证请填写 Token。',
      settings_llm_provider: '服务商选择',
      settings_llm_api_key: 'API Key',
      settings_llm_base_url: 'Base URL',
      settings_llm_model: '模型名称',
      btn_save: '保存设置',
      btn_clear: '一键清除',
      btn_test: '测试连接',
      hero_title: 'EasyMusic：你的灵感助理。',
      hero_subtitle: '用自然语言描述你的音乐创意。EasyMusic 将你的 Prompt 转化为完整的 MIDI 作品 — 鼓组、贝斯、和弦与主旋律。',
      btn_advanced: '高级',
      btn_create: '生成',
      placeholder_prompt: '描述你想要的音乐…',
      label_note_mode: '音符生成模式',
      label_oob_mode: '越界音高处理',
      metric_server_status: '服务器状态',
      metric_version: '版本',
      metric_work_status: '状态',
      metric_total_tasks: '总项目数',
      heading_tasks: '我的任务',
      subtitle_tasks: '实时追踪你的音乐生成进度',
      empty_tasks: '暂无任务，在上方输入 Prompt 并点击生成按钮开始创作音乐。',
      status_connecting: '连接中…',
      status_online: '在线',
      status_offline: '离线',
      status_busy: '工作中',
      status_idle: '空闲',
      status_working: '工作',
      test_success: '测试连接成功！单音符 MIDI 文件已保存。',
      test_fail: '测试连接失败，请检查 API 配置。',
      save_success: '设置已保存。',
      clear_success: '所有本地 API 密钥已清除。',
      backend_auto_configured: '后端已自动配置',
      toast_settings: '设置已更新',
      toast_backend_auto: '后端地址已自动配置'
    },
    en: {
      settings_title: 'Settings',
      settings_backend: 'Backend Connection URL',
      settings_backend_desc: 'Configure the backend API server address',
      settings_llm: 'LLM API Configuration',
      settings_llm_hint: 'Currently supports GPT, DeepSeek, and LM Studio',
      settings_llm_hint_gpt: 'Using OpenAI API, please enter API Key',
      settings_llm_hint_deepseek: 'Using DeepSeek API, please enter API Key',
      settings_llm_hint_lmstudio: 'Using local LM Studio service. Base URL must include /v1 (e.g. http://127.0.0.1:1234/v1). API Key is optional (LM Studio disables auth by default), provide a Token if auth is enabled.',
      settings_llm_provider: 'Provider',
      settings_llm_api_key: 'API Key',
      settings_llm_base_url: 'Base URL',
      settings_llm_model: 'Model Name',
      btn_save: 'Save Settings',
      btn_clear: 'Clear All',
      btn_test: 'Test Connection',
      hero_title: 'EasyMusic: Your Inspiration Assistant.',
      hero_subtitle: 'Describe your musical idea in plain language. EasyMusic transforms your prompt into a complete MIDI composition — drums, bass, chords, and melody.',
      btn_advanced: 'Advanced',
      btn_create: 'Create',
      placeholder_prompt: 'Describe your music…',
      label_note_mode: 'Note Generation Mode',
      label_oob_mode: 'Out-of-Bounds Handling',
      metric_server_status: 'Server Status',
      metric_version: 'Version',
      metric_work_status: 'Status',
      metric_total_tasks: 'Total Projects',
      heading_tasks: 'My Tasks',
      subtitle_tasks: 'Track the progress of your music generations in real time',
      empty_tasks: 'No tasks yet. Enter a prompt above and hit Create to start generating music.',
      status_connecting: 'Connecting…',
      status_online: 'Online',
      status_offline: 'Offline',
      status_busy: 'Working',
      status_idle: 'Idle',
      status_working: 'Working',
      test_success: 'Connection test passed! Single-note MIDI file saved.',
      test_fail: 'Connection test failed. Please check your API configuration.',
      save_success: 'Settings saved.',
      clear_success: 'All local API keys have been cleared.',
      backend_auto_configured: 'Backend auto-configured',
      toast_settings: 'Settings updated',
      toast_backend_auto: 'Backend URL auto-configured'
    }
  };

  function t(key) {
    return (i18n[currentLang] && i18n[currentLang][key]) || (i18n.en && i18n.en[key]) || key;
  }

  function applyLanguage() {
    var els = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < els.length; i++) {
      var k = els[i].getAttribute('data-i18n');
      if (k) { els[i].textContent = t(k); }
    }
    var placeholderEls = document.querySelectorAll('[data-i18n-placeholder]');
    for (var j = 0; j < placeholderEls.length; j++) {
      var pk = placeholderEls[j].getAttribute('data-i18n-placeholder');
      if (pk) { placeholderEls[j].placeholder = t(pk); }
    }
    updateLangButtons();
  }

  function updateLangButtons() {
    var btnZh = el('btnLangZh');
    var btnEn = el('btnLangEn');
    if (btnZh) {
      if (currentLang === 'zh') { btnZh.classList.add('lang-btn--active'); }
      else { btnZh.classList.remove('lang-btn--active'); }
    }
    if (btnEn) {
      if (currentLang === 'en') { btnEn.classList.add('lang-btn--active'); }
      else { btnEn.classList.remove('lang-btn--active'); }
    }
  }

  /* ============================================
     State
     ============================================ */

  var state = {
    runtime: null,
    tasks: [],
    polling: false
  };

  function isBackendOnline() {
    return state.runtime !== null;
  }

  /* ============================================
     API
     ============================================ */

  function api(path, options) {
    options = options || {};
    var base = getBackendUrl().replace(/\/+$/, '');
    var url = base + '/api' + path;
    var headers = {
      'Content-Type': 'application/json',
      'X-EasyMusic-Client-Id': clientId
    };
    if (options.headers) {
      Object.keys(options.headers).forEach(function (k) {
        headers[k] = options.headers[k];
      });
    }
    return fetch(url, {
      method: options.method || 'GET',
      headers: headers,
      body: options.body
    }).then(function (res) {
      if (!res.ok) {
        return res.json().catch(function () { return {}; }).then(function (body) {
          var msg = body.detail || body.message || 'HTTP ' + res.status;
          throw new Error(msg);
        });
      }
      return res.json();
    });
  }

  /* ============================================
     Polling
     ============================================ */

  function poll() {
    if (state.polling) return;
    state.polling = true;
    Promise.allSettled([
      api('/runtime'),
      api('/tasks')
    ]).then(function (results) {
      if (results[0].status === 'fulfilled') {
        state.runtime = results[0].value;
      } else {
        state.runtime = null;
      }
      if (results[1].status === 'fulfilled') {
        var data = results[1].value;
        state.tasks = Array.isArray(data) ? data : (data.tasks || []);
      }
      updateHeaderStatus(state.runtime);
      updateRuntimeMetrics(state.runtime);
      renderTasks();
    }).catch(function () {
      state.runtime = null;
      updateHeaderStatus(null);
      updateRuntimeMetrics(null);
    }).finally(function () {
      state.polling = false;
    });
  }

  /* ============================================
     Header Status
     ============================================ */

  function updateHeaderStatus(r) {
    var dot = document.querySelector('#headerStatus .status-dot');
    var txt = document.querySelector('#headerStatus .status-text');
    if (!dot || !txt) return;

    if (!r) {
      dot.className = 'status-dot offline';
      txt.textContent = t('status_offline');
      return;
    }
    if (r.current_task_id) {
      dot.className = 'status-dot busy';
      txt.textContent = t('status_busy');
    } else {
      dot.className = 'status-dot online';
      txt.textContent = t('status_online');
    }
  }

  /* ============================================
     Runtime Metrics
     ============================================ */

  function updateRuntimeMetrics(r) {
    var elStatus = el('metricStatus');
    var elVersion = el('metricVersion');
    var elWork = el('metricWorkStatus');
    var elTotal = el('metricTotalTasks');

    if (!r) {
      if (elStatus) elStatus.textContent = t('status_offline');
      if (elVersion) elVersion.textContent = '—';
      if (elWork) elWork.textContent = '—';
      if (elTotal) elTotal.textContent = '—';
      return;
    }

    if (elStatus) elStatus.textContent = t('status_online');
    if (elVersion && r.version) elVersion.textContent = r.version;
    if (elWork) {
      if (r.server_status === '工作' || r.server_status === 'Working') {
        elWork.textContent = currentLang === 'zh' ? '工作' : 'Working';
        elWork.style.color = 'var(--color-primary)';
      } else {
        elWork.textContent = currentLang === 'zh' ? '空闲' : 'Idle';
        elWork.style.color = '#4ade80';
      }
    }
    if (elTotal) elTotal.textContent = r.total_tasks != null ? String(r.total_tasks) : '0';
  }

  /* ============================================
     Hero Text Rotation
     ============================================ */

  var heroTexts = [
    'dark cyberpunk battle BGM at 140 BPM',
    'a soothing lofi beat with rain sounds and soft piano',
    'epic orchestral soundtrack with swelling strings',
    'funky 80s synthwave with a driving bassline',
    'jazz trio — piano, upright bass, brushed drums',
    'dreamy ambient pad with shimmering arpeggios',
    'heavy metal riff in drop C with double bass drums',
    'baroque chamber music with harpsichord and strings'
  ];

  var heroIndex = 0;

  function initHeroRotation() {
    var rotEl = el('heroRotatingText');
    if (!rotEl) return;
    if (heroTexts.length === 0) return;

    rotEl.textContent = heroTexts[0];

    setInterval(function () {
      rotEl.style.opacity = '0';
      rotEl.style.transition = 'opacity 0.3s ease';
      setTimeout(function () {
        heroIndex = (heroIndex + 1) % heroTexts.length;
        rotEl.textContent = heroTexts[heroIndex];
        rotEl.style.opacity = '1';
      }, 300);
    }, 3000);
  }

  /* ============================================
     Advanced Panel Toggle
     ============================================ */

  function initAdvancedToggle() {
    var btn = el('btnToggleAdvanced');
    var panel = el('advancedPanel');
    if (!btn || !panel) return;

    btn.addEventListener('click', function () {
      if (panel.style.display === 'none') {
        panel.style.display = 'block';
        btn.classList.add('active');
      } else {
        panel.style.display = 'none';
        btn.classList.remove('active');
      }
    });
  }

  /* ============================================
     Clear Prompt
     ============================================ */

  function initClearPrompt() {
    var btn = el('btnClearPrompt');
    var input = el('promptInput');
    if (!btn || !input) return;
    btn.addEventListener('click', function () {
      input.value = '';
      input.focus();
    });
  }

  /* ============================================
     Keyboard Support
     ============================================ */

  function initKeyboard() {
    var input = el('promptInput');
    if (!input) return;
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        var createBtn = el('btnCreate');
        if (createBtn) createBtn.click();
      }
    });
  }

  /* ============================================
     Footer Year
     ============================================ */

  function initFooterYear() {
    var el_yr = el('currentYear');
    if (el_yr) el_yr.textContent = String(new Date().getFullYear());
  }

  /* ============================================
     Toast
     ============================================ */

  function showToast(msg, type) {
    type = type || 'info';
    var container = el('toastContainer');
    if (!container) return;
    var toast = document.createElement('div');
    toast.className = 'toast toast--' + type;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 4000);
  }

  /* ============================================
     Task Rendering
     ============================================ */

  function statusLabel(s) {
    if (s === 'pending') return 'Pending';
    if (s === 'running') return 'Running';
    if (s === 'succeeded') return 'Succeeded';
    if (s === 'failed') return 'Failed';
    if (s === 'retrying') return 'Retrying';
    return s || 'Unknown';
  }

  function stageLabel(s) {
    if (!s) return '';
    var labels = {
      zh: {
        intent: '意图解析',
        song_plan: '歌曲规划',
        arrangement: '编配规划',
        track_events: '音符生成',
        midi_ir: 'MIDI 组装',
        validation: '数据校验',
        midi_render: 'MIDI 渲染',
        wav_render: 'WAV 渲染',
        mp3_render: 'MP3 转码'
      },
      en: {
        intent: 'Intent Parsing',
        song_plan: 'Song Planning',
        arrangement: 'Arrangement',
        track_events: 'Generating Notes',
        midi_ir: 'MIDI Assembly',
        validation: 'Validation',
        midi_render: 'MIDI Rendering',
        wav_render: 'WAV Rendering',
        mp3_render: 'MP3 Encoding'
      }
    };
    var dict = labels[currentLang] || labels.en;
    return dict[s] || s.replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  function renderTasks() {
    var container = el('taskList');
    if (!container) return;

    if (!state.tasks || state.tasks.length === 0) {
      container.innerHTML =
        '<div class="empty-state">' +
          '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>' +
          '<p class="empty-text">' + t('empty_tasks') + '</p>' +
        '</div>';
      return;
    }

    var sorted = state.tasks.slice().sort(function (a, b) {
      return (b.created_at || '').localeCompare(a.created_at || '');
    });

    var html = '<div class="task-grid">';

    sorted.forEach(function (task) {
      html += '<div class="task-card">';
      html += '<div class="task-card-header">';
      html += '<span class="task-card-id">' + (task.task_id ? task.task_id.slice(0, 8) : '—') + '</span>';
      html += '<span class="badge badge--' + (task.status || 'pending') + '">' + statusLabel(task.status) + '</span>';
      html += '</div>';

      if (task.prompt) {
        html += '<p class="task-prompt">' + escapeHtml(String(task.prompt)) + '</p>';
      }

      if (task.status === 'running') {
        var stageIdx = task.stage_index || 0;
        var stageTot = task.stage_total || 7;
        var pct = stageTot > 0 ? Math.round(stageIdx / stageTot * 100) : 0;
        html += '<div class="task-progress">';
        html += '<div class="progress-bar"><div class="progress-fill" style="width:' + pct + '%"></div></div>';
        html += '<span class="progress-text">' + pct + '%</span>';
        html += '</div>';
        if (task.stage_name) {
          html += '<p class="task-stage">' + stageLabel(task.stage_name) + '</p>';
        }
      }

      if (task.track_progress && task.track_progress.track_total) {
        var tp = task.track_progress;
        var trackPct = tp.track_total > 0 ? Math.round(tp.track_completed / tp.track_total * 100) : 0;
        html += '<div class="task-track-progress">';
        html += '<div class="track-summary">' + tp.track_completed + '/' + tp.track_total + ' tracks</div>';
        if (tp.current_track_id) {
          html += '<span class="track-badge">' + tp.current_track_id.toUpperCase() + '</span>';
        }
        html += '</div>';
      }

      if (task.status === 'failed' && task.error) {
        html += '<div class="task-error">' + escapeHtml(String(task.error)) + '</div>';
        html += '<button class="btn-retry" data-retry="' + task.task_id + '">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>' +
          ' Retry</button>';
      }

      if (task.status === 'succeeded' && task.final_output) {
        html += '<div class="task-results">';
        var trackMidi = task.final_output.per_track_midi;
        if (trackMidi) {
          var roles = Object.keys(trackMidi);
          roles.forEach(function (role) {
            var url = getBackendUrl().replace(/\/+$/, '') + '/api/tasks/' + task.task_id + '/download/mid/' + encodeURIComponent(role);
            html += '<a class="btn-download btn-download--mid" href="' + url + '" download>' +
              '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' +
              role.toUpperCase() + '</a>';
          });
        }
        if (task.final_output.wav_file) {
          html += '<a class="btn-download" href="' + getBackendUrl().replace(/\/+$/, '') + '/api/tasks/' + task.task_id + '/download/wav" download>WAV</a>';
        }
        if (task.final_output.mp3_file) {
          html += '<a class="btn-download" href="' + getBackendUrl().replace(/\/+$/, '') + '/api/tasks/' + task.task_id + '/download/mp3" download>MP3</a>';
        }
        html += '</div>';
      }

      html += '</div>';
    });

    html += '</div>';
    container.innerHTML = html;

    bindRetryButtons();
  }

  function bindRetryButtons() {
    var btns = document.querySelectorAll('[data-retry]');
    btns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var taskId = btn.getAttribute('data-retry');
        retryTask(taskId);
      });
    });
  }

  function escapeHtml(text) {
    var map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, function (m) { return map[m]; });
  }

  /* ============================================
     Create Task
     ============================================ */

  function initCreateTask() {
    var btn = el('btnCreate');
    if (!btn) return;

    btn.addEventListener('click', function () {
      var input = el('promptInput');
      var promptValue = input ? input.value.trim() : '';
      if (!promptValue) {
        showToast('Please enter a description for your music.', 'error');
        return;
      }

      btn.disabled = true;

      var noteMode = (el('noteMode') && el('noteMode').value) || 'llm';
      var oobMode = (el('oobMode') && el('oobMode').value) || 'drop';
      var llmCfg = getLlmConfig();

      var body = JSON.stringify({
        prompt: promptValue,
        options: {
          note_mode: noteMode,
          oob_mode: oobMode
        },
        llm_provider: llmCfg.provider || 'gpt',
        llm_api_key: llmCfg.apiKey || null,
        llm_base_url: llmCfg.baseUrl || null,
        llm_model: llmCfg.model || null
      });

      api('/tasks', { method: 'POST', body: body })
        .then(function (task) {
          if (input) input.value = '';
          showToast('Task created: ' + (task.task_id || '').slice(0, 8), 'success');
          poll();
        })
        .catch(function (err) {
          showToast('Error: ' + err.message, 'error');
        })
        .finally(function () {
          btn.disabled = false;
        });
    });
  }

  /* ============================================
     Retry Task
     ============================================ */

  function retryTask(taskId) {
    api('/tasks/' + taskId + '/retry', { method: 'POST' })
      .then(function () {
        showToast('Task retry initiated', 'success');
        poll();
      })
      .catch(function (err) {
        showToast('Retry failed: ' + err.message, 'error');
      });
  }

  /* ============================================
     Settings Drawer
     ============================================ */

  function initSettingsDrawer() {
    var btn = el('btnSettings');
    var drawer = el('settingsDrawer');
    var overlay = el('settingsOverlay');
    var closeBtn = el('btnSettingsClose');

    if (!btn || !drawer || !overlay) return;

    function open() {
      drawer.style.display = 'block';
      overlay.style.display = 'block';
      drawer.style.animation = 'none';
      drawer.offsetHeight;
      drawer.style.animation = 'drawerIn 0.3s ease';
      populateSettingsFields();
    }

    function close() {
      drawer.style.display = 'none';
      overlay.style.display = 'none';
    }

    btn.addEventListener('click', open);
    closeBtn.addEventListener('click', close);
    overlay.addEventListener('click', close);

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && drawer.style.display !== 'none') {
        close();
      }
    });
  }

  function populateSettingsFields() {
    var backendInput = el('backendUrlInput');
    var providerSelect = el('llmProvider');
    var apiKeyInput = el('llmApiKey');
    var baseUrlInput = el('llmBaseUrl');
    var modelInput = el('llmModel');

    if (backendInput) {
      backendInput.value = localStorage.getItem(BACKEND_URL_KEY) || '';
    }
    var llmCfg = getLlmConfig();
    if (providerSelect) providerSelect.value = llmCfg.provider || 'gpt';
    if (apiKeyInput) apiKeyInput.value = llmCfg.apiKey;
    if (baseUrlInput) baseUrlInput.value = llmCfg.baseUrl;
    if (modelInput && llmCfg.model) {
      modelInput.value = llmCfg.model;
    }
    updateProviderUI();
  }

  /* ============================================
     Save All Settings
     ============================================ */

  function initSaveAll() {
    var btn = el('btnSaveAll');
    if (!btn) return;

    btn.addEventListener('click', function () {
      var backendVal = (el('backendUrlInput') && el('backendUrlInput').value || '').trim();
      var provider = (el('llmProvider') && el('llmProvider').value) || 'gpt';
      var apiKey = (el('llmApiKey') && el('llmApiKey').value || '').trim();
      var baseUrl = (el('llmBaseUrl') && el('llmBaseUrl').value || '').trim();
      var model = (el('llmModel') && el('llmModel').value) || 'gpt-4o';

      setBackendUrl(backendVal);

      setLlmConfig({
        provider: provider,
        apiKey: apiKey,
        baseUrl: baseUrl,
        model: model
      });

      showToast(t('save_success'), 'success');
    });
  }

  /* ============================================
     Provider UI
     ============================================ */

  function updateProviderUI() {
    var provider = (el('llmProvider') && el('llmProvider').value) || 'gpt';
    var apiKeyField = el('apiKeyField');
    var apiKeyInput = el('llmApiKey');
    var hint = el('llmHint');

    if (apiKeyField) {
      apiKeyField.style.display = '';
    }
    if (apiKeyInput) {
      if (provider === 'lmstudio') {
        apiKeyInput.removeAttribute('required');
        apiKeyInput.placeholder = '可选，LM Studio 认证 Token';
      } else {
        apiKeyInput.setAttribute('required', '');
        apiKeyInput.placeholder = 'sk-...';
      }
    }
    if (hint) {
      if (provider === 'lmstudio') {
        hint.textContent = t('settings_llm_hint_lmstudio');
      } else if (provider === 'deepseek') {
        hint.textContent = t('settings_llm_hint_deepseek');
      } else {
        hint.textContent = t('settings_llm_hint_gpt');
      }
    }
  }

  function initProviderSwitch() {
    var select = el('llmProvider');
    if (!select) return;
    select.addEventListener('change', function () {
      updateProviderUI();
    });
  }

  /* ============================================
     Clear All Storage
     ============================================ */

  function initClearAll() {
    var btn = el('btnClearAll');
    if (!btn) return;

    btn.addEventListener('click', function () {
      clearAllStorage();
      populateSettingsFields();
      showToast(t('clear_success'), 'success');
    });
  }

  /* ============================================
     Test Connection — LLM API → Single Note MIDI
     ============================================ */

  function initTestConnection() {
    var btn = el('btnTestConn');
    if (!btn) return;

    btn.addEventListener('click', function () {
      var llmCfg = getLlmConfig();
      var isLmStudio = llmCfg.provider === 'lmstudio';

      if (!isLmStudio && !llmCfg.apiKey) {
        showToast('Please configure your API Key first.', 'error');
        return;
      }

      if (!llmCfg.baseUrl) {
        showToast('Please configure the Base URL first.', 'error');
        return;
      }

      btn.disabled = true;
      var originalText = btn.textContent;
      btn.textContent = 'Testing…';

      var baseUrl = llmCfg.baseUrl;
      var model = llmCfg.model;

      var cleanBase = baseUrl.replace(/\/+$/, '');
      while (/\/chat\/completions$/.test(cleanBase)) {
        cleanBase = cleanBase.replace(/\/chat\/completions$/, '');
      }
      if (isLmStudio && !/\/v1$/.test(cleanBase)) {
        cleanBase = cleanBase + '/v1';
      }
      var apiUrl = cleanBase + '/chat/completions';

      var headers = {
        'Content-Type': 'application/json'
      };
      if (isLmStudio) {
        if (llmCfg.apiKey) {
          headers['Authorization'] = 'Bearer ' + llmCfg.apiKey;
        }
      } else {
        headers['Authorization'] = 'Bearer ' + llmCfg.apiKey;
      }

      var body = JSON.stringify({
        model: model,
        messages: [
          { role: 'system', content: 'You are a MIDI generator. Output ONLY valid JSON.' },
          { role: 'user', content: 'Generate a valid MIDI JSON object with exactly one note. The note should be middle C (60), velocity 80, duration 500ms, start at beat 0, track 0. Format: {"tracks":[{"notes":[{"pitch":60,"velocity":80,"start":0,"duration":0.5}]}]}. Output ONLY the JSON, no explanation.' }
        ],
        temperature: 0
      });

      fetch(apiUrl, {
        method: 'POST',
        headers: headers,
        body: body
      })
        .then(function (res) {
          if (!res.ok) {
            return res.json().catch(function () { return {}; }).then(function (errBody) {
              var msg = errBody.error ? (errBody.error.message || JSON.stringify(errBody.error)) : ('HTTP ' + res.status);
              throw new Error(msg);
            });
          }
          return res.json();
        })
        .then(function (data) {
          var content = (data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content) || '';
          try {
            var midiData = JSON.parse(content.trim());
            var blob = new Blob([JSON.stringify(midiData, null, 2)], { type: 'application/json' });
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'test_single_note_' + Date.now() + '.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(a.href);
            showToast(t('test_success'), 'success');
          } catch (e) {
            showToast('API returned non-JSON response: ' + content.slice(0, 100), 'error');
          }
        })
        .catch(function (err) {
          showToast(t('test_fail') + ' ' + err.message, 'error');
        })
        .finally(function () {
          btn.disabled = false;
          btn.textContent = originalText;
        });
    });
  }

  /* ============================================
     Language Switch
     ============================================ */

  function initLanguageSwitch() {
    var btnZh = el('btnLangZh');
    var btnEn = el('btnLangEn');

    if (btnZh) {
      btnZh.addEventListener('click', function () {
        currentLang = 'zh';
        localStorage.setItem(LANG_KEY, 'zh');
        applyLanguage();
        renderTasks();
      });
    }
    if (btnEn) {
      btnEn.addEventListener('click', function () {
        currentLang = 'en';
        localStorage.setItem(LANG_KEY, 'en');
        applyLanguage();
        renderTasks();
      });
    }
  }

  /* ============================================
     Backend URL Query Parameter Auto-Config
     ============================================ */

  function applyQueryBackendUrl() {
    var params = new URLSearchParams(window.location.search);
    var backend = params.get('backend');
    if (backend) {
      setBackendUrl(backend);
      try {
        var url = new URL(window.location.href);
        url.searchParams.delete('backend');
        window.history.replaceState({}, '', url.toString());
      } catch (e) {}
      return true;
    }
    return false;
  }

  /* ============================================
     Init
     ============================================ */

  function init() {
    var autoConfigured = applyQueryBackendUrl();

    applyLanguage();

    initHeroRotation();
    initAdvancedToggle();
    initClearPrompt();
    initKeyboard();
    initFooterYear();
    initSettingsDrawer();
    initProviderSwitch();
    initSaveAll();
    initClearAll();
    initTestConnection();
    initLanguageSwitch();
    initCreateTask();

    if (autoConfigured) {
      showToast(t('backend_auto_configured'), 'info');
    }

    poll();
    setInterval(poll, POLL_INTERVAL);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();