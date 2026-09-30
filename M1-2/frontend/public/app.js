"use strict";

const API = ((window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) || "http://localhost:8000").replace(/\/+$/, "");
const $ = (sel) => document.querySelector(sel);

/* ---------- 유틸 ---------- */
// innerHTML을 쓰지 않고 DOM API로만 그려서 XSS를 막는다.
function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  node.append(...children.filter((c) => c != null));
  return node;
}

const fmtMan = (n) => `${Math.round(n / 10000).toLocaleString("ko-KR")}만 명`;
const fmtNum = (n) => Number(n).toLocaleString("ko-KR");
const fmtPct = (p) => (p == null ? "데이터 부족" : `${p > 0 ? "▲ +" : p < 0 ? "▼ " : ""}${p.toFixed(1)}%`);
const pctClass = (p) => (p == null ? "" : p > 0 ? "up" : p < 0 ? "down" : "");
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString("ko-KR", { dateStyle: "medium", timeStyle: "short" }) : "");

function formatDetail(detail) {
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(", ");
  return typeof detail === "string" ? detail : "";
}

async function api(path, { method = "GET", body, timeoutMs = 60000 } = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(API + path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new Error(formatDetail(data && data.detail) || `요청에 실패했어요 (${res.status})`);
    return data;
  } catch (e) {
    if (e.name === "AbortError") throw new Error("서버 응답이 너무 늦어요. 잠시 후 다시 시도해 주세요.");
    if (e instanceof TypeError) throw new Error("서버에 연결할 수 없어요. 서버 상태와 CORS(ALLOWED_ORIGINS) 설정을 확인해 주세요.");
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

function showMsg(node, text, isError = false) {
  node.textContent = text;
  node.className = isError ? "msg error" : "msg";
  node.hidden = false;
}

/* ---------- 서버 깨우기 (Render 무료 티어 콜드스타트) ---------- */
async function wakeServer() {
  const status = $("#serverStatus");
  const notice = $("#notice");
  const slow = setTimeout(() => (notice.hidden = false), 3000);
  try {
    await api("/health", { timeoutMs: 90000 });
    status.textContent = "서버 연결됨";
    status.className = "pill ok";
  } catch (e) {
    status.textContent = "서버 연결 실패";
    status.className = "pill err";
  } finally {
    clearTimeout(slow);
    notice.hidden = true;
  }
}

/* ---------- 탭 ---------- */
function activateTab(name) {
  document.querySelectorAll(".tab").forEach((t) => {
    const on = t.dataset.tab === name;
    t.classList.toggle("active", on);
    t.setAttribute("aria-selected", String(on));
  });
  ["chat", "data", "history"].forEach((n) => ($(`#tab-${n}`).hidden = n !== name));
}
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => activateTab(t.dataset.tab)));

/* ---------- 요약 ---------- */
function card(label, value, sub, cls = "") {
  return el("div", { class: "card" },
    el("div", { class: "card-label" }, label),
    el("div", { class: `card-value ${cls}`.trim() }, value),
    el("div", { class: "card-sub" }, sub || ""));
}

async function loadSummary() {
  const box = $("#summary");
  try {
    const s = await api("/api/data/summary");
    box.replaceChildren(
      card("기간", s.period, `${s.count}개 주말`, "small"),
      card("주말 평균", fmtMan(s.metrics.average), "상위 10편 합계 기준"),
      card("최고 주말", fmtMan(s.metrics.max), s.metrics.max_date),
      card("최근 주말", fmtMan(s.latest.value), s.latest.date),
      card("최근 4주 트렌드", fmtPct(s.trend_pct), "직전 4주 대비", pctClass(s.trend_pct)),
      card("전년 동기 대비", fmtPct(s.yoy_pct), "작년 같은 시기 4주", pctClass(s.yoy_pct)),
    );
    loadInsights();
  } catch (e) {
    box.replaceChildren(el("div", { class: "muted" }, `요약을 불러오지 못했어요: ${e.message}`));
  }
}

/* ---------- 채팅 ---------- */
const chatLog = $("#chatLog");
const chatInput = $("#chatInput");
const sendBtn = $("#sendBtn");
let convId = null;
let sending = false;

