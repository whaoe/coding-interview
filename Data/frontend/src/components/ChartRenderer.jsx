import React, { useState } from 'react'

const PIE_COLORS = ['#2563EB', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#6366F1', '#14B8A6']

export default function ChartRenderer({ chart }) {
  const [chartType, setChartType] = useState(chart?.type || 'bar')

  if (!chart || !chart.items || chart.items.length === 0) {
    return null
  }

  const items = chart.items
  const series = chart.series || [{ key: 'v1', label: '数值', color: '#2563EB' }]
  const hasV2 = series.length > 1 && items.some((it) => typeof it.v2 === 'number')

  const allVals = items.flatMap((it) => (hasV2 ? [it.v1 || 0, it.v2 || 0] : [it.v1 || 0]))
  const maxVal = Math.max(...allVals, 1)
  const totalV1 = items.reduce((s, it) => s + Math.max(0, it.v1 || 0), 0) || 1

  const renderBarChart = () => (
    <div>
      <div className="qa-chart-bars" style={{ height: 120, paddingTop: 14 }}>
        {items.map((it, idx) => {
          const h1 = Math.max(4, Math.round(((it.v1 || 0) / maxVal) * 84))
          const h2 = hasV2 ? Math.max(4, Math.round(((it.v2 || 0) / maxVal) * 84)) : 0
          return (
            <div className="qa-chart-grp" key={idx} style={{ maxWidth: 64 }}>
              <div style={{ fontSize: 10, color: '#64748B', marginBottom: 2, whiteSpace: 'nowrap' }}>
                {(it.v1 || 0).toLocaleString()}
              </div>
              <div className="bar-pair" style={{ height: 88 }}>
                <div
                  className="bar b-blue"
                  style={{ height: h1, width: hasV2 ? 12 : 18, background: series[0]?.color || '#2563EB' }}
                  title={`${it.label} - ${series[0]?.label}: ${(it.v1 || 0).toLocaleString()}`}
                />
                {hasV2 && (
                  <div
                    className="bar b-green"
                    style={{ height: h2, width: 12, background: series[1]?.color || '#10B981' }}
                    title={`${it.label} - ${series[1]?.label}: ${(it.v2 || 0).toLocaleString()}`}
                  />
                )}
              </div>
              <div className="chart-xlabel" title={it.label}>
                {it.label.length > 5 ? it.label.slice(0, 5) : it.label}
              </div>
            </div>
          )
        })}
      </div>
      <div className="qa-chart-legend">
        {series.map((s, si) => (
          <span key={si}>
            <span className="leg-dot" style={{ background: s.color }} />
            {s.label}
          </span>
        ))}
      </div>
    </div>
  )

  const renderHorizontalBar = () => (
    <div>
      <div className="qa-hbar-list">
        {items.map((it, idx) => {
          const w1 = Math.max(3, Math.round(((it.v1 || 0) / maxVal) * 100))
          const pct = ((it.v1 || 0) / totalV1 * 100).toFixed(1)
          return (
            <div className="qa-hbar-row" key={idx}>
              <div className="qa-hbar-label" title={it.label}>{it.label}</div>
              <div className="qa-hbar-track">
                <div
                  className="qa-hbar-fill"
                  style={{ width: `${w1}%`, background: PIE_COLORS[idx % PIE_COLORS.length] }}
                />
              </div>
              <div className="qa-hbar-val">
                {(it.v1 || 0).toLocaleString()} ({pct}%)
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )

  const renderPieChart = () => {
    const r = 52
    const c = 2 * Math.PI * r
    let offset = 0
    return (
      <div className="qa-pie-container">
        <svg width="140" height="140" viewBox="0 0 140 140" style={{ transform: 'rotate(-90deg)' }}>
          {items.map((it, idx) => {
            const val = Math.max(0, it.v1 || 0)
            const ratio = val / totalV1
            const dash = ratio * c
            const gap = c - dash
            const strokeOffset = -offset * c
            offset += ratio
            return (
              <circle
                key={idx}
                cx="70"
                cy="70"
                r={r}
                fill="none"
                stroke={PIE_COLORS[idx % PIE_COLORS.length]}
                strokeWidth="24"
                strokeDasharray={`${dash} ${gap}`}
                strokeDashoffset={strokeOffset}
              >
                <title>{`${it.label}: ${val.toLocaleString()} (${(ratio * 100).toFixed(1)}%)`}</title>
              </circle>
            )
          })}
          <circle cx="70" cy="70" r="36" fill="#FAFBFC" />
        </svg>
        <div className="qa-pie-legend">
          {items.map((it, idx) => {
            const val = Math.max(0, it.v1 || 0)
            const pct = ((val / totalV1) * 100).toFixed(1)
            return (
              <div className="qa-pie-legend-item" key={idx}>
                <div className="qa-pie-legend-left">
                  <span className="qa-pie-dot" style={{ background: PIE_COLORS[idx % PIE_COLORS.length] }} />
                  <span>{it.label}</span>
                </div>
                <span style={{ fontWeight: 600 }}>
                  {val.toLocaleString()} ({pct}%)
                </span>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  const renderLineChart = () => {
    const width = 460
    const height = 135
    const padL = 42
    const padR = 24
    const padT = 22
    const padB = 28
    const plotW = width - padL - padR
    const plotH = height - padT - padB

    const getPoints = (key) =>
      items.map((it, idx) => {
        const x = padL + (items.length === 1 ? plotW / 2 : (idx / (items.length - 1)) * plotW)
        const val = it[key] || 0
        const y = padT + plotH - (val / maxVal) * plotH
        return { x, y, val, label: it.label }
      })

    const pts1 = getPoints('v1')
    const pts2 = hasV2 ? getPoints('v2') : []
    const poly1 = pts1.map((p) => `${p.x},${p.y}`).join(' ')
    const poly2 = pts2.map((p) => `${p.x},${p.y}`).join(' ')

    return (
      <div>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', maxHeight: 150, overflow: 'visible' }}>
          {[0, 0.5, 1].map((t, i) => {
            const y = padT + plotH * (1 - t)
            const v = Math.round(maxVal * t)
            return (
              <g key={i}>
                <line x1={padL} y1={y} x2={width - padR} y2={y} stroke="#E2E8F0" strokeDasharray="3 3" />
                <text x={padL - 6} y={y + 4} textAnchor="end" fontSize="10" fill="#94A3B8">
                  {v}
                </text>
              </g>
            )
          })}
          <polyline fill="none" stroke={series[0]?.color || '#2563EB'} strokeWidth="2.5" points={poly1} />
          {hasV2 && (
            <polyline fill="none" stroke={series[1]?.color || '#10B981'} strokeWidth="2.5" points={poly2} />
          )}
          {pts1.map((p, idx) => (
            <g key={idx}>
              <circle cx={p.x} cy={p.y} r="4" fill="#fff" stroke={series[0]?.color || '#2563EB'} strokeWidth="2.5" />
              <text x={p.x} y={p.y - 7} textAnchor="middle" fontSize="10" fill="#334155" fontWeight="600">
                {p.val.toLocaleString()}
              </text>
              <text x={p.x} y={height - 6} textAnchor="middle" fontSize="11" fill="#64748B">
                {p.label.length > 6 ? p.label.slice(0, 6) : p.label}
              </text>
            </g>
          ))}
          {pts2.map((p, idx) => (
            <circle key={idx} cx={p.x} cy={p.y} r="3.5" fill="#fff" stroke={series[1]?.color || '#10B981'} strokeWidth="2" />
          ))}
        </svg>
        <div className="qa-chart-legend">
          {series.map((s, si) => (
            <span key={si}>
              <span className="leg-dot" style={{ background: s.color }} />
              {s.label}
            </span>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="qa-ai-chart">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, gap: 8, flexWrap: 'wrap' }}>
        <div className="chart-desc" style={{ margin: 0 }}>{chart.desc}</div>
        <div className="chart-type-switcher">
          <button
            type="button"
            className={`chart-type-btn ${chartType === 'bar' ? 'active' : ''}`}
            onClick={() => setChartType('bar')}
          >
            <i className="fas fa-chart-bar" /> 柱状图
          </button>
          <button
            type="button"
            className={`chart-type-btn ${chartType === 'pie' ? 'active' : ''}`}
            onClick={() => setChartType('pie')}
          >
            <i className="fas fa-chart-pie" /> 饼图
          </button>
          <button
            type="button"
            className={`chart-type-btn ${chartType === 'line' ? 'active' : ''}`}
            onClick={() => setChartType('line')}
          >
            <i className="fas fa-chart-line" /> 折线图
          </button>
          <button
            type="button"
            className={`chart-type-btn ${chartType === 'horizontal_bar' ? 'active' : ''}`}
            onClick={() => setChartType('horizontal_bar')}
          >
            <i className="fas fa-align-left" /> 条形图
          </button>
        </div>
      </div>
      <div className="qa-chart-wrap">
        <div className="qa-chart-title">{chart.title}</div>
        {chartType === 'pie' && renderPieChart()}
        {chartType === 'line' && renderLineChart()}
        {chartType === 'horizontal_bar' && renderHorizontalBar()}
        {(chartType === 'bar' || !['pie', 'line', 'horizontal_bar'].includes(chartType)) && renderBarChart()}
      </div>
    </div>
  )
}
