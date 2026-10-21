/* Mirrors models/mass_energy_balance.py and models/tea_financials.py. Keep constants in sync. */
(() => {
'use strict';
const K = {crumb:.88, moist:.012, cp:1.95, dh:460, lam:2257, eta:.72, lhv:38000, tAmb:25, tCond:35,
  cpOil:2.2, lamOil:300, cpGas:2, cpW:4.18, dtW:10, capex:280000, exp:.65, elt:25, kwh:115, tariff:.14,
  naoh:4.5, labour:78000, maint:22200, steel:220, tax:.3, disc:.14, yrs:5, dep:10, co2:.85, h2s:.0115};
const SLIDERS = [
  {id:'feed', label:'Daily tyre capacity', unit:'TPD', min:5, max:50, step:1, v:10},
  {id:'temp', label:'Rotary kiln temperature', unit:'°C', min:400, max:600, step:5, v:500},
  {id:'days', label:'Annual operating days', unit:'days/yr', min:200, max:330, step:5, v:300},
  {id:'tpo', label:'TPO price', unit:'$/t', min:300, max:800, step:10, v:550},
  {id:'rcb', label:'rCB price', unit:'$/t', min:100, max:500, step:10, v:380}];
const $ = id => document.getElementById(id);
const fmt = (n, d = 0) => n.toLocaleString('en-US', {minimumFractionDigits:d, maximumFractionDigits:d});
const usd = n => (n < 0 ? '-$' : '$') + fmt(Math.abs(n));

const yields = T => {
  const oil = 44.2 - 0.00115 * (T - 500) ** 2, gas = 9.8 + 0.055 * (T - 400) + 0.00018 * (T - 400) ** 2;
  return {steel:12, oil, gas, rcb:100 - (12 + oil + gas)};
};
const irr = fl => {
  const f = r => fl.reduce((s, c, t) => s + c / (1 + r) ** t, 0);
  let lo = -.99, hi = 100;
  if (f(lo) * f(hi) > 0) return null;
  for (let i = 0; i < 200; i++) { const mid = (lo + hi) / 2; if (f(lo) * f(mid) > 0) lo = mid; else hi = mid; }
  return (lo + hi) / 2;
};

function model({feed, temp, days, tpo, rcb}) {
  const y = yields(temp), f = feed / 100;
  const m = {tpo:y.oil * f, rcb:y.rcb * f, steel:y.steel * f, gas:y.gas * f};
  const crumb = K.crumb * feed, water = K.moist * feed;
  const duty = (crumb * K.cp * (temp - K.tAmb) + crumb * K.dh + water * K.lam) / K.eta / 1000;
  const syn = m.gas * K.lhv / 1000;
  const qCond = (m.tpo * (K.cpOil * (temp - K.tCond) + K.lamOil) + m.gas * K.cpGas * (temp - K.tCond)) / 1000;
  const yr = feed * days, capex = K.capex * (feed / 10) ** K.exp;
  const revenue = days * (m.tpo * tpo + m.rcb * rcb + m.steel * K.steel);
  const opex = yr * (K.elt + K.kwh * K.tariff + K.naoh) + K.labour * Math.sqrt(feed / 10) + K.maint * capex / K.capex;
  const ebitda = revenue - opex, tax = K.tax * Math.max(0, ebitda - capex / K.dep), cf = ebitda - tax;
  const flows = [-capex, ...Array(K.yrs).fill(cf)];
  const h2s = m.gas * 1000 * K.h2s;
  return {...m, crumb, water, duty, syn, ss:100 * syn / duty, qCond, cw:qCond * 1000 / (K.cpW * K.dtW),
    capex, revenue, opex, ebitda, cf, flows, npv:flows.reduce((s, c, t) => s + c / (1 + K.disc) ** t, 0),
    irr:irr(flows), payback:cf > 0 ? capex / cf : null, co2:yr * K.co2,
    h2s, naohKg:h2s / 34.08 * 2 * 40, so2Kg:h2s / 34.08 * 64.07};
}

const UNITS = {
  U101:{t:'U-101 Hydraulic de-beader and twin-shaft shredder', s:'Low-speed, high-torque shear blades (45 kW) screen tyres to 25–50 mm chips so the kiln charge heats evenly.',
    r:(m, s) => [['Whole tyres in', `${fmt(s.feed, 2)} t/d`], ['Chip size', '25–50 mm'], ['Conditions', '25 °C / 101.3 kPa']]},
  U102:{t:'U-102 Overband NdFeB magnetic separator', s:'Removes 99.2% of carbon-steel bead and belt wire before pyrolysis, protecting the kiln wall and keeping steel out of the char.',
    r:(m) => [['Steel wire out', `${fmt(m.steel, 2)} t/d`], ['Crumb to kiln', `${fmt(m.crumb, 2)} t/d`], ['Conditions', '25 °C / 101.3 kPa']]},
  U103:{t:'U-103 Externally heated rotary kiln', s:'310S stainless cylinder (L 6.6 m, D 2.2 m, 3 rpm, sized for the 10-TPD base case). Slight positive pressure and O₂ below 0.5 vol% prevent air ingress.',
    r:(m, s) => [['Crumb in', `${fmt(m.crumb, 2)} t/d`], ['Vapour out', `${fmt(m.tpo + m.gas, 2)} t/d`], ['Char out', `${fmt(m.rcb, 2)} t/d`],
      ['Temperature', `${s.temp} °C, +1.5 kPa(g)`], ['Burner duty', `${fmt(m.duty, 1)} GJ/d`]]},
  U104:{t:'U-104 Hot cyclone and water-jacketed auger', s:'Cools pyrophoric carbon black below the 60 °C auto-ignition threshold before it meets ambient air and jet milling.',
    r:(m, s) => [['rCB out', `${fmt(m.rcb, 2)} t/d`], ['Cooling', `${s.temp} → 55 °C`], ['Pressure', '+1.0 kPa']]},
  U105:{t:'U-105 Two-stage shell-and-tube condenser', s:'Stage 1 at 180 °C takes heavy oil, stage 2 at 35 °C takes light oil. A gravity decanter separates the water.',
    r:(m) => [['TPO out', `${fmt(m.tpo, 2)} t/d`], ['Non-condensable gas', `${fmt(m.gas, 2)} t/d`], ['Condenser duty', `${fmt(m.qCond, 1)} GJ/d`], ['Cooling water', `${fmt(m.cw, 0)} m³/d at 10 K rise`]]},
  U106:{t:'U-106 Packed-bed NaOH wet scrubber', s:'A 5 wt% NaOH spray strips H₂S (H₂S + 2NaOH → Na₂S + 2H₂O) before the furnace. Unscrubbed, it burns to SO₂ (2H₂S + 3O₂ → 2SO₂ + 2H₂O).',
    r:(m) => [['Syngas treated', `${fmt(m.gas, 2)} t/d`], ['Syngas energy', `${fmt(m.syn, 1)} GJ/d`], ['H₂S removed', `${fmt(m.h2s, 1)} kg/d`],
      ['NaOH, stoichiometric', `${fmt(m.naohKg, 1)} kg/d`], ['SO₂ avoided', `${fmt(m.so2Kg, 1)} kg/d`]]}};

const state = {}; let unit = 'U101', yc, cc;
SLIDERS.forEach(s => {
  state[s.id] = s.v;
  $('sliders').insertAdjacentHTML('beforeend', `<label for="s-${s.id}">${s.label}: <output id="o-${s.id}">${s.v}</output> ${s.unit}
    <input type="range" id="s-${s.id}" min="${s.min}" max="${s.max}" step="${s.step}" value="${s.v}"></label>`);
  $('s-' + s.id).addEventListener('input', e => { state[s.id] = +e.target.value; $('o-' + s.id).textContent = e.target.value; update(); });
});

function initCharts() {
  if (typeof Chart === 'undefined') return;
  const css = getComputedStyle(document.documentElement);
  Chart.defaults.color = css.getPropertyValue('--mute').trim();
  Chart.defaults.borderColor = css.getPropertyValue('--line').trim();
  const temps = Array.from({length:41}, (_, i) => 400 + 5 * i);
  const line = (label, key, color, dash) => ({label, data:temps.map(T => yields(T)[key]), borderColor:color, backgroundColor:color,
    borderDash:dash, tension:.3, pointRadius:c => c.dataIndex === (state.temp - 400) / 5 ? 6 : 0});
  yc = new Chart($('yieldChart'), {type:'line', data:{labels:temps, datasets:[
    line('TPO oil', 'oil', '#d97706'), line('Recovered carbon black', 'rcb', '#64748b'),
    line('Syngas', 'gas', '#0d9488'), line('Steel (pre-extracted)', 'steel', '#94a3b8', [5, 4])]},
    options:{maintainAspectRatio:false, plugins:{title:{display:true, text:'Product yield vs kiln temperature (wt% of whole tyre)'}},
      scales:{x:{title:{display:true, text:'°C'}}, y:{min:0, title:{display:true, text:'wt%'}}}}});
  cc = new Chart($('cashflowChart'), {type:'bar', data:{labels:[], datasets:[{label:'Cumulative cash position (USD)', data:[]}]},
    options:{maintainAspectRatio:false, plugins:{legend:{display:false}, title:{display:true, text:'Cumulative after-tax cash position (USD)'}}}});
}

function renderUnit(m) {
  const u = UNITS[unit];
  $('unit-inspector').innerHTML = `<h3>${u.t}</h3><p>${u.s}</p><dl>${u.r(m, state).map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>`;
}

function update() {
  const m = model(state);
  $('kpi-tpo').textContent = `${fmt(m.tpo, 2)} t/d`;
  $('kpi-energy').textContent = `${fmt(m.ss, 1)}%`;
  $('kpi-ebitda').textContent = usd(m.ebitda);
  $('kpi-npv').textContent = usd(m.npv);
  $('kpi-payback').textContent = m.payback === null ? 'never' : `${fmt(m.payback, 2)} yrs`;
  $('kpi-irr').textContent = m.irr === null ? 'n/a' : `${fmt(m.irr * 100, 0)}%`;
  $('kpi-co2').textContent = `${fmt(m.co2)} t/yr`;
  $('kpi-capex').textContent = usd(m.capex);
  if (yc) yc.update('none');
  if (cc) {
    let run = 0; const cum = m.flows.map(c => run += c);
    cc.data.labels = cum.map((_, i) => 'Year ' + i);
    cc.data.datasets[0].data = cum;
    cc.data.datasets[0].backgroundColor = cum.map(v => v < 0 ? '#b91c1c' : '#0d9488');
    cc.update('none');
  }
  renderUnit(m);
}

document.querySelectorAll('.pfd-btn').forEach(b => b.addEventListener('click', () => {
  unit = b.dataset.unit;
  document.querySelectorAll('.pfd-btn').forEach(x => { const on = x === b; x.classList.toggle('active', on); x.setAttribute('aria-pressed', on); });
  renderUnit(model(state));
}));

function verify() {
  const el = $('verify'), set = (cls, txt) => { el.className = 'badge ' + cls; el.textContent = txt; };
  fetch('https://raw.githubusercontent.com/alkim8300-ops/waste-tyre-pyrolysis-simulator/main/data/baseline_10tpd_nairobi.json').then(r => r.json()).then(d => {
    const bad = d.scenarios.filter(s => {
      const m = model({feed:10, temp:s.temp_c, days:300, tpo:550, rcb:380});
      return Math.abs(m.ebitda - s.ebitda_usd_yr) > 25 || Math.abs(m.tpo - s.tpo_tpd) > 1e-3 || Math.abs(m.ss - s.self_sufficiency_pct) > .05;
    });
    bad.length ? set('fail', `Model mismatch in ${bad.length} of ${d.scenarios.length} Python baseline scenarios`)
               : set('ok', `JS engine matches Python baseline: ${d.scenarios.length}/${d.scenarios.length} scenarios`);
  }).catch(() => set('', 'Python baseline not loaded (serve the folder over HTTP to enable the check)'));
}

window.addEventListener('DOMContentLoaded', () => { initCharts(); update(); verify(); });
})();
