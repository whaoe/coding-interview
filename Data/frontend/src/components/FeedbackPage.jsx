import React, { useState } from 'react'

export default function FeedbackPage({ feedbacks, onUpdateFeedback, showToast }) {
  const [kwSearch, setKwSearch] = useState('')
  const [userSearch, setUserSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  const [editingItem, setEditingItem] = useState(null)
  const [remarkStatus, setRemarkStatus] = useState('待处理')
  const [remarkText, setRemarkText] = useState('')

  const filtered = (feedbacks || []).filter((r) => {
    if (statusFilter !== 'all' && r.status !== statusFilter) return false
    if (kwSearch.trim() && !r.question.toLowerCase().includes(kwSearch.trim().toLowerCase())) return false
    if (userSearch.trim() && !r.user.toLowerCase().includes(userSearch.trim().toLowerCase())) return false
    return true
  })

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const start = (safePage - 1) * pageSize
  const pageRows = filtered.slice(start, start + pageSize)

  const openHandleModal = (item) => {
    setEditingItem(item)
    setRemarkStatus(item.status || '待处理')
    setRemarkText(item.remark || '')
  }

  const saveHandle = async () => {
    if (!editingItem) return
    await onUpdateFeedback(editingItem.id, {
      status: remarkStatus,
      remark: remarkText,
    })
    setEditingItem(null)
    showToast('反馈校对处理已保存')
  }

  return (
    <div className="page-content active" id="page-sys-feedback-user" style={{ padding: 20 }}>
      <div className="breadcrumb">
        反馈管理 <span className="sep">/</span> <span>回复校对</span>
      </div>
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px 0', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
            <span style={{ fontSize: 15, fontWeight: 600 }}>
              <i className="fas fa-exclamation-circle" style={{ color: 'var(--primary)', marginRight: 6 }} />
              回复校对
            </span>
            <span style={{ fontSize: 13, color: '#9CA3AF' }}>
              此列表为用户标注AI回复数据有误的信息数据（含原始提问、AI回复摘要与执行SQL对照）
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8, paddingBottom: 12 }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              <div className="search-box" style={{ maxWidth: 200, height: 32 }}>
                <i className="fas fa-search" />
                <input
                  type="text"
                  placeholder="搜索问题..."
                  value={kwSearch}
                  onChange={(e) => {
                    setKwSearch(e.target.value)
                    setPage(1)
                  }}
                />
              </div>
              <div className="search-box" style={{ maxWidth: 150, height: 32 }}>
                <i className="fas fa-user" />
                <input
                  type="text"
                  placeholder="搜索用户..."
                  value={userSearch}
                  onChange={(e) => {
                    setUserSearch(e.target.value)
                    setPage(1)
                  }}
                />
              </div>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value)
                  setPage(1)
                }}
                style={{
                  height: 32,
                  padding: '0 10px',
                  border: '1px solid var(--border)',
                  borderRadius: 4,
                  fontSize: 14,
                  outline: 'none',
                  background: 'var(--surface)',
                  color: 'var(--text-body)',
                }}
              >
                <option value="all">全部状态</option>
                <option value="待处理">待处理</option>
                <option value="已处理">已处理</option>
              </select>
            </div>
            <span style={{ fontSize: 14, color: 'var(--text-hint)', whiteSpace: 'nowrap' }}>
              <i className="fas fa-database" /> 共 <strong>{filtered.length}</strong> 条
            </span>
          </div>
        </div>

        <div style={{ padding: '12px 20px 16px' }}>
          <div className="table-wrap">
            <table className="data-table" id="tableFeedback">
              <thead>
                <tr>
                  <th style={{ width: 50 }}>序号</th>
                  <th style={{ width: 90 }}>用户</th>
                  <th style={{ width: '24%' }}>用户提问</th>
                  <th style={{ width: '26%' }}>反馈说明</th>
                  <th style={{ width: 160 }}>反馈时间</th>
                  <th style={{ width: 90 }}>状态</th>
                  <th
                    style={{
                      width: 90,
                      position: 'sticky',
                      right: 0,
                      background: 'var(--surface)',
                      boxShadow: '-2px 0 4px rgba(0,0,0,.04)',
                    }}
                  >
                    操作
                  </th>
                </tr>
              </thead>
              <tbody>
                {pageRows.length > 0 ? (
                  pageRows.map((r, idx) => (
                    <tr key={r.id}>
                      <td style={{ textAlign: 'center' }}>{start + idx + 1}</td>
                      <td>{r.user}</td>
                      <td style={{ fontWeight: 500, color: '#1E3A5F' }}>{r.question}</td>
                      <td style={{ maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis' }} title={r.msg}>
                        {r.msg}
                      </td>
                      <td>{r.time}</td>
                      <td>
                        <span className={`tag ${r.status === '待处理' ? 'tag-orange' : 'tag-green'}`}>
                          {r.status}
                        </span>
                      </td>
                      <td style={{ position: 'sticky', right: 0, background: 'var(--surface)' }}>
                        <button
                          className="btn btn-text btn-xs"
                          onClick={() => openHandleModal(r)}
                        >
                          处理
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', color: '#9CA3AF', fontSize: 14, padding: 40 }}>
                      暂无反馈数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="pagination">
            <span className="page-info">共 {filtered.length} 条，每页 </span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value))
                setPage(1)
              }}
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
            </select>
            <span className="page-info">条</span>
            <div className="page-btns">
              <button disabled={safePage <= 1} onClick={() => setPage(safePage - 1)}>
                <i className="fas fa-angle-left" />
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  className={p === safePage ? 'active' : ''}
                  onClick={() => setPage(p)}
                >
                  {p}
                </button>
              ))}
              <button disabled={safePage >= totalPages} onClick={() => setPage(safePage + 1)}>
                <i className="fas fa-angle-right" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 反馈处理校对弹窗 (#feedbackRemarkModal) */}
      <div
        className={`modal-overlay ${editingItem ? 'show' : ''}`}
        style={{ zIndex: 1100 }}
        onClick={(e) => e.target === e.currentTarget && setEditingItem(null)}
      >
        <div className="modal" style={{ width: 760 }}>
          <div className="modal-header">
            <h3>
              <i className="fas fa-pen" style={{ color: '#2563EB', marginRight: 6 }} />
              反馈处理与数据校对
            </h3>
            <button className="close-btn" onClick={() => setEditingItem(null)}>
              <i className="fas fa-times" />
            </button>
          </div>
          {editingItem && (
            <div className="modal-body" style={{ display: 'flex', gap: 20 }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ fontSize: 14, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>
                    用户提问（反馈人：{editingItem.user}）
                  </label>
                  <div style={{ background: '#F9FAFB', padding: '10px 12px', borderRadius: 8, fontSize: 15, color: '#374151', lineHeight: 1.5 }}>
                    {editingItem.question}
                  </div>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ fontSize: 14, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>
                    用户反馈问题说明
                  </label>
                  <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', padding: '8px 12px', borderRadius: 8, fontSize: 14, color: '#991B1B' }}>
                    {editingItem.msg}
                  </div>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ fontSize: 14, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>
                    AI 原始回复内容
                  </label>
                  <div style={{ background: '#FFF8F0', border: '1px solid #FDE68A', borderRadius: 8, padding: '10px 12px', fontSize: 14, color: '#92400E', lineHeight: 1.6 }}>
                    {editingItem.aiReply || '（暂无AI回复数据）'}
                  </div>
                </div>
                {editingItem.sqlText && (
                  <div>
                    <label style={{ fontSize: 13, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 4 }}>
                      执行的取数 SQL
                    </label>
                    <pre style={{ background: '#1E293B', color: '#E2E8F0', padding: '8px 10px', borderRadius: 6, fontSize: 12, overflowX: 'auto', margin: 0 }}>
                      {editingItem.sqlText}
                    </pre>
                  </div>
                )}
              </div>

              <div style={{ width: 230, flexShrink: 0 }}>
                <div style={{ marginBottom: 14 }}>
                  <label style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-body)', display: 'block', marginBottom: 6 }}>
                    处理状态
                  </label>
                  <select
                    value={remarkStatus}
                    onChange={(e) => setRemarkStatus(e.target.value)}
                    style={{
                      width: '100%',
                      height: 36,
                      padding: '0 10px',
                      border: '1px solid #D1D5DB',
                      borderRadius: 6,
                      fontSize: 14,
                      outline: 'none',
                      background: '#FAFBFC',
                      color: 'var(--text-body)',
                    }}
                  >
                    <option value="待处理">待处理</option>
                    <option value="已处理">已处理</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-body)', display: 'block', marginBottom: 6 }}>
                    处理备注
                  </label>
                  <textarea
                    value={remarkText}
                    onChange={(e) => setRemarkText(e.target.value)}
                    placeholder="请填写数据核查结果与口径修正备注…"
                    style={{
                      width: '100%',
                      height: 190,
                      padding: 10,
                      border: '1px solid #D1D5DB',
                      borderRadius: 6,
                      fontSize: 14,
                      resize: 'vertical',
                      outline: 'none',
                      boxSizing: 'border-box',
                      fontFamily: 'inherit',
                      background: '#FAFBFC',
                    }}
                  />
                </div>
              </div>
            </div>
          )}
          <div className="modal-footer">
            <button className="btn btn-text" onClick={() => setEditingItem(null)}>取消</button>
            <button className="btn btn-primary" onClick={saveHandle}>
              <i className="fas fa-check" /> 确认
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
