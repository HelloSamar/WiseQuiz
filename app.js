"use strict";

const MAX_SCORE = 5;
const WEAK_THRESHOLD = 3;
const STORAGE_KEY = "wisequiz.progress.v1";
const SETTINGS_KEY = "wisequiz.settings.v1";

const CONFIG = {
  ows: {
    title: "One Word Substitution",
    icon: "🎯",
    source: "ows.json",
    label: "Choose the one-word substitution for",
    desc: "Phrase to one-word answers from the OWS dataset.",
    normalise(row, i) {
      return makeItem("ows", row.Phrases, row["One Word Substitution"] || row["One Word"], row.Example, row["Hindi Meaning"], row.Level, i);
    },
  },
  idioms: {
    title: "Idioms",
    icon: "💬",
    source: "idioms.json",
    label: "Choose the idiom that means",
    desc: "Match idioms with meanings and examples.",
    normalise(row, i) {
      return makeItem("idioms", row.Meaning, row.Idiom, row.Example, row.Meaning, "Idiom", i);
    },
  },
  synonyms: {
    title: "Synonyms",
    icon: "🔁",
    source: "synonyms.json",
    label: "Choose the synonym of",
    desc: "Practice same-meaning word pairs.",
    normalise(row, i) {
      return makeItem("synonyms", row.Word, row.Synonym, row.Example, row.Meaning, "Synonym", i);
    },
  },
  antonyms: {
    title: "Antonyms",
    icon: "↔️",
    source: "antonyms.json",
    label: "Choose the antonym of",
    desc: "Practice opposite-word pairs.",
    normalise(row, i) {
      return makeItem("antonyms", row.Word, row.Antonym, row.Example, row.Meaning, "Antonym", i);
    },
  },
};

const state = {
  data: { ows: [], idioms: [], synonyms: [], antonyms: [] },
  errors: {},
  progress: readJson(STORAGE_KEY, {}),
  settings: { includeMastered: false, weakOnly: false, unlearnedOnly: false, studyMode: "smart", ...readJson(SETTINGS_KEY, {}) },
  active: null,
  pool: [],
  current: null,
  answered: false,
  correct: 0,
  attempted: 0,
  streak: 0,
  recent: [],
};

const $ = selector => document.querySelector(selector);
const $$ = selector => Array.from(document.querySelectorAll(selector));

function clean(value) { return value == null ? "" : String(value).trim(); }
function makeItem(category, promptRaw, answerRaw, exampleRaw, meaningRaw, levelRaw, index) {
  const prompt = clean(promptRaw);
  const answer = clean(answerRaw);
  if (!prompt || !answer) return null;
  return { id: `${category}-${index}-${answer.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`, category, prompt, answer, example: clean(exampleRaw), meaning: clean(meaningRaw), level: clean(levelRaw) };
}
function readJson(key, fallback) { try { const raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : fallback; } catch { return fallback; } }
function writeJson(key, value) { localStorage.setItem(key, JSON.stringify(value)); }
function saveProgress() { writeJson(STORAGE_KEY, state.progress); }
function saveSettings() { writeJson(SETTINGS_KEY, state.settings); }
function progressOf(q) {
  const saved = state.progress[q.category]?.[q.id] || {};
  const score = Math.max(0, Math.min(MAX_SCORE, Number(saved.score) || 0));
  const attempt = Math.max(0, Number(saved.attempt) || 0);
  return { score, attempt, mastered: Boolean(saved.mastered) || score >= MAX_SCORE };
}
function setProgress(q, next) {
  if (!state.progress[q.category]) state.progress[q.category] = {};
  state.progress[q.category][q.id] = { score: Math.max(0, Math.min(MAX_SCORE, next.score)), attempt: Math.max(0, next.attempt), mastered: Boolean(next.mastered) };
  saveProgress();
}

async function loadData() {
  await Promise.all(Object.entries(CONFIG).map(async ([key, config]) => {
    try {
      const response = await fetch(config.source, { cache: "no-store" });
      if (!response.ok) throw new Error(`${config.source}: ${response.status}`);
      const rows = await response.json();
      state.data[key] = Array.isArray(rows) ? rows.map((row, index) => config.normalise(row, index)).filter(Boolean) : [];
      delete state.errors[key];
    } catch (error) {
      state.data[key] = [];
      state.errors[key] = error.message;
    }
  }));
}

