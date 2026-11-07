/* Performance-over-time chart for the player and team pages.
 *
 *   TrendChart.mount(element, data, storageKey)
 *
 * data is what trends.py builds: {labels, metrics}. A dropdown picks the
 * metric; the chart is an SVG line chart with a crosshair tooltip, a legend,
 * end-of-line labels and a table view. Series roles:
 *   primary    colored, in fixed palette order
 *   context    other teams in the division: thin and gray, named on hover
 *   reference  a tier average: dashed gray
 */
(function () {
    'use strict';

    // Categorical slots in fixed order (validated palette, light surface)
    var SERIES_COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100'];
    var CONTEXT_COLOR = '#c9c7bf';
    var REFERENCE_COLOR = '#898781';
    var SVG_NS = 'http://www.w3.org/2000/svg';
    var HEIGHT = 300;

    function el(tag, attrs, parent) {
        var node = document.createElementNS(SVG_NS, tag);
        for (var k in attrs) node.setAttribute(k, attrs[k]);
        if (parent) parent.appendChild(node);
        return node;
    }

    function html(tag, className, parent, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        if (parent) parent.appendChild(node);
        return node;
    }

    function ordinal(n) {
        var s = ['th', 'st', 'nd', 'rd'], v = n % 100;
        return n + (s[(v - 20) % 10] || s[v] || s[0]);
    }

    function formatter(fmt) {
        return function (v) {
            if (v === null || v === undefined) return '—';
            switch (fmt) {
                case 'int': return String(Math.round(v));
                case 'dec1': return v.toFixed(1);
                case 'dec2': return v.toFixed(2);
                case 'signed1': return (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(1);
                case 'signed3': return (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(3);
                case 'pct': return (v * 100).toFixed(1) + '%';
                case 'rank': return ordinal(Math.round(v));
                default: return String(v);
            }
        };
    }

    function axisFormatter(fmt) {
        if (fmt === 'pct') return function (v) { return Math.round(v * 100) + '%'; };
        if (fmt === 'rank') return function (v) { return ordinal(Math.round(v)); };
        if (fmt === 'signed1' || fmt === 'signed3') {
            return function (v) { return (v > 0 ? '+' : v < 0 ? '−' : '') + trim(Math.abs(v)); };
        }
        return trim;
    }

    function trim(v) {
        return String(parseFloat(v.toFixed(4)));
    }

    // Round tick steps (1, 2, 5 x 10^k) covering [lo, hi]
    function niceTicks(lo, hi, count) {
        if (lo === hi) { lo -= 1; hi += 1; }
        var raw = (hi - lo) / count;
        var mag = Math.pow(10, Math.floor(Math.log10(raw)));
        var step = [1, 2, 5, 10].map(function (m) { return m * mag; })
            .find(function (s) { return s >= raw; });
        var start = Math.floor(lo / step) * step;
        var end = Math.ceil(hi / step) * step;
        var ticks = [];
        for (var t = start; t <= end + step / 2; t += step) ticks.push(parseFloat(t.toFixed(10)));
        return ticks;
    }

    function rankTicks(lo, hi) {
        var span = hi - lo;
        var step = span <= 8 ? 1 : span <= 16 ? 2 : span <= 40 ? 5 : Math.ceil(span / 8 / 10) * 10;
        var ticks = [lo];
        for (var t = step; t <= hi; t += step) if (t > lo) ticks.push(t);
        if (ticks[ticks.length - 1] !== hi && hi - ticks[ticks.length - 1] >= step * 0.75) ticks.push(hi);
        return ticks;
    }

    function storageGet(key) {
        try { return window.localStorage.getItem(key); } catch (e) { return null; }
    }

    function storageSet(key, value) {
        try { window.localStorage.setItem(key, value); } catch (e) { /* private mode */ }
    }

    function mount(root, data, storageKey) {
        if (!root || !data || !data.metrics || !data.metrics.length) return;
        var labels = data.labels;
        var metrics = data.metrics;
        var byId = {};
        metrics.forEach(function (m) { byId[m.id] = m; });

        root.classList.add('trend-chart');
        root.textContent = '';

        // Controls: metric dropdown (grouped) and its description
        var controls = html('div', 'trend-controls', root);
        var selectId = 'trend-select-' + Math.random().toString(36).slice(2, 8);
        var label = html('label', 'trend-select-label', controls, 'Show');
        label.setAttribute('for', selectId);
        var select = html('select', 'trend-select', controls);
        select.id = selectId;
        var groups = {};
        metrics.forEach(function (m) {
            if (!groups[m.group]) {
                groups[m.group] = html('optgroup', null, select);
                groups[m.group].label = m.group;
            }
            var opt = html('option', null, groups[m.group], m.label);
            opt.value = m.id;
        });
        var description = html('p', 'trend-description', root);
        var legend = html('div', 'trend-legend', root);
        var plot = html('div', 'trend-plot', root);
        var tooltip = html('div', 'trend-tooltip', plot);
        tooltip.setAttribute('role', 'status');
        var details = html('details', 'trend-table', root);
        html('summary', null, details, 'Show as table');
        var tableWrap = html('div', 'trend-table-wrap', details);

        var current = byId[storageGet(storageKey)] || metrics[0];
        select.value = current.id;
        select.addEventListener('change', function () {
            current = byId[select.value];
            storageSet(storageKey, current.id);
            render();
        });

        var resizeTimer;
        window.addEventListener('resize', function () {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(render, 120);
        });

        render();

        function seriesStyle(metric) {
            var slot = 0;
            return metric.series.map(function (s) {
                if (s.role === 'context') return { color: CONTEXT_COLOR, width: 1.5, dash: null, dots: false };
                if (s.role === 'reference') return { color: REFERENCE_COLOR, width: 1.5, dash: '5 4', dots: false };
                return { color: SERIES_COLORS[slot++ % SERIES_COLORS.length], width: 2, dash: null, dots: true };
            });
        }

        function render() {
            var metric = current;
            var fmt = formatter(metric.format);
            var styles = seriesStyle(metric);
            description.textContent = metric.description;
            renderLegend(metric, styles);
            renderTable(metric, fmt);
            renderPlot(metric, styles, fmt);
        }

        function renderLegend(metric, styles) {
            legend.textContent = '';
            var shownContext = false;
            metric.series.forEach(function (s, i) {
                if (s.role === 'context') {
                    if (shownContext) return;
                    shownContext = true;
                }
                var item = html('span', 'trend-legend-item', legend);
                var key = html('span', 'trend-legend-key', item);
                key.style.borderTopColor = styles[i].color;
                key.style.borderTopStyle = styles[i].dash ? 'dashed' : 'solid';
                html('span', null, item, s.role === 'context' ? 'Rest of division' : s.name);
            });
            // A lone series is named by the dropdown; no legend needed
            legend.style.display = metric.series.length > 1 ? '' : 'none';
        }

        function renderTable(metric, fmt) {
            tableWrap.textContent = '';
            var table = html('table', null, tableWrap);
            var head = html('tr', null, html('thead', null, table));
            html('th', null, head, 'Week');
            metric.series.forEach(function (s) { html('th', null, head, s.name); });
            var body = html('tbody', null, table);
            labels.forEach(function (lab, i) {
                var row = html('tr', null, body);
                html('td', null, row, lab);
                metric.series.forEach(function (s) { html('td', null, row, fmt(s.values[i])); });
            });
        }

        function renderPlot(metric, styles, fmt) {
            var oldSvg = plot.querySelector('svg');
            if (oldSvg) plot.removeChild(oldSvg);
            tooltip.style.display = 'none';

            var width = Math.max(plot.clientWidth, 280);
            var primaryCount = metric.series.filter(function (s) { return s.role !== 'context'; }).length;
            var directLabels = width >= 520 && primaryCount <= 4;
            var margin = { top: 14, right: directLabels ? 96 : 16, bottom: 30, left: 52 };
            var innerW = width - margin.left - margin.right;
            var innerH = HEIGHT - margin.top - margin.bottom;
            var n = labels.length;

            // y domain from the data (or fixed, for ranks)
            var values = [];
            metric.series.forEach(function (s) {
                s.values.forEach(function (v) { if (v !== null && v !== undefined) values.push(v); });
            });
            var lo, hi, ticks;
            if (metric.domain) {
                lo = metric.domain[0]; hi = metric.domain[1];
                ticks = metric.format === 'rank' ? rankTicks(lo, hi) : niceTicks(lo, hi, 5);
            } else if (metric.format === 'rank') {
                // Ranks without a fixed field size: 1st down to the worst shown
                lo = 1;
                hi = Math.max(2, values.length ? Math.max.apply(null, values) : 2);
                ticks = rankTicks(lo, hi);
                hi = Math.max(hi, ticks[ticks.length - 1]);
            } else {
                lo = values.length ? Math.min.apply(null, values) : 0;
                hi = values.length ? Math.max.apply(null, values) : 1;
                if (metric.zero_line) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
                ticks = niceTicks(lo, hi, 5);
                lo = ticks[0]; hi = ticks[ticks.length - 1];
            }

            function x(i) { return margin.left + (n === 1 ? innerW / 2 : i * innerW / (n - 1)); }
            function y(v) {
                var t = (v - lo) / (hi - lo || 1);
                return margin.top + (metric.invert ? t : 1 - t) * innerH;
            }

            var svg = el('svg', {
                width: width, height: HEIGHT, viewBox: '0 0 ' + width + ' ' + HEIGHT,
                role: 'img', tabindex: '0',
                'aria-label': metric.label + ' by week. Use the arrow keys to read values.'
            });
            plot.insertBefore(svg, tooltip);

            // Grid and y axis
            var axisFmt = axisFormatter(metric.format);
            var grid = el('g', { class: 'trend-grid' }, svg);
            ticks.forEach(function (t) {
                var isZero = metric.zero_line && t === 0;
                el('line', {
                    x1: margin.left, x2: margin.left + innerW, y1: y(t), y2: y(t),
                    stroke: isZero ? '#c3c2b7' : '#e1e0d9', 'stroke-width': 1
                }, grid);
                var tl = el('text', {
                    x: margin.left - 8, y: y(t), 'text-anchor': 'end', 'dominant-baseline': 'middle',
                    class: 'trend-axis-text'
                }, grid);
                tl.textContent = axisFmt(t);
            });

            // x axis: thin out labels so they never collide
            var every = Math.max(1, Math.ceil(n / Math.max(1, Math.floor(innerW / 34))));
            labels.forEach(function (lab, i) {
                if (i % every !== 0 && i !== n - 1) return;
                if (i !== n - 1 && n - 1 - i < every && (n - 1) % every !== 0) return;
                var t = el('text', {
                    x: x(i), y: margin.top + innerH + 20, 'text-anchor': 'middle', class: 'trend-axis-text'
                }, grid);
                t.textContent = lab;
            });
            var xTitle = el('text', {
                x: margin.left, y: margin.top + innerH + 20, 'text-anchor': 'end',
                class: 'trend-axis-text', dx: -8
            }, grid);
            xTitle.textContent = 'Wk';

            // Lines: context first so the highlighted series sits on top
            var order = metric.series.map(function (s, i) { return i; });
            var rolePriority = { context: 0, reference: 1, primary: 2 };
            order.sort(function (a, b) {
                return rolePriority[metric.series[a].role] - rolePriority[metric.series[b].role];
            });
            var linesG = el('g', null, svg);
            order.forEach(function (si) {
                var s = metric.series[si], st = styles[si];
                var d = '', pen = false;
                s.values.forEach(function (v, i) {
                    if (v === null || v === undefined) { pen = false; return; }
                    d += (pen ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(v).toFixed(1);
                    pen = true;
                });
                if (d) {
                    var attrs = {
                        d: d, fill: 'none', stroke: st.color, 'stroke-width': st.width,
                        'stroke-linejoin': 'round', 'stroke-linecap': 'round'
                    };
                    if (st.dash) attrs['stroke-dasharray'] = st.dash;
                    el('path', attrs, linesG);
                }
                if (st.dots) {
                    s.values.forEach(function (v, i) {
                        if (v === null || v === undefined) return;
                        el('circle', {
                            cx: x(i), cy: y(v), r: 3, fill: st.color, stroke: '#fff', 'stroke-width': 1.5
                        }, linesG);
                    });
                }
            });

            // End labels for the colored and reference series, pushed apart
            if (directLabels) {
                var ends = [];
                metric.series.forEach(function (s, si) {
                    if (s.role === 'context') return;
                    for (var i = s.values.length - 1; i >= 0; i--) {
                        if (s.values[i] !== null && s.values[i] !== undefined) {
                            ends.push({ name: s.name, y: y(s.values[i]), x: x(i), si: si });
                            break;
                        }
                    }
                });
                ends.sort(function (a, b) { return a.y - b.y; });
                for (var k = 1; k < ends.length; k++) {
                    if (ends[k].y - ends[k - 1].y < 14) ends[k].y = ends[k - 1].y + 14;
                }
                var overflow = ends.length ? ends[ends.length - 1].y - (margin.top + innerH) : 0;
                if (overflow > 0) ends.forEach(function (e) { e.y -= overflow; });
                ends.forEach(function (e) {
                    var t = el('text', {
                        x: margin.left + innerW + 8, y: e.y, 'dominant-baseline': 'middle',
                        class: 'trend-end-label'
                    }, svg);
                    t.textContent = e.name.length > 13 ? e.name.slice(0, 12) + '…' : e.name;
                });
            }

            // Crosshair and tooltip
            var hover = el('g', { visibility: 'hidden' }, svg);
            var cross = el('line', {
                y1: margin.top, y2: margin.top + innerH, stroke: '#898781', 'stroke-width': 1
            }, hover);
            var hoverDots = metric.series.map(function (s, si) {
                if (s.role === 'context') return null;
                return el('circle', {
                    r: 4.5, fill: styles[si].color, stroke: '#fff', 'stroke-width': 2
                }, hover);
            });
            var hit = el('rect', {
                x: margin.left - 12, y: margin.top, width: innerW + 24, height: innerH,
                fill: 'transparent'
            }, svg);

            var active = null;
            function show(i) {
                active = i;
                var cx = x(i);
                hover.setAttribute('visibility', 'visible');
                cross.setAttribute('x1', cx);
                cross.setAttribute('x2', cx);
                metric.series.forEach(function (s, si) {
                    var dot = hoverDots[si];
                    if (!dot) return;
                    var v = s.values[i];
                    if (v === null || v === undefined) { dot.setAttribute('visibility', 'hidden'); return; }
                    dot.setAttribute('visibility', 'visible');
                    dot.setAttribute('cx', cx);
                    dot.setAttribute('cy', y(v));
                });

                tooltip.textContent = '';
                html('div', 'trend-tooltip-title', tooltip, 'Week ' + labels[i]);
                var rows = metric.series.map(function (s, si) { return { s: s, si: si, v: s.values[i] }; });
                // With division rivals, list everyone best first: a standings snapshot
                if (metric.series.some(function (s) { return s.role === 'context'; })) {
                    rows.sort(function (a, b) {
                        var av = a.v === null ? -Infinity : a.v, bv = b.v === null ? -Infinity : b.v;
                        return metric.invert ? av - bv : bv - av;
                    });
                }
                rows.forEach(function (r) {
                    var row = html('div', 'trend-tooltip-row' +
                        (r.s.role === 'context' ? ' is-context' : ''), tooltip);
                    var key = html('span', 'trend-tooltip-key', row);
                    key.style.borderTopColor = styles[r.si].color;
                    key.style.borderTopStyle = styles[r.si].dash ? 'dashed' : 'solid';
                    html('span', 'trend-tooltip-value', row, fmt(r.v));
                    html('span', 'trend-tooltip-name', row, r.s.name);
                });
                tooltip.style.display = 'block';
                var tw = tooltip.offsetWidth;
                var left = cx + 14;
                if (left + tw > width) left = cx - 14 - tw;
                tooltip.style.left = Math.max(0, left) + 'px';
                tooltip.style.top = margin.top + 'px';
            }
            function hide() {
                active = null;
                hover.setAttribute('visibility', 'hidden');
                tooltip.style.display = 'none';
            }
            function nearest(evt) {
                var rect = svg.getBoundingClientRect();
                var px = (evt.clientX - rect.left) * (width / rect.width);
                if (n === 1) return 0;
                return Math.max(0, Math.min(n - 1, Math.round((px - margin.left) / (innerW / (n - 1)))));
            }
            hit.addEventListener('pointermove', function (evt) { show(nearest(evt)); });
            hit.addEventListener('pointerdown', function (evt) { show(nearest(evt)); });
            hit.addEventListener('pointerleave', hide);
            svg.addEventListener('blur', hide);
            svg.addEventListener('keydown', function (evt) {
                if (evt.key === 'ArrowRight' || evt.key === 'ArrowLeft') {
                    var step = evt.key === 'ArrowRight' ? 1 : -1;
                    var next = active === null ? (step > 0 ? 0 : n - 1) : active + step;
                    show(Math.max(0, Math.min(n - 1, next)));
                    evt.preventDefault();
                } else if (evt.key === 'Escape') {
                    hide();
                }
            });
        }
    }

    window.TrendChart = { mount: mount };
})();
