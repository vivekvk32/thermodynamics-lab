function calculateExperiment() {
    normalizeAllAirProps();
    const form = document.getElementById('calcForm');
    const formData = new FormData(form);
    const data = {};
    formData.forEach((value, key) => data[key] = value);

    const inputs = {};
    for (const key in data) {
        if (key !== 'slug') inputs[key] = data[key];
    }
    if (data.slug === 'natural-convection-vertical-tube') {
        inputs.observations = collectTrialsFromTable();
    }

    fetch('/api/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            slug: data.slug,
            inputs: inputs
        })
    })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                document.getElementById('resultsArea').classList.remove('d-none');
                document.getElementById('resultsPlaceholder').classList.add('d-none');

                // Render Steps
                const container = document.getElementById('stepsContainer');
                if (result.slug === 'natural-convection-vertical-tube' && Array.isArray(result.steps_by_trial)) {
                    container.innerHTML = result.steps_by_trial.map(trial => `
                        <div class="mb-3">
                            <h6>Trial ${trial.trial}</h6>
                            <ul class="list-group">${(trial.steps || []).map(s => `<li class="list-group-item">${s}</li>`).join('')}</ul>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = `<ul class="list-group">${result.steps.map(s => `<li class="list-group-item">${s}</li>`).join('')}</ul>`;
                }

                // Render warnings and trace
                renderWarnings(result.warnings || []);
                if (result.slug === 'natural-convection-vertical-tube') {
                    const traceContainer = document.getElementById('traceContainer');
                    if (traceContainer) traceContainer.innerHTML = '';
                } else {
                    renderTrace(result.trace_table || [], result.trace || {}, result.normalized || {});
                }
                renderTrialResults(result);
                renderExplanation(result);

                // Render Charts
                renderCharts(result);

                // Re-render MathJax for all updated content
                if (window.MathJax && window.MathJax.typesetPromise) {
                    window.MathJax.typesetPromise();
                }

                // Switch tab
                const triggerEl = document.querySelector('#expTabs button[data-bs-target="#calculations"]');
                const tab = new bootstrap.Tab(triggerEl);
                tab.show();
            } else {
                alert('Error: ' + result.error);
            }
        })
        .catch(error => console.error('Error:', error));
}

function fmtVal(value) {
    if (value === null || value === undefined || isNaN(value)) return '-';
    const num = Number(value);
    const abs = Math.abs(num);
    if (abs !== 0 && (abs < 1e-3 || abs >= 1e4)) return num.toExponential(3);
    return num.toFixed(4);
}

const AIR_PROPS_CONFIG = {
    rho: { name: 'rho_air', min: 0.5, max: 2.0 },
    cp: { name: 'cp_air', min: 900, max: 1200 },
    k: { name: 'k_air', min: 0.015, max: 0.05 },
    mu: { name: 'mu_air', min: 1.0e-5, max: 3.0e-5, sciPreview: true },
    nu: { name: 'nu_air', min: 1.0e-5, max: 3.0e-5, sciPreview: true },
    pr: { name: 'pr_air', min: 0.6, max: 0.9 },
};

const AIR_PROPS_PRESETS = {
    tf31558: {
        rho: 1.127,
        cp: 1007,
        k: 0.02662,
        mu: 1.918e-5,
        nu: 1.702e-5,
        pr: 0.7255,
    }
};

const SCI_FORMAT_ERROR = 'Accepted formats: 0.00001918, 1.918e-5, 1.918×10^-5 (x or * allowed).';
const SCI_TYPO_ERROR = 'Invalid format: use 1.918e-5 or 1.918×10^-5 (not 10e-5).';

function normalizeMinusSign(text) {
    return text.replace(/[−–]/g, '-');
}

function trimZeros(text) {
    return text.replace(/(\.\d*?[1-9])0+$/u, '$1').replace(/\.0+$/u, '');
}

function formatNormalized(value) {
    if (!Number.isFinite(value)) return '';
    const abs = Math.abs(value);
    if (abs !== 0 && (abs < 1e-3 || abs >= 1e4)) {
        return value.toExponential(3).replace('e+', 'e');
    }
    return trimZeros(value.toFixed(6));
}

function formatTimesTen(value) {
    if (!Number.isFinite(value)) return '-';
    if (value === 0) return '0';
    const exp = value.toExponential(3).replace('e+', 'e');
    const parts = exp.split('e');
    const mantissa = parts[0];
    const exponent = parts[1] || '0';
    return `${mantissa}&times;10<sup>${exponent}</sup>`;
}

function parseScientificInput(raw) {
    const text = String(raw ?? '').trim();
    if (!text) {
        return { value: null, normalized: '', error: null };
    }
    if (/(?:x|\*|×)\s*10e[+-]?\d+/i.test(text)) {
        return { value: null, normalized: '', error: SCI_TYPO_ERROR };
    }

    const normalized = normalizeMinusSign(text).replace(/×/g, 'x');
    const compact = normalized.replace(/\s+/g, '');
    const standardRe = /^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/u;
    if (standardRe.test(compact)) {
        const num = Number(compact);
        if (!Number.isFinite(num)) {
            return { value: null, normalized: '', error: SCI_FORMAT_ERROR };
        }
        return { value: num, normalized: formatNormalized(num), error: null };
    }

    const multRe = /^([+-]?(?:\d+\.?\d*|\.\d+))(?:x|\*)10\^?([+-]?\d+)$/iu;
    const match = compact.match(multRe);
    if (match) {
        const mantissa = Number(match[1]);
        const exponent = Number(match[2]);
        if (!Number.isFinite(mantissa) || !Number.isFinite(exponent)) {
            return { value: null, normalized: '', error: SCI_FORMAT_ERROR };
        }
        const num = mantissa * Math.pow(10, exponent);
        return { value: num, normalized: formatNormalized(num), error: null };
    }

    const powRe = /^10\^?([+-]?\d+)$/iu;
    const powMatch = compact.match(powRe);
    if (powMatch) {
        const exponent = Number(powMatch[1]);
        if (!Number.isFinite(exponent)) {
            return { value: null, normalized: '', error: SCI_FORMAT_ERROR };
        }
        const num = Math.pow(10, exponent);
        return { value: num, normalized: formatNormalized(num), error: null };
    }

    return { value: null, normalized: '', error: SCI_FORMAT_ERROR };
}

class ScientificNumberInput {
    constructor(wrapper, config) {
        this.wrapper = wrapper;
        this.config = config;
        this.input = wrapper.querySelector('.scientific-input');
        this.preview = wrapper.querySelector('.sci-preview');
        this.warning = wrapper.querySelector('.sci-warning');
        this.error = wrapper.querySelector('.sci-error');
        this.helper = wrapper.querySelector('.sci-helper');
        this.helperToggle = wrapper.querySelector('.sci-helper-toggle');
        this.mantissa = wrapper.querySelector('.sci-mantissa');
        this.exponent = wrapper.querySelector('.sci-exponent');
        this.applyBtn = wrapper.querySelector('.sci-apply');
        this.bind();
    }

    bind() {
        if (this.helperToggle && this.helper) {
            this.helperToggle.addEventListener('click', () => {
                this.helper.classList.toggle('d-none');
            });
        }
        if (this.applyBtn) {
            this.applyBtn.addEventListener('click', () => this.applyScientific());
        }
        if (this.input) {
            this.input.addEventListener('blur', () => this.normalize());
            this.input.addEventListener('input', () => this.refresh(false));
        }
    }

    applyScientific() {
        const mantissaVal = Number(this.mantissa?.value);
        const exponentVal = Number(this.exponent?.value);
        if (!Number.isFinite(mantissaVal) || !Number.isFinite(exponentVal)) {
            this.showError('Enter both mantissa and exponent.');
            return;
        }
        const value = mantissaVal * Math.pow(10, exponentVal);
        if (this.input) {
            this.input.value = formatNormalized(value);
        }
        this.refresh(true);
        updateAirPropsPreview();
    }

    normalize() {
        this.refresh(true);
        updateAirPropsPreview();
    }

    refresh(applyNormalized) {
        if (!this.input) return;
        const parsed = parseScientificInput(this.input.value);
        this.clearMessages();

        if (parsed.error) {
            this.showError(parsed.error);
            return;
        }

        if (parsed.value === null) {
            return;
        }

        if (applyNormalized) {
            this.input.value = parsed.normalized;
        }
        this.input.dataset.numericValue = String(parsed.value);

        if (this.config?.sciPreview && this.preview) {
            this.preview.innerHTML = `≈ ${formatTimesTen(parsed.value)}`;
            this.preview.classList.remove('d-none');
        }

        if (this.config?.min !== undefined && this.config?.max !== undefined) {
            if (parsed.value < this.config.min || parsed.value > this.config.max) {
                this.showWarning(`Typical range ${this.config.min}–${this.config.max}. Check units / exponent.`);
            }
        }
    }

    showError(message) {
        if (!this.error) return;
        this.error.textContent = message;
        this.error.classList.remove('d-none');
    }

    showWarning(message) {
        if (!this.warning) return;
        this.warning.textContent = message;
        this.warning.classList.remove('d-none');
    }

    clearMessages() {
        if (this.error) {
            this.error.textContent = '';
            this.error.classList.add('d-none');
        }
        if (this.warning) {
            this.warning.textContent = '';
            this.warning.classList.add('d-none');
        }
        if (this.preview) {
            this.preview.textContent = '';
            this.preview.classList.add('d-none');
        }
    }
}

function updateAirPropsPreview() {
    const previewContainer = document.getElementById('airPropsPreview');
    if (!previewContainer) return;
    Object.entries(AIR_PROPS_CONFIG).forEach(([key, config]) => {
        const input = document.querySelector(`input[name="${config.name}"]`);
        const target = previewContainer.querySelector(`[data-preview="${key}"]`);
        if (!input || !target) return;
        const parsed = parseScientificInput(input.value);
        if (parsed.value === null) {
            target.textContent = '-';
            return;
        }
        const normalized = formatNormalized(parsed.value);
        if (config.sciPreview) {
            target.innerHTML = `${normalized} <span class="text-muted">(${formatTimesTen(parsed.value)})</span>`;
        } else {
            target.textContent = normalized;
        }
    });
}

function applyAirPropsValues(values) {
    Object.entries(AIR_PROPS_CONFIG).forEach(([key, config]) => {
        const input = document.querySelector(`input[name="${config.name}"]`);
        if (!input || values[key] === undefined) return;
        input.value = formatNormalized(values[key]);
        input.dispatchEvent(new Event('blur'));
    });
    updateAirPropsPreview();
}

function parsePasteRow(text) {
    const cleaned = String(text ?? '').replace(/[\t;]+/g, ' ').trim();
    if (!cleaned) return { values: null, error: 'Paste a handbook row first.' };
    const parts = cleaned.split(/[\s,]+/u).filter(Boolean);
    if (parts.length < 6) {
        return { values: null, error: 'Paste 6 values: rho, Cp, k, mu, nu, Pr.' };
    }
    const keys = ['rho', 'cp', 'k', 'mu', 'nu', 'pr'];
    const values = {};
    for (let i = 0; i < keys.length; i += 1) {
        const parsed = parseScientificInput(parts[i]);
        if (parsed.error || parsed.value === null) {
            return { values: null, error: `Invalid ${keys[i]} value. ${parsed.error || SCI_FORMAT_ERROR}` };
        }
        values[keys[i]] = parsed.value;
    }
    return { values, error: null };
}

function initAirPropsInputs() {
    const panel = document.querySelector('.air-props-panel');
    if (!panel) return;

    panel.querySelectorAll('.air-prop-field').forEach((field) => {
        const key = field.dataset.prop;
        const config = AIR_PROPS_CONFIG[key];
        if (!config) return;
        new ScientificNumberInput(field, config);
    });

    const presetSelect = document.getElementById('airPropsPreset');
    if (presetSelect) {
        presetSelect.addEventListener('change', () => {
            const preset = AIR_PROPS_PRESETS[presetSelect.value];
            if (preset) {
                applyAirPropsValues(preset);
            }
        });
    }

    const pasteInput = document.getElementById('airPropsPaste');
    const pasteApply = document.getElementById('airPropsPasteApply');
    const pasteError = document.getElementById('airPropsPasteError');
    if (pasteApply && pasteInput) {
        const applyPaste = () => {
            if (!pasteInput.value.trim()) {
                if (pasteError) {
                    pasteError.textContent = '';
                    pasteError.classList.add('d-none');
                }
                return;
            }
            const { values, error } = parsePasteRow(pasteInput.value);
            if (error) {
                if (pasteError) {
                    pasteError.textContent = error;
                    pasteError.classList.remove('d-none');
                }
                return;
            }
            if (pasteError) {
                pasteError.textContent = '';
                pasteError.classList.add('d-none');
            }
            applyAirPropsValues(values);
        };
        pasteApply.addEventListener('click', applyPaste);
        pasteInput.addEventListener('blur', applyPaste);
    }

    updateAirPropsPreview();
}

function normalizeAllAirProps() {
    const panel = document.querySelector('.air-props-panel');
    if (!panel) return;
    panel.querySelectorAll('.air-prop-field').forEach((field) => {
        const input = field.querySelector('.scientific-input');
        if (!input) return;
        input.dispatchEvent(new Event('blur'));
    });
}

function renderWarnings(warnings) {
    const area = document.getElementById('warningsArea');
    if (!warnings || warnings.length === 0) {
        area.classList.add('d-none');
        area.innerHTML = '';
        return;
    }
    area.classList.remove('d-none');
    area.innerHTML = `<strong>Warnings:</strong><ul class="mb-0">${warnings.map(w => `<li>${w}</li>`).join('')}</ul>`;
}

function renderTrialResults(result) {
    const container = document.getElementById('trialResultsContainer');
    if (!container) return;
    const trials = result?.trial_results || result?.trials;
    if (!result || result.slug !== 'natural-convection-vertical-tube' || !Array.isArray(trials)) {
        container.innerHTML = '';
        return;
    }

    const rows = trials.map(trial => `
        <tr>
            <td>${trial.trial}</td>
            <td>${fmtVal(trial.q)}</td>
            <td>${fmtVal(trial.ts)}</td>
            <td>${fmtVal(trial.ta)}</td>
            <td>${fmtVal(trial.gr)}</td>
            <td>${fmtVal(trial.ra)}</td>
            <td>${fmtVal(trial.nu)}</td>
            <td>${fmtVal(trial.h_exp)}</td>
            <td>${fmtVal(trial.h_theoretical)}</td>
        </tr>
    `).join('');

    const summaryRows = trials.map(trial => `
        <div>Trial ${trial.trial}: h_exp = ${fmtVal(trial.h_exp)} W/m²K, h_theoretical = ${fmtVal(trial.h_theoretical)} W/m²K</div>
    `).join('');
    const overall = result.final_results?.optional_overall;
    const overallHtml = overall ? `
        <div class="mt-2 text-muted">
            Mean h_exp = ${fmtVal(overall.mean_h_exp)}, Mean h_theoretical = ${fmtVal(overall.mean_h_theoretical)}
        </div>
    ` : '';

    container.innerHTML = `
        <h5>Results (Per Trial)</h5>
        <div class="table-responsive">
            <table class="table table-sm table-bordered">
                <thead>
                    <tr>
                        <th>Trial</th>
                        <th>Q (W)</th>
                        <th>Ts (°C)</th>
                        <th>Ta (°C)</th>
                        <th>Gr</th>
                        <th>Ra</th>
                        <th>Nu</th>
                        <th>h_exp (W/m²K)</th>
                        <th>h_theoretical (W/m²K)</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
        <div class="mt-2"><strong>Result:</strong></div>
        ${summaryRows}
        ${overallHtml}
    `;
}

function renderExplanation(result) {
    const container = document.getElementById('explanationContainer');
    if (!container) return;
    if (!result || result.slug !== 'natural-convection-vertical-tube') {
        container.innerHTML = '';
        return;
    }

    const blocks = Array.isArray(result.explanation_blocks) ? result.explanation_blocks : [];
    const finalExplanation = result.final_explanation || '';

    const trialHtml = blocks.map((block, idx) => `
        <div class="mb-3">
            ${block}
        </div>
    `).join('');

    container.innerHTML = `
        <div class="card">
            <div class="card-header">
                What do these results mean?
            </div>
            <div class="card-body">
                ${trialHtml}
                <hr>
                ${finalExplanation}
            </div>
        </div>
    `;
}

function renderTrace(traceTable, trace, normalized) {
    const container = document.getElementById('traceContainer');
    if (!container) return;

    if (Array.isArray(traceTable) && traceTable.length > 0) {
        const body = traceTable.map(r => `<tr><td>${r.label}</td><td>${fmtVal(r.value)}</td><td>${r.unit || '-'}</td></tr>`).join('');
        container.innerHTML = `
            <table class="table table-sm table-bordered">
                <thead><tr><th>Parameter</th><th>Value</th><th>Unit</th></tr></thead>
                <tbody>${body}</tbody>
            </table>
        `;
        return;
    }

    const rows = [
        ['Vdot', normalized.vdot_m3s, 'm^3/s'],
        ['m_dot', normalized.m_dot, 'kg/s'],
        ['Qw', trace.qw, 'W'],
        ['Area', trace.area, 'm^2'],
        ['(dT/dx)_xx', trace.grads ? trace.grads[0] : null, 'K/m'],
        ['(dT/dx)_yy', trace.grads ? trace.grads[1] : null, 'K/m'],
        ['(dT/dx)_zz', trace.grads ? trace.grads[2] : null, 'K/m'],
        ['ln(ro/ri)', trace.ln_ro_ri, '-'],
        ['Loss_xx', trace.loss_xx, 'W'],
        ['Loss_yy', trace.loss_yy, 'W'],
        ['Loss_zz', trace.loss_zz, 'W'],
        ['Qxx', trace.qs ? trace.qs[0] : null, 'W'],
        ['Qyy', trace.qs ? trace.qs[1] : null, 'W'],
        ['Qzz', trace.qs ? trace.qs[2] : null, 'W'],
        ['Kxx', trace.ks ? trace.ks[0] : null, 'W/mK'],
        ['Kyy', trace.ks ? trace.ks[1] : null, 'W/mK'],
        ['Kzz', trace.ks ? trace.ks[2] : null, 'W/mK'],
        ['K_avg', trace.k_avg, 'W/mK'],
    ];

    const body = rows.map(r => `<tr><td>${r[0]}</td><td>${fmtVal(r[1])}</td><td>${r[2]}</td></tr>`).join('');
    container.innerHTML = `
        <table class="table table-sm table-bordered">
            <thead><tr><th>Parameter</th><th>Value</th><th>Unit</th></tr></thead>
            <tbody>${body}</tbody>
        </table>
    `;
}

let myChart = null;
let comparisonChart = null;

function renderCharts(result) {
    const data = result.graphs || {};
    const tempCanvas = document.getElementById('tempDistChart');
    const compCanvas = document.getElementById('comparisonChart');
    const ctx = tempCanvas.getContext('2d');
    if (myChart) myChart.destroy();
    if (comparisonChart) comparisonChart.destroy();

    if (data.type === 'natural_convection') {
        const labels = data.temp_labels || ['T1', 'T2', 'T3', 'T4', 'T5', 'T6'];
        const trialSeries = Array.isArray(data.trials) ? data.trials : [];
        const datasets = trialSeries.map((trial, idx) => ({
            label: trial.label || `Trial ${idx + 1}`,
            data: trial.temps || [],
            borderColor: idx === 0 ? 'rgb(255, 99, 132)' : 'rgb(54, 162, 235)',
            tension: 0.1
        }));
        myChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                scales: {
                    y: { beginAtZero: false, title: { display: true, text: 'Temperature (C)' } },
                    x: { title: { display: true, text: 'Thermocouples' } }
                }
            }
        });

        if (compCanvas) {
            compCanvas.style.display = 'block';
            const compCtx = compCanvas.getContext('2d');
            const trialLabels = trialSeries.map((trial, idx) => trial.label || `Trial ${idx + 1}`);
            const hExp = trialSeries.map(trial => trial.h_exp || 0);
            const hTheoretical = trialSeries.map(trial => trial.h_theoretical || 0);
            comparisonChart = new Chart(compCtx, {
                type: 'bar',
                data: {
                    labels: trialLabels,
                    datasets: [{
                        label: 'h_exp (W/m^2K)',
                        data: hExp,
                        backgroundColor: 'rgba(54, 162, 235, 0.6)'
                    }, {
                        label: 'h_theoretical (W/m^2K)',
                        data: hTheoretical,
                        backgroundColor: 'rgba(255, 159, 64, 0.6)'
                    }]
                },
                options: {
                    scales: {
                        y: { beginAtZero: true, title: { display: true, text: 'h (W/m^2K)' } }
                    }
                }
            });
        }
        return;
    }

    if (compCanvas) compCanvas.style.display = 'none';
    myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['T1', 'T2', 'T3', 'T4', 'T5'],
            datasets: [{
                label: 'Temperature Distribution (C)',
                data: data.rod_temps || [],
                borderColor: 'rgb(255, 99, 132)',
                tension: 0.1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: false,
                    title: { display: true, text: 'Temperature (C)' }
                },
                x: {
                    title: { display: true, text: 'Points along rod' }
                }
            }
        }
    });
}

function updateSim() {
    const slugInput = document.querySelector('input[name="slug"]');
    const slug = slugInput ? slugInput.value : 'therm-conductivity-metal-rod';

    if (slug === 'natural-convection-vertical-tube') {
        const q = parseFloat(document.getElementById('simQ').value || 100);
        const deltaT = parseFloat(document.getElementById('simDeltaT').value || 30);
        const dTube = parseFloat(document.getElementById('simDTube').value || 0.038);
        const lTube = parseFloat(document.getElementById('simLTube').value || 0.5);

        document.getElementById('simQVal').innerText = q;
        document.getElementById('simDeltaTVal').innerText = deltaT;

        fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ slug: slug, q: q, delta_t: deltaT, d_tube: dTube, l_tube: lTube })
        })
            .then(res => res.json())
            .then(data => {
                renderSimChart(data.q, data.h, 'Power (W)', 'h (W/m^2K)');
            });
        return;
    }

    const flow = document.getElementById('simFlow').value;
    const heat = document.getElementById('simHeat').value;

    document.getElementById('simFlowVal').innerText = flow;
    document.getElementById('simHeatVal').innerText = heat;

    fetch('/api/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug: slug, flow: flow, watts: heat })
    })
        .then(res => res.json())
        .then(data => {
            renderSimChart(data.x, data.temps, 'Distance (m)', 'Temp C');
        });
}

let simChart = null;
function renderSimChart(labels, data, xLabel, yLabel) {
    const ctx = document.getElementById('simChart').getContext('2d');
    if (simChart) simChart.destroy();

    const lbls = labels.map(x => {
        if (typeof x === 'number') return x.toFixed(2);
        return x;
    });

    simChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: lbls,
            datasets: [{
                label: yLabel || 'Simulated',
                data: data,
                borderColor: 'rgb(54, 162, 235)',
                borderDash: [5, 5],
                fill: false
            }]
        },
        options: {
            animation: { duration: 0 },
            scales: {
                y: { title: { display: true, text: yLabel || 'Value' } },
                x: { title: { display: true, text: xLabel || 'X' } }
            }
        }
    });
}

function saveRun() {
    normalizeAllAirProps();
    const form = document.getElementById('calcForm');
    const formData = new FormData(form);
    const data = {};
    formData.forEach((value, key) => data[key] = value);

    if (data.slug === 'natural-convection-vertical-tube') {
        data.observations = collectTrialsFromTable();
    }

    fetch('/api/save_run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            slug: data.slug,
            formData: data
        })
    })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                alert('Run saved successfully! Run ID: ' + result.id);
            } else {
                alert('Error saving run: ' + result.error);
            }
        })
        .catch(error => console.error('Error:', error));
}

function generatePDF() {
    normalizeAllAirProps();
    // 1. Get the chart image
    const canvas = document.getElementById('tempDistChart');
    const dataURL = canvas ? canvas.toDataURL('image/png') : '';
    const compCanvas = document.getElementById('comparisonChart');
    const compURL = compCanvas && compCanvas.style.display !== 'none' ? compCanvas.toDataURL('image/png') : '';

    // 2. Populate the hidden PDF form
    const pdfForm = document.getElementById('pdfForm');
    const calcForm = document.getElementById('calcForm');
    const graphInput = document.getElementById('graph_img_input');

    // Clear old inputs from pdfForm except the graph one
    // Actually easier to just append clones of the inputs
    pdfForm.innerHTML = '';

    // Add graph input back
    const newGraphInput = document.createElement('input');
    newGraphInput.type = 'hidden';
    newGraphInput.name = 'graph_img';
    newGraphInput.value = dataURL;
    pdfForm.appendChild(newGraphInput);

    if (compURL) {
        const compInput = document.createElement('input');
        compInput.type = 'hidden';
        compInput.name = 'graph_img_2';
        compInput.value = compURL;
        pdfForm.appendChild(compInput);
    }

    // Include observations JSON for multi-trial experiments
    const slugInput = calcForm.querySelector('input[name="slug"]');
    const slug = slugInput ? slugInput.value : '';
    if (slug === 'natural-convection-vertical-tube') {
        const obsInput = document.createElement('input');
        obsInput.type = 'hidden';
        obsInput.name = 'observations';
        obsInput.value = JSON.stringify(collectTrialsFromTable());
        pdfForm.appendChild(obsInput);
    }

    // Clone all inputs from calcForm
    new FormData(calcForm).forEach((value, key) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = key;
        input.value = value;
        pdfForm.appendChild(input);
    });

    // 3. Submit
    pdfForm.submit();
}

function updateAirPropsVisibility() {
    const modeSelect = document.querySelector('select[name="air_props_mode"]');
    if (!modeSelect) return;
    const isManual = modeSelect.value === 'manual';
    document.querySelectorAll('.field-row[data-prop-group=\"air_props_manual\"]').forEach(row => {
        row.style.display = isManual ? '' : 'none';
    });
}

function collectTrialsFromTable() {
    const tbody = document.getElementById('trialTableBody');
    if (!tbody) return [];
    const rows = Array.from(tbody.querySelectorAll('tr'));
    return rows.map((row, idx) => {
        const trial = parseInt(row.dataset.trial || (idx + 1), 10);
        const getVal = (name) => {
            const input = row.querySelector(`input[name="${name}"]`);
            if (!input) return null;
            if (input.value === '') return null;
            const num = parseFloat(input.value);
            return Number.isNaN(num) ? null : num;
        };
        return {
            trial: trial,
            v: getVal(`trial_${trial}_v`),
            i: getVal(`trial_${trial}_i`),
            t1: getVal(`trial_${trial}_t1`),
            t2: getVal(`trial_${trial}_t2`),
            t3: getVal(`trial_${trial}_t3`),
            t4: getVal(`trial_${trial}_t4`),
            t5: getVal(`trial_${trial}_t5`),
            t6: getVal(`trial_${trial}_t6`),
            t7: getVal(`trial_${trial}_t7`)
        };
    });
}

function addTrialRow() {
    const tbody = document.getElementById('trialTableBody');
    if (!tbody) return;
    const trial = tbody.querySelectorAll('tr').length + 1;
    const row = document.createElement('tr');
    row.dataset.trial = trial;
    row.innerHTML = `
        <td>${trial}</td>
        <td><input type="number" step="any" class="form-control form-control-sm" name="trial_${trial}_v" required></td>
        <td><input type="number" step="any" class="form-control form-control-sm" name="trial_${trial}_i" required></td>
        <td><input type="number" step="any" class="form-control form-control-sm" name="trial_${trial}_t1" required></td>
        <td><input type="number" step="any" class="form-control form-control-sm" name="trial_${trial}_t2" required></td>
        <td><input type="number" step="any" class="form-control form-control-sm" name="trial_${trial}_t3" required></td>
        <td><input type="number" step="any" class="form-control form-control-sm" name="trial_${trial}_t4" required></td>
        <td><input type="number" step="any" class="form-control form-control-sm" name="trial_${trial}_t5" required></td>
        <td><input type="number" step="any" class="form-control form-control-sm" name="trial_${trial}_t6" required></td>
        <td><input type="number" step="any" class="form-control form-control-sm" name="trial_${trial}_t7" required></td>
    `;
    tbody.appendChild(row);
}

function removeTrialRow() {
    const tbody = document.getElementById('trialTableBody');
    if (!tbody) return;
    const rows = tbody.querySelectorAll('tr');
    if (rows.length <= 1) return;
    tbody.removeChild(rows[rows.length - 1]);
}

document.addEventListener('DOMContentLoaded', () => {
    const modeSelect = document.querySelector('select[name="air_props_mode"]');
    if (modeSelect) {
        modeSelect.addEventListener('change', updateAirPropsVisibility);
        updateAirPropsVisibility();
    }
    initAirPropsInputs();
    if (document.getElementById('simChart')) {
        updateSim();
    }
    window.addEventListener('beforeprint', () => {
        if (window.MathJax && window.MathJax.typesetPromise) {
            window.MathJax.typesetPromise();
        }
    });
});