function statsFor(key) {
  return state.data[key].reduce((s, q) => {
    const p = progressOf(q);
    s.total += 1;
    if (p.mastered) s.mastered += 1;
    if (p.attempt === 0) s.unlearned += 1;
    if (p.attempt > 0 && !p.mastered && p.score < WEAK_THRESHOLD) s.weak += 1;
    return s;
  }, { total: 0, mastered: 0, weak: 0, unlearned: 0 });
}
function overallStats() {
  return Object.keys(CONFIG).reduce((total, key) => {
    const s = statsFor(key);
    total.total += s.total;
    total.mastered += s.mastered;
    total.weak += s.weak;
    total.unlearned += s.unlearned;
    return total;
  }, { total: 0, mastered: 0, weak: 0, unlearned: 0 });
}
function setText(selector, text) { const el = $(selector); if (el) el.textContent = text; }
function showScreen(id) { $$(".screen").forEach(screen => screen.classList.toggle("active", screen.id === id)); }

function renderHome() {
  showScreen("homeScreen");
  syncControls();
  renderOverallStats();
  renderCategories();
  renderStatus();
}
function syncControls() {
  $("#includeMastered").checked = state.settings.includeMastered;
  $("#weakOnly").checked = state.settings.weakOnly;
  $("#unlearnedOnly").checked = state.settings.unlearnedOnly;
  $("#studyMode").value = state.settings.studyMode;
}
function renderOverallStats() {
  const target = $("#overallStats");
  target.replaceChildren();
  const s = overallStats();
  addStat(target, s.total, "Total questions");
  addStat(target, s.mastered, "Mastered");
  addStat(target, s.weak, "Weak");
  addStat(target, s.unlearned, "Unlearned");
}
function addStat(parent, number, label) {
  const card = document.createElement("article");
  card.className = "stat";
  const value = document.createElement("strong");
  value.textContent = number.toLocaleString();
  const caption = document.createElement("span");
  caption.textContent = label;
  card.append(value, caption);
  parent.append(card);
}
function renderCategories() {
  const target = $("#categoryGrid");
  target.replaceChildren();
  Object.entries(CONFIG).forEach(([key, config]) => {
    const stats = statsFor(key);
    const percent = stats.total ? Math.round((stats.mastered / stats.total) * 100) : 0;
    const card = document.createElement("button");
    card.type = "button";
    card.className = "category-card";
    card.disabled = stats.total === 0;
    card.addEventListener("click", () => startQuiz(key));
    const icon = document.createElement("span"); icon.className = "cat-icon"; icon.textContent = config.icon;
    const title = document.createElement("h3"); title.textContent = config.title;
    const desc = document.createElement("p"); desc.textContent = config.desc;
    const mini = document.createElement("div"); mini.className = "mini-stats";
    addPill(mini, `${stats.total.toLocaleString()} items`); addPill(mini, `${percent}% mastered`); addPill(mini, `${stats.weak} weak`);
    card.append(icon, title, desc, mini);
    target.append(card);
  });
}
function addPill(parent, text) { const pill = document.createElement("span"); pill.className = "pill"; pill.textContent = text; parent.append(pill); }
function renderStatus() {
  const loaded = Object.values(state.data).reduce((sum, rows) => sum + rows.length, 0);
  const errors = Object.keys(state.errors);
  const status = $("#statusBox");
  if (!loaded) { status.className = "status-box error"; status.textContent = "No quiz data loaded."; return; }
  status.className = errors.length ? "status-box warn" : "status-box ok";
  status.textContent = errors.length ? `Loaded ${loaded.toLocaleString()} questions. Missing: ${errors.map(key => CONFIG[key].title).join(", ")}.` : `Ready: ${loaded.toLocaleString()} questions across four boxes.`;
}