const SUGGESTIONS = ["가장 흥행한 주말은 언제였어?", "최근 추세가 어때?", "작년 이맘때와 비교하면?", "지난 주말은 어땠어?"];

function addBubble(role, text) {
  const b = el("div", { class: `bubble ${role}` });
  b.textContent = text;
  chatLog.append(b);
  chatLog.scrollTop = chatLog.scrollHeight;
  return b;
}

function addToolBadges(bubble, calls) {
  if (!calls || !calls.length) return;
  bubble.append(
    el("div", { class: "tool-badges" },
      ...calls.map((t) => el("div", {}, `🔧 ${t.tool}`, t.reason ? ` — ${t.reason}` : "")))
  );
}

function addTyping() {
  const note = el("span", { class: "typing-note" }, "서버가 깨어나는 중이라 조금 더 걸릴 수 있어요…");
  note.hidden = true;
  const b = el("div", { class: "bubble assistant typing" },
    el("span", { class: "dots" }, el("span"), el("span"), el("span")), note);
  chatLog.append(b);
  chatLog.scrollTop = chatLog.scrollHeight;
  return { node: b, note };
}

function resetChat() {
  convId = null;
  chatLog.replaceChildren();
  addBubble("assistant", "안녕하세요! 저장된 주말 박스오피스 데이터를 바탕으로 궁금한 점에 답해 드릴게요. 아래 질문으로 시작해 보세요.");
  $("#chips").hidden = false;
  document.querySelectorAll(".conv-item").forEach((n) => n.classList.remove("active"));
}

