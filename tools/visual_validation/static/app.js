const state = {
  lastResult: null,
  examples: null,
};

const els = {
  healthText: document.querySelector("#healthText"),
  runAllBtn: document.querySelector("#runAllBtn"),
  currentSeasonBtn: document.querySelector("#currentSeasonBtn"),
  scheduleBtn: document.querySelector("#scheduleBtn"),
  searchBtn: document.querySelector("#searchBtn"),
  detailBtn: document.querySelector("#detailBtn"),
  loadExampleBtn: document.querySelector("#loadExampleBtn"),
  normalizeBtn: document.querySelector("#normalizeBtn"),
  weeklyNormalizeBtn: document.querySelector("#weeklyNormalizeBtn"),
  currentSeasonValue: document.querySelector("#currentSeasonValue"),
  scheduleCountValue: document.querySelector("#scheduleCountValue"),
  searchCountValue: document.querySelector("#searchCountValue"),
  lastStatusValue: document.querySelector("#lastStatusValue"),
  seasonInput: document.querySelector("#seasonInput"),
  weekdayInput: document.querySelector("#weekdayInput"),
  queryInput: document.querySelector("#queryInput"),
  limitInput: document.querySelector("#limitInput"),
  normalizeInput: document.querySelector("#normalizeInput"),
  weeklyNormalizeInput: document.querySelector("#weeklyNormalizeInput"),
  visualOutput: document.querySelector("#visualOutput"),
  jsonOutput: document.querySelector("#jsonOutput"),
  diagnosticsOutput: document.querySelector("#diagnosticsOutput"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setBusy(button, busy) {
  if (!button) return;
  button.disabled = busy;
}

function setStatus(result) {
  const ok = Boolean(result && result.ok);
  els.lastStatusValue.textContent = ok ? "OK" : "ERROR";
  els.lastStatusValue.style.color = ok ? "var(--ok)" : "var(--bad)";
}

function updateJson(result) {
  els.jsonOutput.textContent = JSON.stringify(result, null, 2);
}

function renderDiagnostics(result) {
  const diagnostics = Array.isArray(result?.diagnostics) ? result.diagnostics : [];
  if (!diagnostics.length) {
    els.diagnosticsOutput.className = "diagnostics empty-state";
    els.diagnosticsOutput.textContent = result?.error_message || result?.message || "暂无诊断信息";
    return;
  }

  els.diagnosticsOutput.className = "diagnostics";
  els.diagnosticsOutput.innerHTML = diagnostics
    .map(
      (item) => `
        <article class="diagnostic-item">
          <strong>${escapeHtml(item.code || "diagnostic")}</strong>
          <p>${escapeHtml(item.message || "")}</p>
          <p>${escapeHtml(item.field || "")} ${escapeHtml(item.raw_value ?? "")}</p>
        </article>
      `,
    )
    .join("");
}

function statusLine(result) {
  const statusClass = result?.ok ? "ok" : "bad";
  const statusText = result?.ok ? "OK" : "ERROR";
  const op = result?.operation || result?.service || "request";
  const error = result?.error_type || result?.error || "";
  return `
    <div class="status-line">
      <span class="pill ${statusClass}">${statusText}</span>
      <span class="pill">${escapeHtml(op)}</span>
      ${error ? `<span class="pill warn">${escapeHtml(error)}</span>` : ""}
    </div>
  `;
}

function itemTitle(item) {
  return item?.title_cn || item?.title_raw || item?.title_jp || item?.title_en || "未命名";
}

function renderPlatformLinks(item) {
  const links = item?.platform_links || [];
  if (!links.length) return "";
  return `
    <div class="platform-links">
      ${links
        .map((link) => {
          const label = link.label || link.kind || "link";
          return link.url
            ? `<a href="${escapeHtml(link.url)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`
            : `<span>${escapeHtml(label)}</span>`;
        })
        .join("")}
    </div>
  `;
}

function renderAnimeItem(item) {
  return `
    <article class="anime-item">
      <p class="anime-title">${escapeHtml(itemTitle(item))}</p>
      <div class="anime-meta">
        ${(item.types || []).map((type) => `<span>${escapeHtml(type)}</span>`).join("")}
        ${(item.tags || []).map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}
        ${item.air_time ? `<span>${escapeHtml(item.air_time)}</span>` : ""}
        ${item.start_date ? `<span>${escapeHtml(item.start_date)}</span>` : ""}
        ${item.confidence ? `<span>confidence ${escapeHtml(item.confidence)}</span>` : ""}
      </div>
      ${renderPlatformLinks(item)}
    </article>
  `;
}

function renderSchedule(result) {
  const days = result?.data?.days || [];
  if (!days.length) {
    return `${statusLine(result)}<div class="empty-state">没有周表条目</div>`;
  }

  const total = days.reduce((count, day) => count + (day.items?.length || 0), 0);
  els.scheduleCountValue.textContent = String(total);

  return `
    ${statusLine(result)}
    <div class="schedule-grid">
      ${days
        .map(
          (day) => `
          <section class="day-column">
            <header class="day-header">
              ${escapeHtml(day.label || `周${day.weekday}`)}
              <span>${day.items?.length || 0}</span>
            </header>
            <div class="anime-list">
              ${(day.items || []).map(renderAnimeItem).join("") || '<div class="empty-state">无条目</div>'}
            </div>
          </section>
        `,
        )
        .join("")}
    </div>
  `;
}

function renderResultList(result) {
  const data = Array.isArray(result?.data) ? result.data : result?.data ? [result.data] : [];
  els.searchCountValue.textContent = String(data.length);
  if (!data.length) {
    return `${statusLine(result)}<div class="empty-state">没有结果</div>`;
  }

  if (data.every((item) => item && typeof item === "object" && (item.operation || item.service))) {
    return renderValidationRun(result, data);
  }

  return `
    ${statusLine(result)}
    <div class="result-list">
      ${data.map(renderAnimeItem).join("")}
    </div>
  `;
}

function renderValidationRun(result, items) {
  return `
    ${statusLine(result)}
    <div class="result-list">
      ${items
        .map(
          (item) => `
            <article class="json-card">
              <div class="status-line">
                <span class="pill ${item.ok ? "ok" : "bad"}">${item.ok ? "OK" : "ERROR"}</span>
                <span class="pill">${escapeHtml(item.operation || item.service || "request")}</span>
                ${
                  item.error_type || item.error
                    ? `<span class="pill warn">${escapeHtml(item.error_type || item.error)}</span>`
                    : ""
                }
              </div>
              <dl>
                <dt>来源</dt><dd>${escapeHtml(item.source || "")}</dd>
                <dt>数据</dt><dd>${escapeHtml(summarizeResultData(item.data))}</dd>
                <dt>诊断</dt><dd>${escapeHtml((item.diagnostics || []).length)}</dd>
                <dt>错误</dt><dd>${escapeHtml(item.error_message || item.message || "")}</dd>
              </dl>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function summarizeResultData(data) {
  if (!data) return "无";
  if (Array.isArray(data)) return `${data.length} 条`;
  if (data.days) {
    const total = data.days.reduce((count, day) => count + (day.items?.length || 0), 0);
    return `${data.season || ""} ${data.days.length} 天 / ${total} 条`;
  }
  if (data.season) return data.season;
  if (data.title_cn || data.title_raw) return itemTitle(data);
  return "对象";
}

function renderObjectResult(result) {
  const data = result?.data || result;
  if (!data || typeof data !== "object") {
    return `${statusLine(result)}<div class="empty-state">${escapeHtml(result?.error_message || "没有结果")}</div>`;
  }

  return `
    ${statusLine(result)}
    <article class="json-card">
      <h3>${escapeHtml(itemTitle(data))}</h3>
      <dl>
        <dt>来源</dt><dd>${escapeHtml(data.source || result.source || "")}</dd>
        <dt>季度</dt><dd>${escapeHtml(data.season || "")}</dd>
        <dt>星期</dt><dd>${escapeHtml(data.weekday || "")}</dd>
        <dt>开播时间</dt><dd>${escapeHtml(data.air_time || "")}</dd>
        <dt>开始日期</dt><dd>${escapeHtml(data.start_date || "")}</dd>
        <dt>类型</dt><dd>${escapeHtml((data.types || []).join("、"))}</dd>
        <dt>标签</dt><dd>${escapeHtml((data.tags || []).join("、"))}</dd>
        <dt>制作</dt><dd>${escapeHtml((data.staff || []).join("、"))}</dd>
        <dt>声优</dt><dd>${escapeHtml((data.cast || []).join("、"))}</dd>
        <dt>别名</dt><dd>${escapeHtml((data.aliases || []).join("、"))}</dd>
        <dt>描述</dt><dd>${escapeHtml(data.description || "")}</dd>
      </dl>
      ${renderPlatformLinks(data)}
    </article>
  `;
}

function renderVisual(result) {
  if (result?.data?.days) {
    els.visualOutput.className = "visual-output";
    els.visualOutput.innerHTML = renderSchedule(result);
    return;
  }
  if (Array.isArray(result?.data)) {
    els.visualOutput.className = "visual-output";
    els.visualOutput.innerHTML = renderResultList(result);
    return;
  }
  els.visualOutput.className = "visual-output";
  els.visualOutput.innerHTML = renderObjectResult(result);
}

function showResult(result) {
  state.lastResult = result;
  setStatus(result);
  updateJson(result);
  renderDiagnostics(result);
  renderVisual(result);

  if (result?.data?.season) {
    els.currentSeasonValue.textContent = result.data.season;
  }
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    return { ok: false, error: response.statusText, status: response.status, ...payload };
  }
  return payload;
}

async function runAction(button, callback) {
  setBusy(button, true);
  try {
    const result = await callback();
    showResult(result);
    return result;
  } catch (error) {
    const result = { ok: false, error: error.name, message: error.message };
    showResult(result);
    return result;
  } finally {
    setBusy(button, false);
  }
}

async function loadExamples() {
  state.examples = await requestJson("/api/examples");
  els.normalizeInput.value = JSON.stringify(state.examples.normalizeAnime, null, 2);
  els.weeklyNormalizeInput.value = JSON.stringify(state.examples.normalizeWeeklySchedule, null, 2);
}

function scheduleUrl() {
  const params = new URLSearchParams();
  params.set("season", els.seasonInput.value.trim() || "current");
  if (els.weekdayInput.value) {
    params.set("weekday", els.weekdayInput.value);
  }
  return `/api/yuc/weekly-schedule?${params.toString()}`;
}

function searchUrl(path) {
  const params = new URLSearchParams();
  params.set("season", els.seasonInput.value.trim() || "current");
  params.set("query", els.queryInput.value.trim());
  if (path.includes("search")) {
    params.set("limit", els.limitInput.value || "5");
  }
  return `${path}?${params.toString()}`;
}

async function runAll() {
  setBusy(els.runAllBtn, true);
  const results = [];
  try {
    results.push(await requestJson("/api/yuc/current-season"));
    results.push(await requestJson(scheduleUrl()));
    results.push(await requestJson(searchUrl("/api/yuc/search")));
    const normalizePayload = JSON.parse(els.normalizeInput.value || "{}");
    results.push(
      await requestJson("/api/anime/normalize", {
        method: "POST",
        body: JSON.stringify(normalizePayload),
      }),
    );
    const ok = results.every((result) => result.ok);
    showResult({
      ok,
      operation: "run_all_visual_validation",
      data: results,
      diagnostics: results.flatMap((result) => result.diagnostics || []),
    });
  } finally {
    setBusy(els.runAllBtn, false);
  }
}

function wireTabs() {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab-button").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      document.querySelector(`#${button.dataset.tab}Tab`).classList.add("active");
    });
  });
}

