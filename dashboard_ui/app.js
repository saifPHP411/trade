'use strict';
const byId = id => document.getElementById(id);
const usd = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'});
const axis = new Intl.NumberFormat('en-US', {maximumFractionDigits: 1, notation: 'compact'});
const countFormat = new Intl.NumberFormat('en-US', {maximumFractionDigits: 6});
const shortDate = new Intl.DateTimeFormat('en-GB', {month: 'short', day: '2-digit', timeZone: 'America/New_York'});
const localDate = new Intl.DateTimeFormat('ar-JO', {dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Amman'});
const sideText = {buy:'شراء', sell:'بيع', long:'شراء', short:'بيع'};
const sectionText = {account:'ملخص الحساب', equity:'سجل الأداء', positions:'المراكز', fills:'الصفقات', orders:'الأوامر'};
const canvas = byId('performance');
let snapshot = null;
let period = '1M';
let metric = 'equity';
let tab = 'fills';
let requestNumber = 0;
let chartPoints = [];
let hoverIndex = null;

function numeric(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}
function money(value) {
  const number = numeric(value);
  return number === null ? '—' : usd.format(number);
}
function quantity(value) {
  const number = numeric(value);
  return number === null ? '—' : countFormat.format(number);
}
function timestamp(value) {
  const date = new Date(value);
  return value && Number.isFinite(date.getTime()) ? localDate.format(date) : '—';
}
function setValue(id, label, diff = null) {
  const element = byId(id);
  element.textContent = label;
  element.classList.toggle('positive', diff !== null && diff > 0);
  element.classList.toggle('negative', diff !== null && diff < 0);
}
function renderTable(target, data, headers, cells, empty) {
  const root = byId(target);
  root.replaceChildren();
  if (!data?.length) {
    const message = document.createElement('p');
    message.className = 'empty';
    message.textContent = data === null ? 'البيانات غير متاحة حاليًا.' : data === undefined ? 'جاري التحميل…' : empty;
    root.append(message);
    return;
  }
  const wrapper = document.createElement('div');
  wrapper.className = 'table-wrap';
  const table = document.createElement('table');
  const heading = table.createTHead().insertRow();
  for (const name of headers) {
    const headingCell = document.createElement('th');
    headingCell.scope = 'col';
    headingCell.textContent = name;
    heading.append(headingCell);
  }
  const body = table.createTBody();
  for (const item of data) {
    const row = body.insertRow();
    for (const value of cells(item)) {
      const cell = row.insertCell();
      cell.dir = 'auto';
      cell.textContent = value ?? '—';
    }
    const pnl = numeric(item.unrealized_pl);
    if (pnl) row.cells[row.cells.length - 1].className = pnl > 0 ? 'positive' : 'negative';
  }
  wrapper.append(table);
  root.append(wrapper);
}
function renderActivity() {
  if (tab === 'fills') {
    renderTable('trade-data', snapshot?.fills, ['السهم','الجهة','الكمية','سعر التعبئة','الوقت · عمّان'], row =>
      [row.symbol, sideText[row.side] ?? row.side, quantity(row.qty), money(row.price), timestamp(row.transaction_time)], 'ما في صفقات منفّذة على الحساب.');
  } else {
    renderTable('trade-data', snapshot?.orders, ['السهم','الجهة','الكمية','النوع','الحالة','السعر المحدد','سعر الوقف'], row =>
      [row.symbol, sideText[row.side] ?? row.side, quantity(row.qty), row.type, row.status, money(row.limit_price), money(row.stop_price)], 'ما في أوامر مفتوحة.');
  }
}
function renderSnapshot() {
  const account = snapshot.account;
  const equity = numeric(account?.equity);
  const last = numeric(account?.last_equity);
  const delta = equity !== null && last !== null ? equity - last : null;
  setValue('equity', money(equity));
  setValue('delta', delta === null ? '—' : (delta > 0 ? '+' : '') + money(delta), delta);
  setValue('pct', delta === null || !last ? '—' : (delta > 0 ? '+' : '') + (100 * delta / last).toFixed(2) + '%', delta);
  setValue('cash', money(account?.cash));
  setValue('buying', money(account?.buying_power));
  setValue('position-count', snapshot.positions ? String(snapshot.positions.length) : '');
  renderTable('position-data', snapshot.positions, ['السهم','الجهة','الكمية','متوسط الدخول','السعر الحالي','قيمة المركز','الربح والخسارة'], row =>
    [row.symbol, sideText[row.side] ?? row.side, quantity(row.qty), money(row.avg_entry_price), money(row.current_price), money(row.market_value), money(row.unrealized_pl)], 'ما في مراكز مفتوحة.');
  renderActivity();
  drawChart();
}
function drawChart() {
  chartPoints = (snapshot?.equity ?? []).filter(point => numeric(point[metric]) !== null);
  canvas.hidden = chartPoints.length === 0;
  byId('chart-empty').hidden = chartPoints.length > 0;
  if (!chartPoints.length) {
    byId('chart-empty').textContent = snapshot?.equity === null ? 'تعذّر جلب سجل الأداء.' : 'ما في بيانات كافية للفترة المختارة.';
    byId('chart-detail').textContent = '';
    return;
  }
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const scale = window.devicePixelRatio || 1;
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext('2d');
  ctx.scale(scale, scale);
  const values = chartPoints.map(point => Number(point[metric]));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padding = max === min ? Math.max(Math.abs(max) * .012, 1) : (max - min) * .13;
  const left = 57, right = width - 16, top = 10, bottom = height - 31;
  const x = index => chartPoints.length === 1 ? (left + right) / 2 : left + index * (right - left) / (chartPoints.length - 1);
  const y = value => bottom - (value - min + padding) / (max - min + 2 * padding) * (bottom - top);
  ctx.font = '11px system-ui';
  ctx.fillStyle = '#ccb0c2';
  ctx.strokeStyle = '#493346';
  ctx.lineWidth = 1;
  for (let i = 0; i < 5; i++) {
    const gridY = top + i * (bottom - top) / 4;
    ctx.beginPath(); ctx.moveTo(left, gridY); ctx.lineTo(right, gridY); ctx.stroke();
    ctx.textAlign = 'right';
    ctx.fillText('$' + axis.format(max + padding - i * (max - min + 2 * padding) / 4), left - 7, gridY + 4);
  }
  const labelCount = Math.min(width < 530 ? 3 : 5, chartPoints.length);
  for (let i = 0; i < labelCount; i++) {
    const index = labelCount === 1 ? 0 : Math.round(i * (chartPoints.length - 1) / (labelCount - 1));
    ctx.textAlign = i === 0 ? 'left' : i === labelCount - 1 ? 'right' : 'center';
    ctx.fillText(shortDate.format(chartPoints[index].time * 1000), x(index), height - 8);
  }
  if (chartPoints.length > 1) {
    const gradient = ctx.createLinearGradient(0, top, 0, bottom);
    gradient.addColorStop(0, '#ec91b37d'); gradient.addColorStop(1, '#ec91b305');
    ctx.beginPath(); values.forEach((value, index) => index ? ctx.lineTo(x(index), y(value)) : ctx.moveTo(x(index), y(value)));
    ctx.lineTo(right, bottom); ctx.lineTo(left, bottom); ctx.closePath();
    ctx.fillStyle = gradient; ctx.fill();
    ctx.beginPath(); values.forEach((value, index) => index ? ctx.lineTo(x(index), y(value)) : ctx.moveTo(x(index), y(value)));
    ctx.strokeStyle = '#f7a4c5'; ctx.lineWidth = 2.25; ctx.stroke();
  }
  const selected = hoverIndex === null ? chartPoints.length - 1 : Math.min(hoverIndex, chartPoints.length - 1);
  ctx.beginPath(); ctx.arc(x(selected), y(values[selected]), 4, 0, 2 * Math.PI); ctx.fillStyle = '#ffd3e5'; ctx.fill();
  byId('chart-detail').textContent = shortDate.format(chartPoints[selected].time * 1000) + ' · ' + money(values[selected]);
  canvas.setAttribute('aria-label', 'قيم الأداء من ' + money(values[0]) + ' إلى ' + money(values.at(-1)));
}
async function refresh() {
  const current = ++requestNumber;
  const button = byId('refresh');
  button.disabled = true;
  byId('update').textContent = 'جاري التحديث…';
  try {
    const response = await fetch('/api/portfolio?period=' + encodeURIComponent(period), {cache:'no-store'});
    if (!response.ok) throw new Error('Portfolio request failed');
    const data = await response.json();
    if (current !== requestNumber) return;
    snapshot = data;
    hoverIndex = null;
    renderSnapshot();
    const unavailable = data.unavailable;
    byId('error').hidden = unavailable.length === 0;
    byId('error').textContent = unavailable.length === 5 ? 'تعذّر الاتصال بـAlpaca Paper. تحقّق من إعدادات الخدمة.' :
      'تعذّر تحديث: ' + unavailable.map(name => sectionText[name]).join('، ') + '.';
    byId('update').textContent = unavailable.length === 5 ? 'البيانات غير متاحة' : 'آخر قراءة · ' + timestamp(data.asOf);
  } catch {
    if (current !== requestNumber) return;
    byId('error').hidden = false;
    byId('error').textContent = snapshot ? 'توقف التحديث. الأرقام المعروضة من آخر قراءة ناجحة.' : 'تعذّر تحميل البيانات. جرّب التحديث.';
    byId('update').textContent = snapshot ? 'آخر قراءة · ' + timestamp(snapshot.asOf) : 'البيانات غير متاحة';
    if (!snapshot) byId('chart-empty').textContent = 'البيانات غير متاحة.';
  } finally {
    if (current === requestNumber) button.disabled = false;
  }
}
function bindSwitch(name, change) {
  const buttons = [...document.querySelectorAll('[data-' + name + ']')];
  for (const button of buttons) button.addEventListener('click', () => {
    if (button.getAttribute('aria-pressed') === 'true') return;
    for (const item of buttons) item.setAttribute('aria-pressed', String(item === button));
    change(button.dataset[name]);
  });
}
bindSwitch('period', next => { period = next; refresh(); });
bindSwitch('metric', next => { metric = next; drawChart(); });
bindSwitch('tab', next => { tab = next; renderActivity(); });
canvas.addEventListener('pointermove', event => {
  if (!chartPoints.length || canvas.clientWidth < 74) return;
  const relative = (event.offsetX - 57) / (canvas.clientWidth - 73);
  const index = Math.max(0, Math.min(chartPoints.length - 1, Math.round(relative * (chartPoints.length - 1))));
  if (index !== hoverIndex) { hoverIndex = index; drawChart(); }
});
canvas.addEventListener('pointerleave', () => { hoverIndex = null; drawChart(); });
new ResizeObserver(() => { if (!canvas.hidden) drawChart(); }).observe(canvas.parentElement);
byId('refresh').addEventListener('click', refresh);
renderActivity();
refresh();