function buildPool(key) {
  return state.data[key].filter(q => {
    const p = progressOf(q);
    if (!state.settings.includeMastered && p.mastered) return false;
    if (state.settings.weakOnly && !(p.attempt > 0 && !p.mastered && p.score < WEAK_THRESHOLD)) return false;
    if (state.settings.unlearnedOnly && p.attempt !== 0) return false;
    return true;
  });
}
function startQuiz(key) {
  state.active = key;
  state.pool = buildPool(key);
  state.correct = 0;
  state.attempted = 0;
  state.streak = 0;
  state.recent = [];
  if (!state.pool.length) { window.alert("No questions match these filters. Try including mastered words or clearing filters."); return; }
  showScreen("quizScreen");
  nextQuestion();
}
function weightedPick() {
  const fresh = state.pool.filter(q => !state.recent.includes(q.id));
  const list = fresh.length ? fresh : state.pool;
  const weighted = [];
  list.forEach(q => {
    const p = progressOf(q);
    const weight = p.attempt === 0 ? 5 : p.mastered ? 1 : Math.max(1, MAX_SCORE - p.score + 1);
    for (let i = 0; i < weight; i += 1) weighted.push(q);
  });
  return weighted[Math.floor(Math.random() * weighted.length)];
}
function nextQuestion() {
  state.current = weightedPick();
  state.answered = false;
  state.recent.push(state.current.id);
  if (state.recent.length > Math.min(10, state.pool.length)) state.recent.shift();
  const config = CONFIG[state.active];
  setText("#quizCategory", config.title);
  setText("#promptLabel", config.label);
  setText("#questionText", state.current.prompt);
  updateQuizStats();
  $("#progressLine").style.width = `${Math.min(100, (state.attempted / Math.max(1, state.pool.length)) * 100)}%`;
  $("#feedbackBox").className = "feedback-box hidden";
  $("#feedbackBox").replaceChildren();
  $("#nextBtn").classList.add("hidden");
  renderOptions();
}
function renderOptions() {
  const correct = state.current.answer;
  const answers = Array.from(new Set(state.data[state.active].map(q => q.answer).filter(answer => answer && answer !== correct)));
  shuffle(answers);
  const options = shuffle([correct, ...answers.slice(0, 3)]);
  const target = $("#optionGrid");
  target.replaceChildren();
  options.forEach((answer, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "option-btn";
    button.dataset.answer = answer;
    button.addEventListener("click", () => answerQuestion(answer));
    const key = document.createElement("span"); key.className = "option-key"; key.textContent = String(index + 1);
    const label = document.createElement("span"); label.textContent = answer;
    button.append(key, label);
    target.append(button);
  });
}
function answerQuestion(answer) {
  if (state.answered) return;
  state.answered = true;
  state.attempted += 1;
  const q = state.current;
  const correct = answer === q.answer;
  const prev = progressOf(q);
  const score = correct ? (state.settings.studyMode === "instant" ? MAX_SCORE : prev.score + 1) : Math.max(0, prev.score - 1);
  setProgress(q, { score, attempt: prev.attempt + 1, mastered: score >= MAX_SCORE });
  if (correct) { state.correct += 1; state.streak += 1; } else { state.streak = 0; }
  $$(".option-btn").forEach(button => {
    button.disabled = true;
    const value = button.dataset.answer;
    if (value === q.answer) button.classList.add("correct");
    else if (value === answer) button.classList.add("wrong");
    else button.classList.toggle("reveal", value === q.answer);
  });
  renderFeedback(correct);
  updateQuizStats();
  $("#nextBtn").classList.remove("hidden");
}
function renderFeedback(correct) {
  const q = state.current;
  const box = $("#feedbackBox");
  box.className = `feedback-box ${correct ? "good" : "bad"}`;
  box.replaceChildren();
  const headline = document.createElement("strong");
  headline.textContent = correct ? "Correct" : `Correct answer: ${q.answer}`;
  box.append(headline);
  if (q.meaning) addFeedbackLine(box, "Meaning", q.meaning);
  if (q.example) addFeedbackLine(box, "Example", q.example);
}
function addFeedbackLine(parent, label, value) {
  const line = document.createElement("p");
  const strong = document.createElement("b");
  strong.textContent = `${label}: `;
  line.append(strong, document.createTextNode(value));
  parent.append(line);
}
function updateQuizStats() { setText("#quizCount", `${state.attempted} attempted · ${state.correct} correct · streak ${state.streak}`); }
function shuffle(array) { for (let i = array.length - 1; i > 0; i -= 1) { const j = Math.floor(Math.random() * (i + 1)); [array[i], array[j]] = [array[j], array[i]]; } return array; }

function bindEvents() {
  $("#backBtn").addEventListener("click", renderHome);
  $("#nextBtn").addEventListener("click", nextQuestion);
  $$("[data-action='home']").forEach(el => el.addEventListener("click", event => { event.preventDefault(); renderHome(); }));
  ["includeMastered", "weakOnly", "unlearnedOnly"].forEach(id => {
    $("#" + id).addEventListener("change", event => { state.settings[id] = event.target.checked; saveSettings(); renderHome(); });
  });
  $("#studyMode").addEventListener("change", event => { state.settings.studyMode = event.target.value; saveSettings(); });
  $("#resetBtn").addEventListener("click", () => { if (window.confirm("Reset all WiseQuiz progress on this browser?")) { state.progress = {}; saveProgress(); renderHome(); } });
  $("#exportBtn").disabled = true;
  $("#importInput").disabled = true;
  document.addEventListener("keydown", event => {
    if (!$("#quizScreen").classList.contains("active")) return;
    if (/^[1-4]$/.test(event.key) && !state.answered) $$(".option-btn")[Number(event.key) - 1]?.click();
    if (event.key === "Enter" && state.answered) nextQuestion();
  });
}

loadData().then(() => { bindEvents(); renderHome(); }).catch(error => {
  console.error(error);
  const status = $("#statusBox");
  status.className = "status-box error";
  status.textContent = "WiseQuiz failed to start.";
});
