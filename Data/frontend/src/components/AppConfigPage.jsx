import React, { useState } from 'react'

export default function AppConfigPage({ appConfig, onUpdateConfig, onNavigate, showToast }) {
  const [greetingModalOpen, setGreetingModalOpen] = useState(false)
  const [greetingText, setGreetingText] = useState('')
  const [greetingQuestions, setGreetingQuestions] = useState([])

  const [hotModalOpen, setHotModalOpen] = useState(false)
  const [hotThreshold, setHotThreshold] = useState(3)

  const handleToggle = async (key) => {
    await onUpdateConfig({ [key]: !appConfig[key] })
    showToast('配置已更新')
  }

  const openGreetingModal = () => {
    setGreetingText(appConfig.greetingText || '')
    setGreetingQuestions([...(appConfig.greetingQuestions || [])])
    setGreetingModalOpen(true)
  }

  const saveGreeting = async () => {
    if (!greetingText.trim()) {
      showToast('开场白不能为空')
      return
    }
    const cleanQs = greetingQuestions.map((q) => q.trim()).filter(Boolean)
    await onUpdateConfig({
      greetingText: greetingText.trim(),
      greetingQuestions: cleanQs,
    })
    setGreetingModalOpen(false)
    showToast('对话开场白已保存')
  }

  const openHotModal = () => {
    setHotThreshold(appConfig.hotThreshold || 3)
    setHotModalOpen(true)
  }

  const saveHotConfig = async () => {
    const val = Math.max(1, parseInt(hotThreshold, 10) || 3)
    await onUpdateConfig({ hotThreshold: val })
    setHotModalOpen(false)
    showToast('常问频次阈值已保存')
  }

  return (
    <div className="page-content active" id="page-sys-app" style={{ padding: 20 }}>
      <div className="breadcrumb">
        系统管理 <span className="sep">/</span> <span>应用配置</span>
      </div>
      <div className="card" style={{ padding: 20 }}>
        <div className="app-config-grid">
          {/* 1. 对话开场白 */}
          <div className="app-card">
            <div className="app-card-top">
              <div className="app-card-icon" style={{ background: '#E8F0FE', color: '#2563EB' }}>
                <i className="fas fa-comments" />
              </div>
              <span className="app-card-name">对话开场白</span>
              <div className="app-card-actions">
                <button className="app-card-set" onClick={openGreetingModal} title="配置开场白">
                  <i className="fas fa-cog" />
                </button>
                <div
                  className={`toggle ${appConfig.greeting ? 'on' : ''}`}
                  onClick={() => handleToggle('greeting')}
                />
              </div>
            </div>
            <div className="app-card-desc">
              开启后，新对话将自动显示开场白引导语（如“欢迎使用智能AI问数...”）及推荐问题卡片
            </div>
          </div>

          {/* 2. 下一步问题建议 */}
          <div className="app-card">
            <div className="app-card-top">
              <div className="app-card-icon" style={{ background: '#FEF3C7', color: '#D97706' }}>
                <i className="fas fa-list" />
              </div>
              <span className="app-card-name">下一步问题建议</span>
              <div className="app-card-actions">
                <div
                  className={`toggle ${appConfig.suggestions ? 'on' : ''}`}
                  onClick={() => handleToggle('suggestions')}
                />
              </div>
            </div>
            <div className="app-card-desc">
              开启后，AI回复下方自动生成3条相关延伸问题提示条
            </div>
          </div>

          {/* 3. 文字转语音 */}
          <div className="app-card">
            <div className="app-card-top">
              <div className="app-card-icon" style={{ background: '#F0FDF4', color: '#16A34A' }}>
                <i className="fas fa-volume-up" />
              </div>
              <span className="app-card-name">文字转语音</span>
              <div className="app-card-actions">
                <div
                  className={`toggle ${appConfig.tts ? 'on' : ''}`}
                  onClick={() => handleToggle('tts')}
                />
              </div>
            </div>
            <div className="app-card-desc">开启后，AI回答支持语音播报功能</div>
          </div>

          {/* 4. 语音转文字 */}
          <div className="app-card">
            <div className="app-card-top">
              <div className="app-card-icon" style={{ background: '#F3E8FF', color: '#9333EA' }}>
                <i className="fas fa-microphone" />
              </div>
              <span className="app-card-name">语音转文字</span>
              <div className="app-card-actions">
                <div
                  className={`toggle ${appConfig.stt ? 'on' : ''}`}
                  onClick={() => handleToggle('stt')}
                />
              </div>
            </div>
            <div className="app-card-desc">开启后，支持通过语音输入问题</div>
          </div>

          {/* 5. 模型配置 */}
          <div className="app-card">
            <div className="app-card-top">
              <div className="app-card-icon" style={{ background: '#E8F0FE', color: '#2563EB' }}>
                <i className="fas fa-cube" />
              </div>
              <span className="app-card-name">模型配置</span>
              <div className="app-card-actions">
                <button
                  className="app-card-set"
                  onClick={() => onNavigate('sys-model')}
                  title="配置模型"
                >
                  <i className="fas fa-cog" />
                </button>
                <div
                  className={`toggle ${appConfig.modelConfig ? 'on' : ''}`}
                  onClick={() => handleToggle('modelConfig')}
                />
              </div>
            </div>
            <div className="app-card-desc">配置各业务场景使用的AI模型</div>
          </div>

          {/* 6. 常问设置 */}
          <div className="app-card">
            <div className="app-card-top">
              <div className="app-card-icon" style={{ background: '#FEF3C7', color: '#D97706' }}>
                <i className="fas fa-fire" />
              </div>
              <span className="app-card-name">常问设置</span>
              <div className="app-card-actions">
                <button className="app-card-set" onClick={openHotModal} title="配置常问设置">
                  <i className="fas fa-cog" />
                </button>
                <div
                  className={`toggle ${appConfig.hotRecommend ? 'on' : ''}`}
                  onClick={() => handleToggle('hotRecommend')}
                />
              </div>
            </div>
            <div className="app-card-desc">
              根据经常提问频次（当前阈值 ≥ {appConfig.hotThreshold} 次），在快捷提问中能看到常问问题
            </div>
          </div>
        </div>
      </div>

      {/* 开场白配置弹窗 */}
      <div
        className={`modal-overlay ${greetingModalOpen ? 'show' : ''}`}
        onClick={(e) => e.target === e.currentTarget && setGreetingModalOpen(false)}
      >
        <div className="modal" style={{ width: 560 }}>
          <div className="modal-header">
            <h3>
              <i className="fas fa-comments" style={{ color: 'var(--primary)' }} /> 对话开场白
            </h3>
            <button className="close-btn" onClick={() => setGreetingModalOpen(false)}>
              <i className="fas fa-times" />
            </button>
          </div>
          <div className="modal-body">
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>
                开场白文案
              </label>
              <textarea
                value={greetingText}
                onChange={(e) => setGreetingText(e.target.value)}
                placeholder="请输入欢迎开场白…"
                style={{
                  width: '100%',
                  height: 80,
                  padding: 10,
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  fontSize: 15,
                  resize: 'vertical',
                  outline: 'none',
                  boxSizing: 'border-box',
                  background: 'var(--bg-muted)',
                  color: 'var(--text-body)',
                  fontFamily: 'inherit',
                }}
              />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <label style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>
                  开场问题 · <span>{greetingQuestions.length}</span>/10
                </label>
                <button
                  type="button"
                  className={`btn btn-text btn-sm ${greetingQuestions.length >= 10 ? 'disabled' : ''}`}
                  onClick={() => {
                    if (greetingQuestions.length < 10) {
                      setGreetingQuestions((prev) => [...prev, ''])
                    }
                  }}
                >
                  <i className="fas fa-plus" /> 添加开场问题
                </button>
              </div>
              <div>
                {greetingQuestions.map((q, idx) => (
                  <div className="gq-row" key={idx}>
                    <input
                      className="gq-input"
                      value={q}
                      placeholder="请输入快捷问题"
                      maxLength={100}
                      onChange={(e) => {
                        const val = e.target.value
                        setGreetingQuestions((prev) => prev.map((item, i) => (i === idx ? val : item)))
                      }}
                    />
                    <button
                      type="button"
                      className="gq-del"
                      onClick={() => setGreetingQuestions((prev) => prev.filter((_, i) => i !== idx))}
                    >
                      <i className="fas fa-times" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <button className="btn btn-text" onClick={() => setGreetingModalOpen(false)}>
              <i className="fas fa-times" /> 取消
            </button>
            <button className="btn btn-primary" onClick={saveGreeting}>
              <i className="fas fa-check" /> 保存
            </button>
          </div>
        </div>
      </div>

      {/* 常问设置弹窗 */}
      <div
        className={`modal-overlay ${hotModalOpen ? 'show' : ''}`}
        onClick={(e) => e.target === e.currentTarget && setHotModalOpen(false)}
      >
        <div className="modal" style={{ width: 480 }}>
          <div className="modal-header">
            <h3>
              <i className="fas fa-fire" /> 常问设置
            </h3>
            <button className="close-btn" onClick={() => setHotModalOpen(false)}>
              <i className="fas fa-times" />
            </button>
          </div>
          <div className="modal-body">
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                问题频次阈值
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input
                  type="number"
                  min={1}
                  value={hotThreshold}
                  onChange={(e) => setHotThreshold(e.target.value)}
                  style={{
                    width: 100,
                    height: 36,
                    padding: '0 10px',
                    border: '1px solid var(--border)',
                    borderRadius: 6,
                    fontSize: 15,
                    outline: 'none',
                    background: 'var(--bg-muted)',
                    color: 'var(--text-body)',
                  }}
                />
                <span style={{ fontSize: 14, color: 'var(--text-hint)' }}>
                  次（同一问题出现次数达到此值即视为常问）
                </span>
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button className="btn btn-text" onClick={() => setHotModalOpen(false)}>取消</button>
            <button className="btn btn-primary" onClick={saveHotConfig}>保存</button>
          </div>
        </div>
      </div>
    </div>
  )
}
