import React, { useState, useEffect } from 'react'
import { api } from './api.js'
import AiQaPage from './components/AiQaPage.jsx'
import AppConfigPage from './components/AppConfigPage.jsx'
import ModelConfigPage from './components/ModelConfigPage.jsx'
import FeedbackPage from './components/FeedbackPage.jsx'

export default function App() {
  const [activePage, setActivePage] = useState('ai-qa') // 'ai-qa' | 'sys-app' | 'sys-model' | 'sys-feedback-user'
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [openMenus, setOpenMenus] = useState({ system: true, feedback: true })
  const [avatarDropdownOpen, setAvatarDropdownOpen] = useState(false)

  // 全局业务状态
  const [appConfig, setAppConfig] = useState({
    greeting: true,
    suggestions: true,
    tts: true,
    stt: true,
    hotRecommend: true,
    modelConfig: true,
    greetingText: '欢迎使用智能AI问数，您可以向我咨询经营数据、报表分析相关问题。',
    greetingQuestions: ['各产品线销售情况', '北京的产品线收入情况', '深圳的产品销售情况'],
    hotThreshold: 3,
  })
  const [models, setModels] = useState([])
  const [activeModel, setActiveModel] = useState({ id: 1, name: 'GPT-4o' })
  const [dataSources, setDataSources] = useState([])
  const [favorites, setFavorites] = useState([])
  const [hotQuestions, setHotQuestions] = useState([])
  const [sessions, setSessions] = useState([])
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const [feedbacks, setFeedbacks] = useState([])
  const [toastMsg, setToastMsg] = useState('')

  const showToast = (msg) => {
    setToastMsg(msg)
    setTimeout(() => {
      setToastMsg((prev) => (prev === msg ? '' : prev))
    }, 3500)
  }

  // 初始化加载
  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getBootstrap()
        setAppConfig(data.appConfig)
        setModels(data.models || [])
        setActiveModel(data.activeModel || { id: 1, name: 'GPT-4o' })
        setDataSources(data.dataSources || [])
        setFavorites(data.favorites || [])
        setHotQuestions(data.hotQuestions || [])
        setSessions(data.sessions || [])
        if (data.sessions && data.sessions.length > 0) {
          setCurrentSessionId(data.sessions[0].id)
        }
        const fbRes = await api.listFeedbacks()
        setFeedbacks(fbRes.feedbacks || [])
      } catch (err) {
        console.error('Bootstrap error:', err)
      }
    }
    load()
  }, [])

  // 点击外部关闭右上角头像下拉菜单
  useEffect(() => {
    const onDocClick = (e) => {
      if (!e.target.closest('#userAvatar')) {
        setAvatarDropdownOpen(false)
      }
    }
    document.addEventListener('click', onDocClick)
    return () => document.removeEventListener('click', onDocClick)
  }, [])

  // 会话操作
  const handleNewChat = async () => {
    const res = await api.createSession({ title: '新对话' })
    const newSess = res.session
    setSessions((prev) => [newSess, ...prev])
    setCurrentSessionId(newSess.id)
  }

  const handleSendChat = async ({ session_id, question, edit_msg_id, regenerate }) => {
    const res = await api.sendChat({
      session_id,
      question,
      edit_msg_id,
      regenerate,
    })
    const updatedSess = res.session
    setSessions((prev) => {
      const exists = prev.some((s) => s.id === updatedSess.id)
      if (exists) {
        return prev.map((s) => (s.id === updatedSess.id ? updatedSess : s))
      }
      return [updatedSess, ...prev]
    })
    setCurrentSessionId(updatedSess.id)
    if (res.hotQuestions) {
      setHotQuestions(res.hotQuestions)
    }
  }

  const handlePinSession = async (sid, pinned) => {
    const res = await api.updateSession(sid, { pinned })
    setSessions((prev) => prev.map((s) => (s.id === sid ? res.session : s)))
  }

  const handleRenameSession = async (sid, title) => {
    const res = await api.updateSession(sid, { title })
    setSessions((prev) => prev.map((s) => (s.id === sid ? res.session : s)))
  }

  const handleDeleteSession = async (sid) => {
    await api.deleteSession(sid)
    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== sid)
      if (currentSessionId === sid) {
        setCurrentSessionId(next.length > 0 ? next[0].id : null)
      }
      return next
    })
    showToast('会话已删除')
  }

  const handleClearSession = async (sid) => {
    const res = await api.clearSession(sid)
    setSessions((prev) => prev.map((s) => (s.id === sid ? res.session : s)))
    showToast('当前对话已清空')
  }

  const handleToggleFavorite = async (question) => {
    const res = await api.toggleFavorite(question)
    setFavorites(res.favorites || [])
    showToast(res.favorited ? '问题已收藏' : '已取消收藏')
  }

  const handleUpdateConfig = async (patch) => {
    const res = await api.updateConfig(patch)
    setAppConfig(res.appConfig)
    if (res.hotQuestions) {
      setHotQuestions(res.hotQuestions)
    }
  }

  const handleSetActiveModel = async (modelId) => {
    const res = await api.setActiveModel(modelId)
    setModels(res.models)
    setActiveModel(res.activeModel)
  }

  const handleAddModel = async (data) => {
    const res = await api.addModel(data)
    setModels(res.models)
    setActiveModel(res.activeModel)
  }

  const handleUpdateSources = async (sources) => {
    const res = await api.updateSources(sources)
    setDataSources(res.dataSources)
  }

  const handleSubmitFeedback = async (payload) => {
    const res = await api.createFeedback(payload)
    setFeedbacks(res.feedbacks || [])
    // 同步更新会话的 userFeedback 标记
    if (payload.session_id) {
      setSessions((prev) =>
        prev.map((s) => (s.id === payload.session_id ? { ...s, userFeedback: '数据有误' } : s))
      )
    }
    showToast('您的数据问题反馈已提交至「回复校对」，我们将尽快核查')
  }

  const handleUpdateFeedback = async (id, payload) => {
    const res = await api.updateFeedback(id, payload)
    setFeedbacks(res.feedbacks || [])
  }

  const pendingFbCount = feedbacks.filter((f) => f.status === '待处理').length

  return (
    <div className="app-layout" id="appLayout">
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
        {/* 顶部栏 */}
        <div className="top-bar">
          <div className="brand" style={{ cursor: 'pointer' }} onClick={() => setActivePage('ai-qa')}>
            <i className="fas fa-chart-line" /> AI问数
          </div>
          <div className="top-right">
            <div
              className="icon-btn"
              title={`待处理反馈校对：${pendingFbCount} 条`}
              onClick={() => setActivePage('sys-feedback-user')}
            >
              <i className="fas fa-bell" />
              {pendingFbCount > 0 && <span className="badge-dot" />}
            </div>
            <div
              className="avatar"
              id="userAvatar"
              onClick={() => setAvatarDropdownOpen((v) => !v)}
            >
              管
              <div className={`dropdown ${avatarDropdownOpen ? 'show' : ''}`} id="userDropdown">
                <div>
                  <i className="fas fa-user" /> 管理员（经管分析）
                </div>
                <div style={{ color: 'var(--text-hint)', fontSize: 14, cursor: 'default' }}>
                  <i className="fas fa-code-branch" /> v1.0.0 ({activeModel?.name || 'GPT-4o'})
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 主体区域：左侧导航 + 右侧内容 */}
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          <div className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`} id="sidebar">
            <div className="sidebar-menu" id="sidebarMenu">
              <div
                className={`menu-item ${activePage === 'ai-qa' ? 'active' : ''}`}
                onClick={() => setActivePage('ai-qa')}
              >
                <i className="fas fa-robot" />
                <span>智能问数</span>
              </div>

              <div>
                <div
                  className="menu-item has-sub"
                  onClick={() => setOpenMenus((p) => ({ ...p, system: !p.system }))}
                >
                  <i className="fas fa-cog" />
                  <span>系统管理</span>
                  <i className={`fas fa-chevron-right arrow ${openMenus.system ? 'open' : ''}`} />
                </div>
                <div className={`sub-menu ${openMenus.system ? 'open' : ''}`}>
                  <div
                    className={`menu-item ${activePage === 'sys-app' ? 'active' : ''}`}
                    onClick={() => setActivePage('sys-app')}
                  >
                    <i className="fas fa-sliders" />
                    <span>应用配置</span>
                  </div>
                  <div
                    className={`menu-item ${activePage === 'sys-model' ? 'active' : ''}`}
                    onClick={() => setActivePage('sys-model')}
                  >
                    <i className="fas fa-cube" />
                    <span>模型配置</span>
                  </div>
                </div>
              </div>

              <div>
                <div
                  className="menu-item has-sub"
                  onClick={() => setOpenMenus((p) => ({ ...p, feedback: !p.feedback }))}
                >
                  <i className="fas fa-flag" />
                  <span>反馈管理</span>
                  <i className={`fas fa-chevron-right arrow ${openMenus.feedback ? 'open' : ''}`} />
                </div>
                <div className={`sub-menu ${openMenus.feedback ? 'open' : ''}`}>
                  <div
                    className={`menu-item ${activePage === 'sys-feedback-user' ? 'active' : ''}`}
                    onClick={() => setActivePage('sys-feedback-user')}
                  >
                    <i className="fas fa-exclamation-circle" />
                    <span>回复校对</span>
                    {pendingFbCount > 0 && (
                      <span
                        style={{
                          marginLeft: 'auto',
                          background: '#EF4444',
                          color: '#fff',
                          borderRadius: 10,
                          fontSize: 11,
                          padding: '1px 6px',
                          lineHeight: 1.3,
                        }}
                      >
                        {pendingFbCount}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="sidebar-footer">
              <button
                className="sidebar-toggle"
                onClick={() => setSidebarCollapsed((v) => !v)}
                title="收起/展开侧边栏"
              >
                <i className="fas fa-chevron-left" />
              </button>
            </div>
          </div>

          <div className="main-wrap">
            <div className="content-area" id="contentArea">
              {activePage === 'ai-qa' && (
                <AiQaPage
                  sessions={sessions}
                  currentSessionId={currentSessionId}
                  setCurrentSessionId={setCurrentSessionId}
                  appConfig={appConfig}
                  dataSources={dataSources}
                  favorites={favorites}
                  hotQuestions={hotQuestions}
                  onNewChat={handleNewChat}
                  onSendChat={handleSendChat}
                  onPinSession={handlePinSession}
                  onRenameSession={handleRenameSession}
                  onDeleteSession={handleDeleteSession}
                  onClearSession={handleClearSession}
                  onToggleFavorite={handleToggleFavorite}
                  onUpdateSources={handleUpdateSources}
                  onSubmitFeedback={handleSubmitFeedback}
                  showToast={showToast}
                  collapseMainSidebar={() => setSidebarCollapsed(true)}
                />
              )}

              {activePage === 'sys-app' && (
                <AppConfigPage
                  appConfig={appConfig}
                  onUpdateConfig={handleUpdateConfig}
                  onNavigate={setActivePage}
                  showToast={showToast}
                />
              )}

              {activePage === 'sys-model' && (
                <ModelConfigPage
                  models={models}
                  activeModel={activeModel}
                  onSetActiveModel={handleSetActiveModel}
                  onTestModel={api.testModel}
                  onAddModel={handleAddModel}
                  showToast={showToast}
                />
              )}

              {activePage === 'sys-feedback-user' && (
                <FeedbackPage
                  feedbacks={feedbacks}
                  onUpdateFeedback={handleUpdateFeedback}
                  showToast={showToast}
                />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 全局 Toast 提示 */}
      {toastMsg && (
        <div
          style={{
            position: 'fixed',
            top: 84,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 9999,
            background: '#1F2937',
            color: '#fff',
            padding: '10px 20px',
            borderRadius: 8,
            fontSize: 15,
            boxShadow: '0 4px 12px rgba(0,0,0,.2)',
            pointerEvents: 'none',
            whiteSpace: 'nowrap',
          }}
        >
          {toastMsg}
        </div>
      )}
    </div>
  )
}
