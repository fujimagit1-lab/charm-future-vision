#!/usr/bin/env python3
"""charm_seed_finder.html を組み立てる (WASM base64 + スキル一覧を埋め込み)"""
import base64, json, pathlib

HERE = pathlib.Path(__file__).parent
wasm_b64 = base64.b64encode((HERE / 'seedfind.wasm').read_bytes()).decode()
wasm_simd_b64 = base64.b64encode((HERE / 'seedfind_simd.wasm').read_bytes()).decode()
skills = json.dumps(json.loads((HERE / 'skill_list.json').read_text()), ensure_ascii=False)

HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>護石 基準seed復元ツール</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 16px auto; max-width: 860px; padding: 0 12px; color: #222; }
  h1 { font-size: 20px; margin: 8px 0; }
  .note { color: #555; font-size: 13px; line-height: 1.6; }
  .obsrow { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; padding: 6px 0; border-bottom: 1px solid #eee; }
  .obsrow .no { min-width: 22px; flex: 0 0 auto; white-space: nowrap; color: #888; font-size: 13px; }
  button { font-size: 14px; padding: 6px 10px; border: 1px solid #bbb; border-radius: 6px; background: #f7f7f7; cursor: pointer; }
  button:hover { background: #eee; }
  button.primary { background: #2563eb; color: #fff; border-color: #2563eb; font-weight: bold; padding: 8px 18px; }
  button.primary:hover { background: #1d4ed8; }
  button:disabled { opacity: .45; cursor: default; }
  .skbtn { min-width: 118px; text-align: left; }
  .skbtn .lv { color: #2563eb; font-weight: bold; }
  select, input[type=number] { font-size: 14px; padding: 6px; border: 1px solid #bbb; border-radius: 6px; }
  .del { color: #b91c1c; }
  #progwrap { display: none; margin: 14px 0; }
  #bar { height: 14px; background: #e5e7eb; border-radius: 7px; overflow: hidden; }
  #barfill { height: 100%; width: 0%; background: #2563eb; transition: width .3s; }
  #stats { font-size: 13px; color: #444; margin-top: 6px; line-height: 1.7; }
  #results { margin: 12px 0; }
  .hit { background: #ecfdf5; border: 1px solid #10b981; border-radius: 8px; padding: 10px 12px; margin: 8px 0; font-size: 15px; }
  .hit b { font-size: 17px; }
  .warn { background: #fffbeb; border: 1px solid #f59e0b; border-radius: 8px; padding: 10px 12px; margin: 8px 0; font-size: 14px; }
  dialog { border: 1px solid #ccc; border-radius: 10px; max-width: 520px; width: 92vw; max-height: 80vh; }
  dialog::backdrop { background: rgba(0,0,0,.35); }
  .skitem { display: flex; align-items: center; gap: 6px; padding: 5px 0; border-bottom: 1px solid #f0f0f0; }
  .skitem .nm { flex: 1; }
  .lvbtn.sel { background: #2563eb; color: #fff; }
  #sklist { overflow-y: auto; max-height: 52vh; margin-top: 8px; }
  .row2 { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 10px 0; }
</style>
</head>
<body>
<h1>護石 基準seed復元ツール</h1>
<p class="note">連続で引いた護石の結果を入力すると、基準seedと現在の錬金カウンタ位置を全探索で復元します。
計算はすべてこの端末の中で行われ、通信は一切しません。護石は<b>3個以上</b>の入力を推奨します（2個だと候補が複数残ることがあります）。</p>

<h3>1. 連続で引いた護石（古い順）</h3>
<div id="obsrows"></div>
<div class="row2">
  <button id="addrow">＋ 護石を追加</button>
  <button id="clearrows">入力をクリア</button>
</div>

<h3>2. カウンタ範囲</h3>
<p class="note">観測した<b>1個目の護石のカウンタ位置</b>があり得る範囲を指定します。「今までに錬金した回数は1万回以下のはず」なら下限0・上限10000です。探索時間は範囲の幅に比例します。<br>
上限まで探して見つからなかった場合は、<b>下限を前回の上限に</b>して再探索すれば、済んだ範囲をやり直さずに続きを探せます。</p>
<div class="row2">
  <label>下限 <input type="number" id="wlo" value="0" min="0" max="10000000" step="100" style="width:110px"></label>
  <label>上限 <input type="number" id="whi" value="10000" min="1" max="10000000" step="100" style="width:110px"></label>
</div>

<div class="row2">
  <button id="start" class="primary">探索開始</button>
  <button id="stop" disabled>中止</button>
  <span id="workernote" class="note"></span>
  <label class="note">ワーカー数 <select id="wcount"></select></label>
</div>

<div id="progwrap">
  <div id="bar"><div id="barfill"></div></div>
  <div id="stats"></div>
</div>
<div id="results"></div>

<dialog id="skdlg">
  <h3 style="margin-top:0">スキルを選ぶ</h3>
  <input type="text" id="sksearch" placeholder="スキル名で検索" style="width:96%; padding:7px; font-size:15px;">
  <div class="row2">
    <button id="sknone">なしにする（空スキル）</button>
    <button id="skclose">閉じる</button>
  </div>
  <div id="sklist"></div>
</dialog>

<script>
"use strict";
const WASM_B64 = "__WASM_B64__";
const WASM_SIMD_B64 = "__WASM_SIMD_B64__";
const SIMD_OK = (() => { try { return WebAssembly.validate(new Uint8Array([0,97,115,109,1,0,0,0,1,5,1,96,0,1,123,3,2,1,0,10,10,1,8,0,65,0,253,15,253,98,11])); } catch (e) { return false; } })();
const LANES = SIMD_OK ? 128 : 64;
function engineBytes() { return b64ToBytes(SIMD_OK ? WASM_SIMD_B64 : WASM_B64); }
const SKILLS = __SKILLS__;
const SLOT_PATTERNS = [[3,0,0],[2,1,0],[2,0,0],[1,1,1],[1,1,0],[1,0,0],[0,0,0]];
const SKILL_MAP = new Map(SKILLS.map(s => [s[0], s]));
document.getElementById('workernote').textContent = '探索エンジン: ' + (SIMD_OK ? 'SIMD高速版' : '標準版');
document.getElementById('wcount').innerHTML = '<option value="auto">自動（論理コア数 ' + (navigator.hardwareConcurrency || 4) + '）</option>' +
  [1, 2, 3, 4, 6, 8, 12, 16, 24, 32].map(n => '<option value="' + n + '">' + n + '</option>').join('');

// ---------- 観測入力 ----------
let rows = []; // {sk: [[id,lv]x3], sl: [a,b,c]}
function defaultRow() { return { sk: [[0,0],[0,0],[0,0]], sl: [0,0,0] }; }
function skillLabel(id, lv) {
  if (!id) return '（なし）';
  const s = SKILL_MAP.get(id);
  return (s ? s[1] : ('ID:' + id)) + ' <span class="lv">Lv' + lv + '</span>';
}
function renderRows() {
  const box = document.getElementById('obsrows');
  box.innerHTML = '';
  rows.forEach((r, ri) => {
    const div = document.createElement('div');
    div.className = 'obsrow';
    let h = '<span class="no">' + (ri + 1) + '.</span>';
    r.sk.forEach((sk, si) => {
      h += '<button class="skbtn" data-row="' + ri + '" data-pos="' + si + '">' + skillLabel(sk[0], sk[1]) + '</button>';
    });
    h += '<select data-slot="' + ri + '">' + SLOT_PATTERNS.map(p =>
      '<option value="' + p.join(',') + '"' + (r.sl.join(',') === p.join(',') ? ' selected' : '') + '>スロット ' + p.join('-') + '</option>').join('') + '</select>';
    if (rows.length > 2) h += '<button class="del" data-del="' + ri + '">削除</button>';
    div.innerHTML = h;
    box.appendChild(div);
  });
  box.querySelectorAll('.skbtn').forEach(b => b.addEventListener('click', () => openPicker(+b.dataset.row, +b.dataset.pos)));
  box.querySelectorAll('select[data-slot]').forEach(s => s.addEventListener('change', () => {
    rows[+s.dataset.slot].sl = s.value.split(',').map(Number); saveInputs();
  }));
  box.querySelectorAll('button[data-del]').forEach(b => b.addEventListener('click', () => {
    rows.splice(+b.dataset.del, 1); renderRows(); saveInputs();
  }));
}
document.getElementById('addrow').addEventListener('click', () => { if (rows.length < 8) { rows.push(defaultRow()); renderRows(); saveInputs(); } });
document.getElementById('clearrows').addEventListener('click', () => { rows = [defaultRow(), defaultRow(), defaultRow()]; renderRows(); saveInputs(); });

// ---------- スキルピッカー ----------
let pickTarget = null;
const dlg = document.getElementById('skdlg');
function openPicker(ri, si) {
  pickTarget = [ri, si];
  document.getElementById('sksearch').value = '';
  renderSkillList('');
  dlg.showModal();
}
function renderSkillList(q) {
  const list = document.getElementById('sklist');
  list.innerHTML = '';
  const cur = pickTarget ? rows[pickTarget[0]].sk[pickTarget[1]] : [0, 0];
  SKILLS.forEach(s => {
    if (q && !s[1].includes(q)) return;
    const div = document.createElement('div');
    div.className = 'skitem';
    let h = '<span class="nm">' + s[1] + '</span>';
    s[2].forEach(lv => {
      h += '<button class="lvbtn' + (cur[0] === s[0] && cur[1] === lv ? ' sel' : '') + '" data-id="' + s[0] + '" data-lv="' + lv + '">Lv' + lv + '</button>';
    });
    div.innerHTML = h;
    list.appendChild(div);
  });
  list.querySelectorAll('.lvbtn').forEach(b => b.addEventListener('click', () => {
    rows[pickTarget[0]].sk[pickTarget[1]] = [+b.dataset.id, +b.dataset.lv];
    dlg.close(); renderRows(); saveInputs();
  }));
}
document.getElementById('sksearch').addEventListener('input', e => renderSkillList(e.target.value.trim()));
document.getElementById('sknone').addEventListener('click', () => {
  rows[pickTarget[0]].sk[pickTarget[1]] = [0, 0];
  dlg.close(); renderRows(); saveInputs();
});
document.getElementById('skclose').addEventListener('click', () => dlg.close());

// ---------- 入力の保存 ----------
function saveInputs() {
  try { localStorage.setItem('sf_inputs', JSON.stringify({ rows, wlo: document.getElementById('wlo').value, whi: document.getElementById('whi').value })); } catch (e) {}
}
function loadInputs() {
  try {
    const d = JSON.parse(localStorage.getItem('sf_inputs') || 'null');
    if (d && Array.isArray(d.rows) && d.rows.length >= 2) { rows = d.rows; document.getElementById('wlo').value = d.wlo || 0; document.getElementById('whi').value = d.whi || d.W || 10000; return; }
  } catch (e) {}
  rows = [defaultRow(), defaultRow(), defaultRow()];
}
document.getElementById('wlo').addEventListener('change', saveInputs);
document.getElementById('whi').addEventListener('change', saveInputs);
loadInputs();
renderRows();

// ---------- ワーカー ----------
function sfWorkerMain() {
  let ex = null, cfg = null;
  self.onmessage = async (ev) => {
    const m = ev.data;
    if (m.t === 'start') {
      cfg = m;
      const instance = await WebAssembly.instantiate(m.module, {});
      ex = instance.exports;
      m.obs.forEach((o, i) => ex.sf_set_obs(i, o[0], o[1], o[2], o[3], o[4], o[5], o[6], o[7], o[8]));
      self.postMessage({ t: 'need' });
    } else if (m.t === 'chunk') {
      ex.sf_begin(cfg.K, cfg.wlo, cfg.whi, m.lo, m.hi);
      const batchesPerChunk = Math.max(1, Math.floor(20000000 / (cfg.lanes * (cfg.whi - cfg.wlo))));
      let lastFound = 0, cont = 1;
      while (cont === 1) {
        cont = ex.sf_step(batchesPerChunk);
        const fc = ex.sf_found_count();
        for (let i = lastFound; i < fc; i++) self.postMessage({ t: 'found', seed: ex.sf_found_seed(i), counter: ex.sf_found_counter(i) });
        lastFound = fc;
        self.postMessage({ t: 'prog', cursor: ex.sf_cursor() });
      }
      self.postMessage({ t: 'need' });
    } else if (m.t === 'end') {
      self.postMessage({ t: 'done' });
    }
  };
}
function b64ToBytes(b64) {
  const bin = atob(b64);
  const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return u8;
}

// ---------- 探索制御 ----------
let workers = [], running = false, startTime = 0, totalSeeds = 0, cursors = [], Wcur = 0, timerId = null, foundList = [];
let completedSeeds = 0, nextSeed = 0, chunkSeeds = 0, inflight = [];
let modulePromise = null;
function getModule() {
  if (!modulePromise) modulePromise = WebAssembly.compile(engineBytes());
  return modulePromise;
}
async function validateObs(obs, K) {
  const mod = await getModule();
  const instance = await WebAssembly.instantiate(mod, {});
  const ex = instance.exports;
  obs.forEach((o, i) => ex.sf_set_obs(i, o[0], o[1], o[2], o[3], o[4], o[5], o[6], o[7], o[8]));
  ex.sf_begin(K, 0, 100, 0, 64);
  return [ex.sf_compat0(), ex.sf_compat1()];
}
function fmt(n) { return n.toLocaleString('ja-JP'); }
function updateStats(finished) {
  const doneSeeds = completedSeeds + cursors.reduce((a, c) => a + c, 0);
  const pairs = doneSeeds * Wcur;
  const totalPairs = totalSeeds * Wcur;
  const el = (Date.now() - startTime) / 1000;
  const rate = el > 0 ? pairs / el : 0;
  const pct = totalPairs ? (100 * pairs / totalPairs) : 0;
  document.getElementById('barfill').style.width = pct.toFixed(2) + '%';
  let eta = '—';
  if (rate > 0 && !finished) { const sec = (totalPairs - pairs) / rate; eta = sec >= 90 ? '約' + Math.round(sec / 60) + '分' : '約' + Math.round(sec) + '秒'; }
  document.getElementById('stats').innerHTML =
    '進捗 ' + pct.toFixed(1) + '%（' + fmt(pairs) + ' / ' + fmt(totalPairs) + ' ペア）<br>' +
    '速度 ' + (rate / 1e6).toFixed(1) + ' Mペア/秒 ／ 経過 ' + Math.floor(el / 60) + '分' + Math.floor(el % 60) + '秒 ／ 残り ' + eta +
    (foundList.length ? '<br>発見: ' + foundList.length + ' 件' : '');
}
document.getElementById('start').addEventListener('click', async () => {
  if (running) return;
  const K = rows.length;
  let wlo = parseInt(document.getElementById('wlo').value, 10);
  let whi = parseInt(document.getElementById('whi').value, 10);
  if (isNaN(wlo) || wlo < 0) wlo = 0;
  if (wlo > 10000000) wlo = 10000000;
  if (isNaN(whi) || whi <= wlo) whi = wlo + 1;
  if (whi > 10000000) whi = 10000000;
  const W = whi - wlo;
  const obs = rows.map(r => [r.sk[0][0], r.sk[0][1], r.sk[1][0], r.sk[1][1], r.sk[2][0], r.sk[2][1], r.sl[0], r.sl[1], r.sl[2]]);
  const resBox = document.getElementById('results');
  resBox.innerHTML = '';
  const [c0, c1] = await validateObs(obs, K);
  if (c0 === 0 || c1 === 0) {
    resBox.innerHTML = '<div class="warn">入力された護石の組み合わせが実在しません（' + (c0 === 0 ? '1個目' : '2個目') + 'のスキル／スロットの組み合わせがゲーム内に存在しない組み合わせです）。スキルLvやスロットの入力ミスがないか確認してください。</div>';
    return;
  }
  running = true; foundList = [];
  document.getElementById('start').disabled = true;
  document.getElementById('stop').disabled = false;
  document.getElementById('progwrap').style.display = 'block';
  const mod = await getModule();
  const TOTAL = 100000000;
  const wsel = document.getElementById('wcount').value;
  const NW = wsel === 'auto' ? Math.min(navigator.hardwareConcurrency || 4, 16) : parseInt(wsel, 10);
  workers = []; cursors = []; inflight = []; completedSeeds = 0; nextSeed = 0;
  chunkSeeds = Math.max(128, Math.min(4194304, Math.floor(400000000 / W / 128) * 128));
  totalSeeds = TOTAL; Wcur = W; startTime = Date.now();
  const src = 'const sfWorkerMain = ' + sfWorkerMain.toString() + ';\nsfWorkerMain();';
  const url = URL.createObjectURL(new Blob([src], { type: 'text/javascript' }));
  let doneCount = 0;
  function assignChunk(i) {
    if (nextSeed >= TOTAL) { workers[i].postMessage({ t: 'end' }); return; }
    const lo = nextSeed, hi = Math.min(TOTAL, lo + chunkSeeds);
    nextSeed = hi;
    inflight[i] = [lo, hi];
    cursors[i] = 0;
    workers[i].postMessage({ t: 'chunk', lo, hi });
  }
  for (let i = 0; i < NW; i++) {
    const wk = new Worker(url);
    cursors.push(0);
    inflight.push(null);
    wk.onmessage = (ev) => {
      const m = ev.data;
      if (m.t === 'prog') { if (inflight[i]) cursors[i] = Math.min(m.cursor, inflight[i][1]) - inflight[i][0]; }
      else if (m.t === 'found') {
        foundList.push(m);
        const div = document.createElement('div');
        div.className = 'hit';
        div.innerHTML = '基準seed: <b>' + fmt(m.seed) + '</b> ／ 観測した護石の位置（カウンタ）: <b>' + fmt(m.counter) + '</b>';
        resBox.appendChild(div);
      } else if (m.t === 'need') {
        if (inflight[i]) { completedSeeds += inflight[i][1] - inflight[i][0]; inflight[i] = null; cursors[i] = 0; }
        assignChunk(i);
      } else if (m.t === 'done') {
        doneCount++;
        if (doneCount === NW) finish(false);
      }
    };
    wk.postMessage({ t: 'start', module: mod, obs, K, wlo, whi, lanes: LANES });
    workers.push(wk);
  }
  timerId = setInterval(() => updateStats(false), 300);
  updateStats(false);
});
function finish(stopped) {
  running = false;
  clearInterval(timerId);
  workers.forEach(w => w.terminate());
  workers = [];
  document.getElementById('start').disabled = false;
  document.getElementById('stop').disabled = true;
  updateStats(true);
  const resBox = document.getElementById('results');
  if (!foundList.length) {
    resBox.innerHTML = '<div class="warn">' + (stopped ? '探索を中止しました。' : '範囲内に候補は見つかりませんでした。下限をいまの上限にして続きを探索するか、観測入力（スキルLv・スロット・順番）にミスがないか確認してください。') + '</div>';
  } else if (!stopped) {
    const div = document.createElement('div');
    div.className = 'note';
    div.textContent = '探索完了。見つかった基準seedとカウンタ位置を未来視アプリに入力すると、その先の錬金結果を予測できます。候補が複数ある場合は、護石を追加でもう一度探索すると絞り込めます。';
    resBox.appendChild(div);
  }
}
document.getElementById('stop').addEventListener('click', () => { if (running) finish(true); });
</script>
</body>
</html>
"""

out = HTML.replace('__WASM_B64__', wasm_b64).replace('__WASM_SIMD_B64__', wasm_simd_b64).replace('__SKILLS__', skills)
dest = HERE.parent / 'goals/charm-future-vision-standalone-app/files/charm_seed_finder.html'
dest.write_text(out)
print('written:', dest, len(out), 'bytes')
