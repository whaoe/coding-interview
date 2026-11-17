import React, { useState, useEffect } from 'react'

export default function ModelConfigPage({
  models,
  activeModel,
  onSetActiveModel,
  onTestModel,
  onAddModel,
  showToast,
}) {
  const [selectedId, setSelectedId] = useState(activeModel?.id || 1)
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [modelName, setModelName] = useState('')
  const [testState, setTestState] = useState({ status: 'idle', msg: '' }) // 'idle' | 'testing' | 'ok' | 'err'

  useEffect(() => {
    if (activeModel?.id) {
      setSelectedId(activeModel.id)
    }
  }, [activeModel])

  const handleSelectChange = (e) => {
    const val = e.target.value
    if (val === '__add__') {
      setBaseUrl('')
      setApiKey('')
      setModelName('')
      setTestState({ status: 'idle', msg: '' })
      setAddModalOpen(true)
      return
    }
    setSelectedId(Number(val))
  }

  const handleSave = async () => {
    if (!selectedId) {
      showToast('请选择一个模型')
      return
    }
    await onSetActiveModel(selectedId)
    showToast('模型配置已保存')
  }

  const handleTest = async () => {
    if (!baseUrl.trim() || !apiKey.trim() || !modelName.trim()) {
      setTestState({ status: 'err', msg: '请填写完整的 Base URL、API Key 和 Model Name' })
      return
    }
    setTestState({ status: 'testing', msg: '测试中...' })
    try {
      const res = await onTestModel({
        baseUrl: baseUrl.trim(),
        apiKey: apiKey.trim(),
        modelName: modelName.trim(),
      })
      setTestState({ status: 'ok', msg: res.message || '连接成功' })
    } catch (err) {
      setTestState({ status: 'err', msg: err.message || '连接失败' })
    }
  }

  const handleConfirmAdd = async () => {
    if (testState.status !== 'ok') return
    await onAddModel({
      baseUrl: baseUrl.trim(),
      apiKey: apiKey.trim(),
      modelName: modelName.trim(),
    })
    setAddModalOpen(false)
    showToast('新模型已添加并设为当前激活模型')
  }

  return (
    <div className="page-content active" id="page-sys-model" style={{ padding: 20 }}>
      <div className="breadcrumb">
        系统管理 <span className="sep">/</span> <span>模型配置</span>
      </div>
      <div className="card" style={{ padding: 20 }}>
        <div className="model-config">
          <div className="mc-title">
            <i className="fas fa-cube" style={{ color: 'var(--primary)', marginRight: 6 }} />
            应用模型设置
          </div>
          <div className="mc-subtitle">选择AI问答使用的LLM模型（支持自定义接入 OpenAI 兼容接口）</div>

          <div className="mc-card">
            <div className="mc-card-hdr">
              <span className="mc-card-title">
                <i className="fas fa-robot" /> 智能问数模型
              </span>
              <select id="mcModel0" value={selectedId} onChange={handleSelectChange}>
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
                <option value="__add__" style={{ color: 'var(--primary)', fontWeight: 600 }}>
                  ── 新增模型 ──
                </option>
              </select>
            </div>
            <div className="mc-card-body">
              用于智能问数、经营指标问答、台账数据分析（当前生效：{activeModel?.name || 'GPT-4o'}）
            </div>
          </div>

          <div className="mc-actions">
            <button className="btn btn-outline btn-sm" onClick={handleSave}>
              <i className="fas fa-save" /> 保存配置
            </button>
          </div>
        </div>
      </div>

      {/* 新增模型弹窗 */}
      <div
        className={`modal-overlay ${addModalOpen ? 'show' : ''}`}
        onClick={(e) => e.target === e.currentTarget && setAddModalOpen(false)}
      >
        <div className="modal" style={{ width: 480 }}>
          <div className="modal-header">
            <h3>
              <i className="fas fa-plus-circle" /> 新增模型
            </h3>
            <button className="close-btn" onClick={() => setAddModalOpen(false)}>
              <i className="fas fa-times" />
            </button>
          </div>
          <div className="modal-body">
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                Base URL <span style={{ color: 'var(--danger)' }}>*</span>
              </label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => {
                  setBaseUrl(e.target.value)
                  setTestState({ status: 'idle', msg: '' })
                }}
                placeholder="https://api.openai.com/v1"
                style={{
                  width: '100%',
                  height: 40,
                  padding: '0 12px',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  fontSize: 15,
                  outline: 'none',
                  background: 'var(--bg-muted)',
                  color: 'var(--text-body)',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                API Key <span style={{ color: 'var(--danger)' }}>*</span>
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value)
                  setTestState({ status: 'idle', msg: '' })
                }}
                placeholder="sk-..."
                style={{
                  width: '100%',
                  height: 40,
                  padding: '0 12px',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  fontSize: 15,
                  outline: 'none',
                  background: 'var(--bg-muted)',
                  color: 'var(--text-body)',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            <div style={{ marginBottom: 8 }}>
              <label style={{ display: 'block', fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                Model Name <span style={{ color: 'var(--danger)' }}>*</span>
              </label>
              <input
                type="text"
                value={modelName}
                onChange={(e) => {
                  setModelName(e.target.value)
                  setTestState({ status: 'idle', msg: '' })
                }}
                placeholder="gpt-4o / deepseek-chat"
                style={{
                  width: '100%',
                  height: 40,
                  padding: '0 12px',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  fontSize: 15,
                  outline: 'none',
                  background: 'var(--bg-muted)',
                  color: 'var(--text-body)',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            <div style={{ fontSize: 15, minHeight: 22, marginTop: 4 }}>
              {testState.status === 'testing' && (
                <span>
                  <i className="fas fa-spinner fa-spin" /> {testState.msg}
                </span>
              )}
              {testState.status === 'ok' && (
                <span style={{ color: 'var(--success)' }}>
                  <i className="fas fa-check-circle" /> {testState.msg}
                </span>
              )}
              {testState.status === 'err' && (
                <span style={{ color: 'var(--warning)' }}>
                  <i className="fas fa-exclamation-circle" /> {testState.msg}
                </span>
              )}
            </div>
          </div>
          <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between' }}>
            <button className="btn btn-outline btn-sm" onClick={handleTest}>
              <i className="fas fa-plug" /> 测试连接
            </button>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-text" onClick={() => setAddModalOpen(false)}>取消</button>
              <button
                className="btn btn-primary"
                disabled={testState.status !== 'ok'}
                style={{ opacity: testState.status === 'ok' ? 1 : 0.5 }}
                onClick={handleConfirmAdd}
              >
                添加
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