async function sendMessage(text) {
  text = text.trim();
  if (sending || !text) return;
  sending = true;
  sendBtn.disabled = true;
  $("#chips").hidden = true;
  addBubble("user", text);
  chatInput.value = "";
  const typing = addTyping();
  const slow = setTimeout(() => (typing.note.hidden = false), 5000);
  try {
    const res = await api("/api/chat", { method: "POST", body: { message: text, conversation_id: convId } });
    typing.node.remove();
    const bubble = addBubble("assistant", res.reply);
    addToolBadges(bubble, res.tool_calls);
    convId = res.conversation_id;
    loadConversations();
  } catch (e) {
    typing.node.remove();
    addBubble("error", e.message);
  } finally {
    clearTimeout(slow);
    sending = false;
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

$("#chatForm").addEventListener("submit", (e) => { e.preventDefault(); sendMessage(chatInput.value); });
$("#newChat").addEventListener("click", resetChat);
$("#chips").replaceChildren(...SUGGESTIONS.map((q) => el("button", { class: "chip", type: "button", onclick: () => sendMessage(q) }, q)));

/* ---------- 대화 기록 ---------- */
async function loadConversations() {
  const list = $("#convList");
  try {
    const items = await api("/api/conversations");
    if (!items.length) {
      list.replaceChildren(el("div", { class: "muted" }, "저장된 대화가 아직 없어요. 채팅을 시작하면 자동으로 저장돼요."));
      return;
    }
    list.replaceChildren(...items.map((c) =>
      el("div", { class: `conv-item${c.id === convId ? " active" : ""}`, onclick: () => openConversation(c.id) },
        el("div", {},
          el("div", { class: "conv-title" }, c.title || "제목 없음"),
          el("div", { class: "muted" }, `${c.message_count}개 메시지 · ${fmtDate(c.updated_at)}`)),
        el("button", { class: "btn small danger", onclick: (ev) => { ev.stopPropagation(); deleteConversation(c.id); } }, "삭제"))
    ));
  } catch (e) {
    list.replaceChildren(el("div", { class: "msg error" }, e.message));
  }
}

async function openConversation(id) {
  try {
    const conv = await api(`/api/conversations/${encodeURIComponent(id)}`);
    chatLog.replaceChildren();
    conv.messages.forEach((m) => addBubble(m.role, m.content));
    convId = conv.id;
    $("#chips").hidden = true;
    activateTab("chat");
    loadConversations();
  } catch (e) {
    alert(e.message);
  }
}

async function deleteConversation(id) {
  if (!confirm("이 대화를 삭제할까요?")) return;
  try {
    await api(`/api/conversations/${encodeURIComponent(id)}`, { method: "DELETE" });
    if (id === convId) resetChat();
    loadConversations();
  } catch (e) {
    alert(e.message);
  }
}

/* ---------- 데이터 관리 ---------- */
let rows = [];

function renderTable() {
  $("#dataCount").textContent = `총 ${rows.length}개 (최신순)`;
  $("#dataBody").replaceChildren(...rows.slice().reverse().map((r) =>
    el("tr", {},
      el("td", {}, r.date),
      el("td", { class: "num" }, fmtNum(r.value)),
      el("td", {}, r.memo || ""),
      el("td", {},
        el("button", { class: "btn small ghost", onclick: () => openEdit(r) }, "수정"),
        el("button", { class: "btn small danger", onclick: () => removeRow(r) }, "삭제")))
  ));
}

async function loadData() {
  try {
    rows = await api("/api/data");
    renderTable();
  } catch (e) {
    showMsg($("#dataMsg"), e.message, true);
  }
}

$("#addForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = { date: $("#addDate").value, value: Number($("#addValue").value), memo: $("#addMemo").value.trim() };
  try {
    await api("/api/data", { method: "POST", body });
    showMsg($("#dataMsg"), `${body.date} 데이터를 추가했어요.`);
    $("#addValue").value = "";
    $("#addMemo").value = "";
    await Promise.all([loadData(), loadSummary()]);
  } catch (err) {
    showMsg($("#dataMsg"), err.message, true);
  }
});

$("#syncBtn").addEventListener("click", async () => {
  const btn = $("#syncBtn");
  btn.disabled = true;
  btn.textContent = "가져오는 중…";
  try {
    const r = await api("/api/data/sync?weeks=8", { method: "POST", timeoutMs: 90000 });
    showMsg($("#dataMsg"),
      `KOBIS에서 ${r.fetched}주를 조회했어요 → 새로 ${r.added}개 추가, ${r.skipped}개는 이미 있음` +
      (r.failed ? ` (${r.failed}주 조회 실패)` : ""));
    await Promise.all([loadData(), loadSummary()]);
  } catch (err) {
    showMsg($("#dataMsg"), err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "🔄 최신 데이터 가져오기";
  }
});

async function removeRow(r) {
  if (!confirm(`${r.date} 데이터를 삭제할까요?`)) return;
  try {
    await api(`/api/data/${encodeURIComponent(r.id)}`, { method: "DELETE" });
    showMsg($("#dataMsg"), `${r.date} 데이터를 삭제했어요.`);
    await Promise.all([loadData(), loadSummary()]);
  } catch (err) {
    showMsg($("#dataMsg"), err.message, true);
  }
}

const dialog = $("#editDialog");
let editingId = null;

function openEdit(r) {
  editingId = r.id;
  $("#editDate").textContent = `날짜: ${r.date} (날짜는 수정할 수 없어요)`;
  $("#editValue").value = r.value;
  $("#editMemo").value = r.memo || "";
  $("#editMsg").hidden = true;
  dialog.showModal();
}

$("#editCancel").addEventListener("click", () => dialog.close());
$("#editForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api(`/api/data/${encodeURIComponent(editingId)}`, {
      method: "PUT",
      body: { value: Number($("#editValue").value), memo: $("#editMemo").value.trim() },
    });
    dialog.close();
    showMsg($("#dataMsg"), `${editingId} 데이터를 수정했어요.`);
    await Promise.all([loadData(), loadSummary()]);
  } catch (err) {
    showMsg($("#editMsg"), err.message, true);
  }
});

/* ---------- 시작 ---------- */
(async function init() {
  resetChat();
  await wakeServer(); // 콜드스타트를 먼저 기다린 뒤 나머지 요청을 보낸다
  await Promise.all([loadSummary(), loadData(), loadConversations()]);
})();

/* ---------- 보너스: 추가 지표 + 추세 그래프 ---------- */
let trendChart = null;
let lastStats = null;