async function init() {
  wireTabs();
  await loadExamples();
  const health = await requestJson("/api/health");
  els.healthText.textContent = health.ok ? "本地验证服务已连接" : "本地验证服务异常";

  els.currentSeasonBtn.addEventListener("click", () =>
    runAction(els.currentSeasonBtn, () => requestJson("/api/yuc/current-season")),
  );
  els.scheduleBtn.addEventListener("click", () =>
    runAction(els.scheduleBtn, () => requestJson(scheduleUrl())),
  );
  els.searchBtn.addEventListener("click", () =>
    runAction(els.searchBtn, () => requestJson(searchUrl("/api/yuc/search"))),
  );
  els.detailBtn.addEventListener("click", () =>
    runAction(els.detailBtn, () => requestJson(searchUrl("/api/yuc/detail"))),
  );
  els.loadExampleBtn.addEventListener("click", loadExamples);
  els.normalizeBtn.addEventListener("click", () =>
    runAction(els.normalizeBtn, () =>
      requestJson("/api/anime/normalize", {
        method: "POST",
        body: JSON.stringify(JSON.parse(els.normalizeInput.value || "{}")),
      }),
    ),
  );
  els.weeklyNormalizeBtn.addEventListener("click", () =>
    runAction(els.weeklyNormalizeBtn, () =>
      requestJson("/api/anime/weekly-schedule", {
        method: "POST",
        body: JSON.stringify(JSON.parse(els.weeklyNormalizeInput.value || "{}")),
      }),
    ),
  );
  els.runAllBtn.addEventListener("click", runAll);
}

init().catch((error) => {
  els.healthText.textContent = `初始化失败：${error.message}`;
  showResult({ ok: false, error: error.name, message: error.message });
});
