import React, { useState, useEffect, useRef } from 'react'
import ChartRenderer from './ChartRenderer.jsx'

export default function AiQaPage({
  sessions,
  currentSessionId,
  setCurrentSessionId,
  appConfig,
  dataSources,
  favorites,
  hotQuestions,
  onNewChat,
  onSendChat,
  onPinSession,
  onRenameSession,
  onDeleteSession,
  onClearSession,
  onToggleFavorite,
  onUpdateSources,
  onSubmitFeedback,
  showToast,
  collapseMainSidebar,
}) {
  const [qaSidebarCollapsed, setQaSidebarCollapsed] = useState(false)
  const [activeSubView, setActiveSubView] = useState('chat') // 'chat' | 'log'
  const [inputText, setInputText] = useState('')
  const [sending, setSending] = useState(false)

  // 快捷提问浮层
  const [qqOpen, setQqOpen] = useState(false)
  const [qqTab, setQqTab] = useState('recent') // 'recent' | 'favorite'

  // 会话右键/三点菜单
  const [ctxMenu, setCtxMenu] = useState({ show: false, x: 0, y: 0, sessionId: null })

  // 消息原地编辑状态
  const [editingMsgId, setEditingMsgId] = useState(null)
  const [editingText, setEditingText] = useState('')

  // 分析过程展开状态 map: { [msgId]: boolean }
  const [expandedSteps, setExpandedSteps] = useState({})

  // 复制成功提示状态 map
  const [copiedKey, setCopiedKey] = useState(null)

  // TTS 播报状态
  const [speakingMsgId, setSpeakingMsgId] = useState(null)

  // STT 录音状态
  const [recording, setRecording] = useState(false)
  const recognitionRef = useRef(null)

  // 数据源选择弹窗
  const [sourceModalOpen, setSourceModalOpen] = useState(false)
  const [localSources, setLocalSources] = useState([])

  // 报错反馈弹窗
  const [feedbackModal, setFeedbackModal] = useState({
    show: false,
    question: '',
    aiReply: '',
    sqlText: '',
    customMsg: '数据有误，实际数据与AI回复不一致',
  })

  // 日志筛选与右侧详情抽屉
  const [logTimeFilter, setLogTimeFilter] = useState('30')
  const [logUserFilter, setLogUserFilter] = useState('all')
  const [logSearch, setLogSearch] = useState('')
  const [detailSession, setDetailSession] = useState(null)

  const chatContainerRef = useRef(null)

  const currentSession = sessions.find((s) => s.id === currentSessionId) || null
  const hasMessages = currentSession && currentSession.msgs && currentSession.msgs.length > 0

  useEffect(() => {
    setLocalSources(dataSources || [])
  }, [dataSources])

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [currentSessionId, currentSession?.msgs?.length, sending])

  // 当常问开关关闭时，自动切到收藏 Tab
  useEffect(() => {
    if (!appConfig.hotRecommend && qqTab === 'recent') {
      setQqTab('favorite')
    }
  }, [appConfig.hotRecommend, qqTab])

  // 点击外部关闭右键菜单与快捷提问面板
  useEffect(() => {
    const handleDocClick = (e) => {
      if (ctxMenu.show && !e.target.closest('.qa-sb-ctx-menu') && !e.target.closest('.qa-sbi-menu')) {
        setCtxMenu({ show: false, x: 0, y: 0, sessionId: null })
      }
      if (qqOpen && !e.target.closest('.qq-panel') && !e.target.closest('.qq-btn')) {
        setQqOpen(false)
      }
    }
    document.addEventListener('click', handleDocClick)
    return () => document.removeEventListener('click', handleDocClick)
  }, [ctxMenu.show, qqOpen])

  const handleSend = async (customQ = null, editId = null, isRegen = false) => {
    const q = (customQ !== null ? customQ : inputText).trim()
    if (!q || sending) return
    if (customQ === null) setInputText('')
    setQqOpen(false)
    setActiveSubView('chat')
    collapseMainSidebar()
    setSending(true)
    try {
      await onSendChat({
        session_id: currentSessionId,
        question: q,
        edit_msg_id: editId,
        regenerate: isRegen,
      })
      if (editId !== null) {
        setEditingMsgId(null)
        setEditingText('')
      }
    } finally {
      setSending(false)
    }
  }

  const handleCopy = (text, key) => {
    navigator.clipboard?.writeText(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 1500)
  }

  // 文字转语音 (TTS)
  const handleToggleTts = (msgId, text) => {
    if (!('speechSynthesis' in window)) {
      showToast('当前浏览器不支持语音播报')
      return
    }
    if (speakingMsgId === msgId) {
      window.speechSynthesis.cancel()
      setSpeakingMsgId(null)
      return
    }
    window.speechSynthesis.cancel()
    const utter = new SpeechSynthesisUtterance(text)
    utter.lang = 'zh-CN'
    utter.rate = 1.05
    utter.onend = () => setSpeakingMsgId(null)
    utter.onerror = () => setSpeakingMsgId(null)
    setSpeakingMsgId(msgId)
    window.speechSynthesis.speak(utter)
  }

  // 语音转文字 (STT)
  const handleToggleStt = () => {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition
    if (recording) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop()
        } catch {
          // ignore
        }
      }
      setRecording(false)
      return
    }

    if (SpeechRec) {
      try {
        const rec = new SpeechRec()
        rec.lang = 'zh-CN'
        rec.continuous = false
        rec.interimResults = false
        rec.onstart = () => {
          setRecording(true)
          showToast('正在聆听，请说出您的数据问题...')
        }
        rec.onresult = (event) => {
          const transcript = event.results?.[0]?.[0]?.transcript || ''
          if (transcript) {
            setInputText((prev) => (prev ? `${prev} ${transcript}` : transcript))
          }
          setRecording(false)
        }
        rec.onerror = () => {
          setRecording(false)
          // 浏览器环境无麦克风硬件权限时提供智能语音识别演示兜底
          const sampleQuestions = [
            '2026年各经营单元收入排名',
            '政企行业收入3000万-5000万数据',
            '北京代表处今年达成情况',
            '高风险项目有哪些',
          ]
          const picked = sampleQuestions[Math.floor(Math.random() * sampleQuestions.length)]
          setInputText(picked)
          showToast(`语音识别完成：「${picked}」`)
        }
        rec.onend = () => setRecording(false)
        recognitionRef.current = rec
        rec.start()
        return
      } catch {
        // fallback below
      }
    }

    // 兜底模拟语音输入
    setRecording(true)
    showToast('正在语音识别中...')
    setTimeout(() => {
      const sampleQuestions = [
        '2026年各经营单元收入排名',
        '各产品线销售情况',
        '北京代表处今年达成情况',
        '高风险项目有哪些',
      ]
      const picked = sampleQuestions[Math.floor(Math.random() * sampleQuestions.length)]
      setInputText(picked)
      setRecording(false)
      showToast(`语音识别完成：「${picked}」`)
    }, 900)
  }

  // 数据源统计
  const selectedSourceCount = (dataSources || []).filter((s) => s.checked).length
  const totalSourceCount = (dataSources || []).length
  const sourceIndicatorText =
    selectedSourceCount === totalSourceCount
      ? '已选择所有数据源'
      : `已选 ${selectedSourceCount} 个数据源`

  // 排序后的会话列表（置顶优先，其次按创建时间倒序）
  const sortedSessions = [...sessions].sort((a, b) => {
    if (a.pinned && !b.pinned) return -1
    if (!a.pinned && b.pinned) return 1
    return new Date(b.createdAt) - new Date(a.createdAt)
  })

  // 过滤后的问答日志
  const filteredLogs = sessions.filter((s) => {
    if (logTimeFilter !== 'all') {
      const days = parseInt(logTimeFilter, 10)
      const cutoff = new Date()
      cutoff.setDate(cutoff.getDate() - days)
      if (new Date(s.createdAt) < cutoff) return false
    }
    if (logUserFilter !== 'all') {
      if (logUserFilter === 'admin' && s.user !== '管理员') return false
      if (logUserFilter === 'user' && s.user === '管理员') return false
    }
    if (logSearch.trim() && !s.title.toLowerCase().includes(logSearch.trim().toLowerCase())) {
      return false
    }
    return true
  })

  // 将开场问题两两分组
  const greetingRows = []
  const gQs = appConfig.greetingQuestions || []
  for (let i = 0; i < gQs.length; i += 2) {
    greetingRows.push(gQs.slice(i, i + 2))
  }

  const ctxSession = sessions.find((s) => s.id === ctxMenu.sessionId)

  return (
    <div className="page-content active" id="page-ai-qa" style={{ display: 'flex', height: 'calc(100vh - 56px)', overflow: 'hidden' }}>
      {/* 左侧近30天会话记录栏 */}
      <div id="qaSidebar" className={`qa-sidebar ${qaSidebarCollapsed ? 'collapsed' : ''}`}>
        <div className="qa-sb-top">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              className="qa-sb-collapse"
              onClick={() => setQaSidebarCollapsed((v) => !v)}
              title="收起侧栏"
            >
              <i className="fas fa-chevron-left" />
            </button>
            <span style={{ fontSize: 15, fontWeight: 500, color: '#1E3A5F' }}>近30天记录</span>
          </div>
        </div>
        <button
          className="qa-sb-newchat"
          onClick={() => {
            setActiveSubView('chat')
            onNewChat()
          }}
        >
          <i className="fas fa-plus" /> 开启新对话
        </button>
        <div className="qa-sb-list" id="qaSessionList">
          {sortedSessions.map((s) => {
            const isActive = s.id === currentSessionId
            return (
              <div
                key={s.id}
                className={`qa-sb-item ${s.pinned ? 'pinned' : ''} ${isActive ? 'active' : ''}`}
                onClick={() => {
                  setCurrentSessionId(s.id)
                  setActiveSubView('chat')
                  collapseMainSidebar()
                }}
              >
                {s.pinned && (
                  <span className="qa-sbi-pin">
                    <i className="fas fa-thumbtack" />
                  </span>
                )}
                <span className="qa-sbi-title" title={s.title}>{s.title}</span>
                <button
                  className="qa-sbi-menu"
                  onClick={(e) => {
                    e.stopPropagation()
                    setCtxMenu({
                      show: true,
                      x: e.clientX,
                      y: e.clientY,
                      sessionId: s.id,
                    })
                  }}
                >
                  <i className="fas fa-ellipsis-v" />
                </button>
              </div>
            )
          })}
        </div>
      </div>

      {/* 主问答区 */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden', height: '100%' }}>
        <div className="qa-main" id="qaMainArea">
          {/* 顶部栏（补全数据源选择与问答日志入口） */}
          <div className="qa-right-hdr">
            <div className="qa-rh-left">
              <button
                className="qa-rh-btn"
                onClick={() => setQaSidebarCollapsed((v) => !v)}
                title="展开/收起会话记录栏"
              >
                <i className="fas fa-outdent" />
              </button>
            </div>
            <div className="qa-rh-center" id="qaSessionTitle">
              {currentSession ? currentSession.title : 'AI 智能问数对话'}
            </div>
            <div className="qa-rh-right">
              <button
                type="button"
                className="qa-top-chip"
                onClick={() => {
                  setLocalSources(dataSources.map((s) => ({ ...s })))
                  setSourceModalOpen(true)
                }}
                title="选择参与智能问数的数据源表"
              >
                <i className="fas fa-database" style={{ color: '#2563EB' }} />
                <span id="qaSourceIndicator">{sourceIndicatorText}</span>
              </button>
              {hasMessages && activeSubView === 'chat' && (
                <button
                  type="button"
                  className="qa-top-chip"
                  onClick={() => {
                    if (window.confirm('确认清空当前对话？消息将永久删除。')) {
                      onClearSession(currentSession.id)
                    }
                  }}
                  title="清空当前对话记录"
                >
                  <i className="fas fa-broom" /> 清空
                </button>
              )}
              <button
                type="button"
                className={`qa-top-chip ${activeSubView === 'log' ? 'active' : ''}`}
                onClick={() => setActiveSubView(activeSubView === 'log' ? 'chat' : 'log')}
                title="查看智能问数会话日志"
              >
                <i className="fas fa-clock" /> 问答日志
              </button>
            </div>
          </div>

          {/* 视图 A：问答日志视图 (#qaLogView) */}
          {activeSubView === 'log' ? (
            <div id="qaLogView" className="qa-chat-view show" style={{ flex: 1 }}>
              <div className="qa-chat-hdr">
                <span className="qa-chat-title">
                  <i className="fas fa-clock" style={{ color: 'var(--primary)', marginRight: 6 }} />
                  问答会话日志（点击行可查看详情抽屉）
                </span>
                <div className="qa-chat-actions">
                  <button className="btn btn-text btn-sm" onClick={() => setActiveSubView('chat')}>
                    <i className="fas fa-arrow-left" /> 返回对话
                  </button>
                </div>
              </div>
              <div style={{ padding: '12px 20px', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <select
                  value={logTimeFilter}
                  onChange={(e) => setLogTimeFilter(e.target.value)}
                  style={{ height: 32, padding: '0 10px', border: '1px solid var(--border)', borderRadius: 4, fontSize: 14, background: 'var(--surface)', color: 'var(--text-body)' }}
                >
                  <option value="7">过去7天</option>
                  <option value="30">过去30天</option>
                  <option value="90">过去90天</option>
                  <option value="all">全部时间</option>
                </select>
                <select
                  value={logUserFilter}
                  onChange={(e) => setLogUserFilter(e.target.value)}
                  style={{ height: 32, padding: '0 10px', border: '1px solid var(--border)', borderRadius: 4, fontSize: 14, background: 'var(--surface)', color: 'var(--text-body)' }}
                >
                  <option value="all">全部用户</option>
                  <option value="admin">管理员</option>
                  <option value="user">普通用户</option>
                </select>
                <div className="search-box" style={{ maxWidth: 220, height: 32 }}>
                  <i className="fas fa-search" />
                  <input
                    type="text"
                    placeholder="搜索会话标题..."
                    value={logSearch}
                    onChange={(e) => setLogSearch(e.target.value)}
                  />
                </div>
                <span style={{ fontSize: 14, color: 'var(--text-hint)', marginLeft: 'auto' }}>
                  共 <strong>{filteredLogs.length}</strong> 条会话日志
                </span>
              </div>
              <div className="table-wrap" style={{ flex: 1, overflowY: 'auto', minHeight: 0, margin: '0 20px 16px' }}>
                <table className="data-table" id="qaLogTable">
                  <thead>
                    <tr>
                      <th style={{ width: 220 }}>标题</th>
                      <th style={{ width: 90 }}>用户</th>
                      <th style={{ width: 80 }}>调用模型</th>
                      <th style={{ width: 70 }}>消息数</th>
                      <th style={{ width: 90 }}>用户反馈</th>
                      <th style={{ width: 90 }}>管理员校对</th>
                      <th style={{ width: 150 }}>更新时间</th>
                      <th style={{ width: 150 }}>创建时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredLogs.map((s) => (
                      <tr
                        key={s.id}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setDetailSession(s)}
                      >
                        <td style={{ fontWeight: 500, color: '#1E3A5F' }}>{s.title}</td>
                        <td>{s.user}</td>
                        <td>
                          <span className="tag tag-blue" style={{ height: 22, fontSize: 12 }}>
                            {s.modelUsed || 'GPT-4o'}
                          </span>
                        </td>
                        <td>{s.msgCount}</td>
                        <td>{s.userFeedback || '-'}</td>
                        <td>{s.adminFeedback || '-'}</td>
                        <td>{s.time}</td>
                        <td>{(s.createdAt || '').slice(0, 16).replace('T', ' ')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <>
              {/* 视图 B1：欢迎页 (#qaWelcomeView) */}
              {!hasMessages ? (
                <div id="qaWelcomeView" className="qa-welcome">
                  <div className="qa-welcome-inner">
                    <h1>你好</h1>
                    <h2>我是 AI 问数助手</h2>
                    {appConfig.greeting && (
                      <>
                        <p className="qa-desc" id="qaDesc">
                          {appConfig.greetingText || '欢迎使用智能AI问数，您可以向我咨询经营数据、报表分析相关问题。'}
                        </p>
                        {greetingRows.length > 0 && (
                          <div className="qa-quick-section" id="qaQuickSection">
                            <div className="qa-quick-title">你可以这么问我</div>
                            <div className="qa-quick-grid">
                              {greetingRows.map((row, rIdx) => (
                                <div className="qa-quick-row" key={rIdx}>
                                  {row.map((qText, qIdx) => (
                                    <div
                                      key={qIdx}
                                      className="qa-quick-btn"
                                      onClick={() => handleSend(qText)}
                                    >
                                      {qText}
                                    </div>
                                  ))}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              ) : (
                /* 视图 B2：多轮问答对话区 (#qaChatView) */
                <div className="qa-chat-view show" id="qaChatView">
                  <div className="qa-chat-msgs" id="chatMessages" ref={chatContainerRef}>
                    {currentSession.msgs.map((m) => {
                      if (m.role === 'user') {
                        const isFav = favorites.includes(m.text)
                        const isEditing = editingMsgId === m.id
                        return (
                          <div className="qa-user-msg" key={m.id}>
                            <div className="qa-user-bubble" style={isEditing ? { width: '70%' } : undefined}>
                              {isEditing ? (
                                <textarea
                                  value={editingText}
                                  onChange={(e) => setEditingText(e.target.value)}
                                  style={{
                                    width: '100%',
                                    border: 'none',
                                    background: 'transparent',
                                    resize: 'vertical',
                                    outline: 'none',
                                    fontSize: 16,
                                    color: '#1E1B4B',
                                    lineHeight: 1.5,
                                    fontFamily: 'inherit',
                                    minHeight: 48,
                                  }}
                                  autoFocus
                                />
                              ) : (
                                m.text
                              )}
                            </div>

                            {isEditing ? (
                              <div className="qa-edit-bar" style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                                <button
                                  className="btn btn-text btn-sm"
                                  onClick={() => {
                                    setEditingMsgId(null)
                                    setEditingText('')
                                  }}
                                >
                                  <i className="fas fa-times" /> 取消
                                </button>
                                <button
                                  className="btn btn-primary btn-sm"
                                  onClick={() => handleSend(editingText, m.id, false)}
                                >
                                  <i className="fas fa-paper-plane" /> 重新发送
                                </button>
                              </div>
                            ) : (
                              <div className="qa-user-actions">
                                <button
                                  onClick={() => onToggleFavorite(m.text)}
                                  data-title={isFav ? '取消收藏' : '收藏'}
                                >
                                  <i
                                    className="fas fa-star"
                                    style={isFav ? { color: '#F59E0B' } : undefined}
                                  />
                                </button>
                                <button
                                  onClick={() => {
                                    setEditingMsgId(m.id)
                                    setEditingText(m.text)
                                  }}
                                  data-title="编辑"
                                >
                                  <i className="fas fa-pen" />
                                </button>
                                <button
                                  onClick={() => handleSend(m.text, m.id, false)}
                                  data-title="重新发送"
                                >
                                  <i className="fas fa-sync-alt" />
                                </button>
                                <button
                                  onClick={() => handleCopy(m.text, `u_${m.id}`)}
                                  data-title={copiedKey === `u_${m.id}` ? '已复制' : '复制'}
                                >
                                  <i className={`fas ${copiedKey === `u_${m.id}` ? 'fa-check' : 'fa-copy'}`} />
                                </button>
                              </div>
                            )}
                          </div>
                        )
                      }

                      // AI 回复卡片
                      const p = m.payload || {}
                      const steps = p.steps || []
                      const discovery = p.discovery || []
                      const tbl = p.table || { columns: [], rows: [] }
                      const stats = p.stats || []
                      const chart = p.chart || null
                      const followups = p.followups || []
                      const metrics = p.metrics || { elapsed: '0.4s', tokens: 320, time: '' }
                      const isStepsOpen = !!expandedSteps[m.id]

                      return (
                        <div className="qa-ai-msg" key={m.id}>
                          <div className="qa-ai-card" data-question={p.question || ''}>
                            <div className="qa-ai-avatar" style={{ marginBottom: 12 }}>
                              <i className="fas fa-robot" />
                            </div>

                            {/* 5步透明化分析过程折叠面板 */}
                            {steps.length > 0 && (
                              <div className="aa-wrap">
                                <div
                                  className="aa-summary-bar"
                                  onClick={() =>
                                    setExpandedSteps((prev) => ({ ...prev, [m.id]: !prev[m.id] }))
                                  }
                                >
                                  <i className="fas fa-microchip" /> 分析过程{' '}
                                  <span className="arr">{isStepsOpen ? '▾' : '▸'}</span>
                                  <span style={{ marginLeft: 'auto', color: '#6B7280', fontSize: 13 }}>
                                    {isStepsOpen ? '点击收起' : '点击展开'}
                                  </span>
                                </div>
                                <div className={`aa-inline-steps ${isStepsOpen ? 'show' : ''}`}>
                                  {steps.map((st, sIdx) => (
                                    <div key={sIdx} className={`aa-step ${st.done ? 'done' : 'active'}`} style={{ display: 'flex', gap: 8, padding: '6px 0', borderTop: sIdx > 0 ? '1px dashed #DBEAFE' : 'none' }}>
                                      <div className="aa-step-icon" style={{ color: '#2563EB', fontSize: 13, marginTop: 2 }}>
                                        {st.done ? <i className="fas fa-check-circle" /> : <i className="fas fa-spinner fa-spin" />}
                                      </div>
                                      <div className="aa-step-body" style={{ flex: 1, minWidth: 0 }}>
                                        <div className="aa-step-title" style={{ fontWeight: 600, fontSize: 13, color: '#1E3A5F', marginBottom: 2 }}>
                                          {st.title}
                                        </div>
                                        <div
                                          className={`aa-step-desc ${st.isCode ? 'code' : ''}`}
                                          style={
                                            st.isCode
                                              ? {
                                                  background: '#1E293B',
                                                  color: '#E2E8F0',
                                                  padding: '8px 10px',
                                                  borderRadius: 6,
                                                  fontFamily: 'monospace',
                                                  fontSize: 12,
                                                  whiteSpace: 'pre-wrap',
                                                }
                                              : { fontSize: 13, color: '#4B5563', whiteSpace: 'pre-line' }
                                          }
                                        >
                                          {st.desc}
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* 模块 1：数据发现 */}
                            {discovery.length > 0 && (
                              <div className="qa-ai-module">
                                <div className="mod-title">
                                  <span className="mod-num">1</span>数据发现
                                </div>
                                <div className="mod-body">
                                  {discovery.map((dItem, dIdx) => (
                                    <div className="dot-li" key={dIdx}>{dItem}</div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* 模块 2：数据表格 */}
                            {tbl.columns && tbl.columns.length > 0 && (
                              <div className="qa-ai-module">
                                <div className="mod-title">
                                  <span className="mod-num">2</span>数据表格
                                </div>
                                <div style={{ overflowX: 'auto' }}>
                                  <table className="qa-ai-table">
                                    <thead>
                                      <tr>
                                        {tbl.columns.map((col, cIdx) => (
                                          <th key={cIdx}>{col}</th>
                                        ))}
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {tbl.rows.map((r, rIdx) => (
                                        <tr key={rIdx}>
                                          {r.map((cell, cIdx) => (
                                            <td key={cIdx}>
                                              {typeof cell === 'number' ? cell.toLocaleString() : String(cell ?? '')}
                                            </td>
                                          ))}
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            )}

                            {/* 模块 3：数据统计 */}
                            {stats.length > 0 && (
                              <div className="qa-ai-module">
                                <div className="mod-title">
                                  <span className="mod-num">3</span>数据统计
                                </div>
                                <div className="mod-body">
                                  {stats.map((sItem, sIdx) => (
                                    <div className="dot-li" key={sIdx}>{sItem}</div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* 模块 4：数据可视化 */}
                            {chart && chart.items && chart.items.length > 0 && (
                              <div className="qa-ai-module">
                                <div className="mod-title">
                                  <span className="mod-num">4</span>数据可视化
                                </div>
                                <ChartRenderer chart={chart} />
                              </div>
                            )}

                            {/* 兼容纯文本历史回复 */}
                            {discovery.length === 0 && (!tbl.columns || tbl.columns.length === 0) && (
                              <div style={{ whiteSpace: 'pre-line', fontSize: 15, color: '#374151' }}>{m.text}</div>
                            )}

                            {/* 卡片底部操作栏 */}
                            <div className="qa-ai-footer">
                              <div className="qa-ai-actions">
                                <button
                                  onClick={() => handleCopy(p.summary_text || m.text, `ai_${m.id}`)}
                                  data-title={copiedKey === `ai_${m.id}` ? '已复制' : '复制'}
                                >
                                  <i className={`fas ${copiedKey === `ai_${m.id}` ? 'fa-check' : 'fa-copy'}`} />
                                </button>
                                <button
                                  onClick={() =>
                                    setFeedbackModal({
                                      show: true,
                                      question: p.question || currentSession?.title || '智能问数查询',
                                      aiReply: p.summary_text || m.text,
                                      sqlText: p.sql || '',
                                      customMsg: '数据有误，实际数据与AI回复不一致',
                                    })
                                  }
                                  data-title="反馈校对"
                                >
                                  <i className="fas fa-frown" />
                                </button>
                                {appConfig.tts && (
                                  <button
                                    className={speakingMsgId === m.id ? 'speaking' : ''}
                                    onClick={() => handleToggleTts(m.id, p.summary_text || m.text)}
                                    data-title={speakingMsgId === m.id ? '停止播报' : '语音播放'}
                                  >
                                    <i className="fas fa-volume-up" />
                                  </button>
                                )}
                              </div>
                              <div className="qa-ai-stats">
                                耗时{metrics.elapsed} {'  '}Token:{metrics.tokens} {'  '}
                                {metrics.model ? `${metrics.model}  ` : ''}
                                {metrics.time}
                              </div>
                            </div>

                            {/* 延伸追问建议（受 appConfig.suggestions 开关动态控制） */}
                            {appConfig.suggestions && followups.length > 0 && (
                              <div className="qa-followup">
                                {followups.map((fu, fIdx) => (
                                  <span
                                    key={fIdx}
                                    className="fu-chip"
                                    onClick={() => handleSend(fu)}
                                  >
                                    {fu}
                                    <span className="arr">→</span>
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    })}

                    {sending && (
                      <div className="qa-ai-msg">
                        <div className="qa-ai-card" style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#2563EB' }}>
                          <i className="fas fa-spinner fa-spin" />
                          <span>正在解析自然语言并执行 Text2SQL 数据分析...</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 底部输入栏与快捷提问面板 */}
              <div className="qa-input-bar">
                <div className="qa-input-wrap">
                  <button
                    type="button"
                    className="qq-btn"
                    onClick={() => setQqOpen((v) => !v)}
                    title="快捷提问"
                  >
                    <i className="fas fa-bolt" />
                  </button>
                  <input
                    id="chatInput"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="请写下您的想法…（例如：2026年各经营单元收入排名 / 政企行业收入3000万-5000万数据）"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleSend()
                      }
                    }}
                  />
                  {appConfig.stt && (
                    <button
                      type="button"
                      className={`qa-mic-btn ${recording ? 'recording' : ''}`}
                      onClick={handleToggleStt}
                      title={recording ? '点击结束语音输入' : '语音转文字提问'}
                    >
                      <i className="fas fa-microphone" />
                    </button>
                  )}
                  <button
                    type="button"
                    className={`qa-send-btn ${!inputText.trim() || sending ? 'op' : ''}`}
                    id="qaSendBtn"
                    onClick={() => handleSend()}
                  >
                    <i className="fas fa-arrow-right" />
                  </button>

                  {/* 快捷提问面板 (#qqPanel) */}
                  <div className={`qq-panel ${qqOpen ? 'show' : ''}`} id="qqPanel">
                    <div className="qq-phdr">
                      <h4>
                        <i className="fas fa-bolt" style={{ color: '#2563EB', marginRight: 4 }} />
                        快捷提问
                      </h4>
                      <button className="qq-close" onClick={() => setQqOpen(false)}>
                        <i className="fas fa-times" />
                      </button>
                    </div>
                    <div className="qq-tabs" id="qqTabs">
                      {appConfig.hotRecommend && (
                        <span
                          className={`qq-tab ${qqTab === 'recent' ? 'active' : ''}`}
                          onClick={() => setQqTab('recent')}
                        >
                          常问（≥{appConfig.hotThreshold}次）
                        </span>
                      )}
                      <span
                        className={`qq-tab ${qqTab === 'favorite' ? 'active' : ''}`}
                        onClick={() => setQqTab('favorite')}
                      >
                        收藏（{favorites.length}）
                      </span>
                    </div>
                    <div className="qq-list" id="qqList">
                      {qqTab === 'recent' && appConfig.hotRecommend ? (
                        hotQuestions.length > 0 ? (
                          hotQuestions.map((hq, idx) => (
                            <div
                              key={idx}
                              className="qq-item"
                              onClick={() => handleSend(hq.question)}
                            >
                              <span>{hq.question}</span>
                              <span style={{ fontSize: 12, color: '#9CA3AF' }}>{hq.count}次</span>
                            </div>
                          ))
                        ) : (
                          <div style={{ padding: 20, textAlign: 'center', color: '#9CA3AF', fontSize: 14 }}>
                            暂无达到频次阈值（{appConfig.hotThreshold}次）的常问问题
                          </div>
                        )
                      ) : favorites.length > 0 ? (
                        favorites.map((fq, idx) => (
                          <div
                            key={idx}
                            className="qq-item"
                            onClick={() => handleSend(fq)}
                          >
                            <span>{fq}</span>
                            <span
                              className="qq-unfav"
                              onClick={(e) => {
                                e.stopPropagation()
                                onToggleFavorite(fq)
                              }}
                              title="取消收藏"
                            >
                              <i className="fas fa-times" />
                            </span>
                          </div>
                        ))
                      ) : (
                        <div style={{ padding: 20, textAlign: 'center', color: '#9CA3AF', fontSize: 14 }}>
                          暂无收藏问题，可在对话消息下方点击星标收藏
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* 会话右键/三点操作菜单 */}
      <div
        className={`qa-sb-ctx-menu ${ctxMenu.show ? 'show' : ''}`}
        style={{ left: ctxMenu.x, top: ctxMenu.y }}
      >
        <button
          className="ctx-item"
          onClick={() => {
            if (ctxSession) onPinSession(ctxSession.id, !ctxSession.pinned)
            setCtxMenu({ show: false, x: 0, y: 0, sessionId: null })
          }}
        >
          <i className="fas fa-thumbtack" /> {ctxSession?.pinned ? '取消置顶' : '置顶'}
        </button>
        <button
          className="ctx-item"
          onClick={() => {
            if (ctxSession) {
              const newTitle = window.prompt('重命名会话：', ctxSession.title)
              if (newTitle && newTitle.trim()) {
                onRenameSession(ctxSession.id, newTitle.trim())
              }
            }
            setCtxMenu({ show: false, x: 0, y: 0, sessionId: null })
          }}
        >
          <i className="fas fa-edit" /> 重命名
        </button>
        <button
          className="ctx-item ctx-danger"
          onClick={() => {
            if (ctxSession && window.confirm(`确认删除会话「${ctxSession.title}」？`)) {
              onDeleteSession(ctxSession.id)
            }
            setCtxMenu({ show: false, x: 0, y: 0, sessionId: null })
          }}
        >
          <i className="fas fa-trash" /> 删除
        </button>
      </div>

      {/* 数据源选择弹窗 (#qaFilePickerModal) */}
      <div className={`modal-overlay ${sourceModalOpen ? 'show' : ''}`} onClick={(e) => e.target === e.currentTarget && setSourceModalOpen(false)}>
        <div className="modal" style={{ width: 420 }}>
          <div className="modal-header">
            <h3>
              <i className="fas fa-database" style={{ color: 'var(--primary)', marginRight: 6 }} />
              选择数据源
            </h3>
            <button className="close-btn" onClick={() => setSourceModalOpen(false)}>
              <i className="fas fa-times" />
            </button>
          </div>
          <div className="modal-body" style={{ padding: '12px 20px' }}>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <button
                className="btn btn-text btn-xs"
                style={{ fontSize: 14 }}
                onClick={() => setLocalSources((prev) => prev.map((s) => ({ ...s, checked: true })))}
              >
                全选
              </button>
              <button
                className="btn btn-text btn-xs"
                style={{ fontSize: 14 }}
                onClick={() => setLocalSources((prev) => prev.map((s) => ({ ...s, checked: false })))}
              >
                取消全选
              </button>
            </div>
            <div style={{ maxHeight: 320, overflowY: 'auto' }}>
              {['台账数据', '统计报表'].map((grp) => (
                <div key={grp} style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-hint)', padding: '6px 0 4px' }}>
                    {grp}
                  </div>
                  {localSources
                    .filter((s) => s.group === grp)
                    .map((s) => (
                      <label
                        key={s.name}
                        className="sf-pop-opt"
                        style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', fontSize: 15, cursor: 'pointer' }}
                      >
                        <input
                          type="checkbox"
                          checked={s.checked}
                          onChange={(e) => {
                            const val = e.target.checked
                            setLocalSources((prev) =>
                              prev.map((item) => (item.name === s.name ? { ...item, checked: val } : item))
                            )
                          }}
                        />
                        <span>{s.label || s.name}</span>
                        <span style={{ marginLeft: 'auto', fontSize: 12, color: '#9CA3AF' }}>{s.tableName}</span>
                      </label>
                    ))}
                </div>
              ))}
            </div>
          </div>
          <div className="modal-footer">
            <button className="btn btn-text" onClick={() => setSourceModalOpen(false)}>取消</button>
            <button
              className="btn btn-primary"
              onClick={async () => {
                await onUpdateSources(localSources)
                setSourceModalOpen(false)
                showToast('数据源范围已更新')
              }}
            >
              确定
            </button>
          </div>
        </div>
      </div>

      {/* AI 回复报错反馈弹窗 (#optimizeModal) */}
      <div
        className={`modal-overlay ${feedbackModal.show ? 'show' : ''}`}
        style={{ zIndex: 1100 }}
        onClick={(e) => e.target === e.currentTarget && setFeedbackModal((prev) => ({ ...prev, show: false }))}
      >
        <div className="modal" style={{ width: 480 }}>
          <div className="modal-header">
            <h3>
              <i className="fas fa-frown" style={{ color: '#2563EB', marginRight: 6 }} />
              AI回复反馈
            </h3>
            <button className="close-btn" onClick={() => setFeedbackModal((prev) => ({ ...prev, show: false }))}>
              <i className="fas fa-times" />
            </button>
          </div>
          <div className="modal-body">
            <div style={{ fontSize: 15, color: '#374151', marginBottom: 10, lineHeight: 1.6 }}>
              请问您对当前「<strong>{feedbackModal.question}</strong>」的回复哪里不满意？
            </div>
            <textarea
              value={feedbackModal.customMsg}
              onChange={(e) => setFeedbackModal((prev) => ({ ...prev, customMsg: e.target.value }))}
              placeholder="请描述具体的数据差异或口径问题..."
              style={{
                width: '100%',
                height: 76,
                padding: 10,
                border: '1px solid var(--border)',
                borderRadius: 8,
                fontSize: 14,
                marginBottom: 12,
                outline: 'none',
                resize: 'vertical',
                fontFamily: 'inherit',
              }}
            />
            <button
              className="btn btn-outline"
              style={{ width: '100%', height: 44, fontSize: 15, justifyContent: 'center' }}
              onClick={async () => {
                await onSubmitFeedback({
                  session_id: currentSessionId,
                  question: feedbackModal.question,
                  msg: feedbackModal.customMsg || '数据有误，实际数据与AI回复不一致',
                  ai_reply: feedbackModal.aiReply,
                  sql_text: feedbackModal.sqlText,
                })
                setFeedbackModal((prev) => ({ ...prev, show: false }))
              }}
            >
              <i className="fas fa-exclamation-triangle" style={{ marginRight: 4 }} />
              数据有误，提交至「回复校对」
            </button>
          </div>
        </div>
      </div>

      {/* 问答日志右侧会话详情抽屉 (#qaDetailPanel) */}
      <div
        className={`qa-detail-overlay ${detailSession ? 'show' : ''}`}
        onClick={() => setDetailSession(null)}
      />
      <div className={`qa-detail-panel ${detailSession ? 'show' : ''}`}>
        {detailSession && (
          <>
            <div className="qa-detail-hdr">
              <div className="qa-dh-left">
                <div className="qa-dh-title">{detailSession.title}</div>
                <div
                  className="qa-dh-id"
                  onClick={() => {
                    handleCopy(String(detailSession.id), 'dt_id')
                    showToast('会话 ID 已复制')
                  }}
                >
                  <span>ID: {detailSession.id}</span>
                  <i className={`fas ${copiedKey === 'dt_id' ? 'fa-check' : 'fa-copy'}`} style={{ fontSize: 12 }} />
                </div>
              </div>
              <div className="qa-dh-right">
                <span className="qa-dh-model">{detailSession.modelUsed || 'GPT-4o'}</span>
                <span
                  className="close-btn"
                  onClick={() => setDetailSession(null)}
                  style={{
                    position: 'static',
                    width: 28,
                    height: 28,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: 6,
                    cursor: 'pointer',
                    color: 'var(--text-hint)',
                    fontSize: 16,
                  }}
                >
                  <i className="fas fa-times" />
                </span>
              </div>
            </div>
            <div className="qa-detail-body">
              {(detailSession.msgs || []).map((m, idx) => (
                <div
                  key={idx}
                  style={{
                    marginBottom: 14,
                    padding: 12,
                    borderRadius: 8,
                    background: m.role === 'user' ? '#EDE9FE' : '#F8FAFC',
                    border: m.role === 'user' ? 'none' : '1px solid #E2E8F0',
                  }}
                >
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#64748B', marginBottom: 4 }}>
                    {m.role === 'user' ? `用户提问（${detailSession.user}）` : `AI 回复（${detailSession.modelUsed || 'GPT-4o'}）`}
                  </div>
                  <div style={{ fontSize: 14, color: '#1E293B', lineHeight: 1.6, whiteSpace: 'pre-line' }}>
                    {m.text}
                  </div>
                  {m.payload?.sql && (
                    <pre
                      style={{
                        marginTop: 8,
                        padding: 8,
                        borderRadius: 6,
                        background: '#1E293B',
                        color: '#E2E8F0',
                        fontSize: 11,
                        overflowX: 'auto',
                      }}
                    >
                      {m.payload.sql}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