const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function renderStatCards(s) {
  const ma = s.moving_avg_4w[s.moving_avg_4w.length - 1];
  $("#statCards").replaceChildren(
    card("중앙값", fmtMan(s.median), "전체 주말 기준"),
    card("변동폭 (표준편차)", fmtMan(s.std_dev), "클수록 주말별 편차가 커요"),
    card("직전 주 대비", fmtPct(s.wow_change_pct), "가장 최근 두 주말", pctClass(s.wow_change_pct)),
    card("4주 이동평균", ma ? fmtMan(ma.value) : "-", ma ? `${ma.date} 기준` : ""),
  );
}

function renderChart() {
  if (!lastStats) return;
  const msg = $("#chartMsg");
  if (typeof Chart === "undefined") {
    showMsg(msg, "그래프 라이브러리를 불러오지 못했어요. 네트워크를 확인해 주세요.", true);
    return;
  }
  msg.hidden = true;

  const text = cssVar("--text");
  const muted = cssVar("--muted");
  const grid = cssVar("--line");
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;

  const labels = lastStats.series.map((p) => p.date);
  if (trendChart) trendChart.destroy();
  trendChart = new Chart($("#trendChart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "주말 관객수", data: lastStats.series.map((p) => p.value),
          borderColor: cssVar("--gold-2"), backgroundColor: cssVar("--gold-2"),
          borderWidth: 1.5, pointRadius: 0, pointHoverRadius: 4, tension: 0.2 },
        { label: "4주 이동평균", data: lastStats.moving_avg_4w.map((p) => p.value),
          borderColor: "#60a5fa", backgroundColor: "#60a5fa",
          borderWidth: 2.5, borderDash: [6, 4], pointRadius: 0, pointHoverRadius: 4, tension: 0.3 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { color: text } },
        tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmtMan(ctx.parsed.y)}` } },
      },
      scales: {
        x: { ticks: { color: muted, maxTicksLimit: 8 }, grid: { color: grid } },
        y: { ticks: { color: muted, callback: (v) => `${Math.round(v / 10000)}만` }, grid: { color: grid } },
      },
    },
  });
}

async function loadInsights() {
  try {
    lastStats = await api("/api/data/statistics");
    renderStatCards(lastStats);
    renderChart();
  } catch (e) {
    $("#statCards").replaceChildren();
    showMsg($("#chartMsg"), `그래프를 불러오지 못했어요: ${e.message}`, true);
  }
}

/* ---------- 보너스: 내보내기 (CSV / JSON) ---------- */
async function downloadExport(format) {
  try {
    const res = await fetch(`${API}/api/data/export?format=${format}`);
    if (!res.ok) throw new Error(`내보내기에 실패했어요 (${res.status})`);
    const url = URL.createObjectURL(await res.blob());
    const a = el("a", { href: url, download: `boxoffice.${format}` });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    showMsg($("#dataMsg"), `${format.toUpperCase()} 파일을 내려받았어요.`);
  } catch (e) {
    const text = e instanceof TypeError
      ? "서버에 연결할 수 없어요. 서버 상태와 CORS(ALLOWED_ORIGINS) 설정을 확인해 주세요."
      : e.message;
    showMsg($("#dataMsg"), text, true);
  }
}
$("#exportCsv").addEventListener("click", () => downloadExport("csv"));
$("#exportJson").addEventListener("click", () => downloadExport("json"));

/* ---------- 보너스: 다크 모드 토글 ---------- */
const themeBtn = $("#themeToggle");
const currentTheme = () => (document.documentElement.dataset.theme === "light" ? "light" : "dark");
function syncThemeBtn() {
  const dark = currentTheme() === "dark";
  themeBtn.textContent = dark ? "🌙" : "☀️";
  themeBtn.setAttribute("aria-label", dark ? "라이트 모드로 전환" : "다크 모드로 전환");
}
themeBtn.addEventListener("click", () => {
  const next = currentTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch { /* 저장 실패는 무시 */ }
  syncThemeBtn();
  renderChart();   // 그래프 색도 새 테마에 맞게 다시 그림
});
syncThemeBtn();