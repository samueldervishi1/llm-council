import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { FRONTEND_VERSION } from '../config/api'
import './Settings.css'

function Settings({
  theme,
  onToggleTheme,
  mode,
  onModeChange,
  availableModels,
  selectedModels,
  onToggleModel,
  onSelectAllModels,
}) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState('general')

  // Handle URL tab parameter
  useEffect(() => {
    const tabParam = searchParams.get('tab')
    if (tabParam && ['general', 'models', 'about'].includes(tabParam)) {
      setActiveTab(tabParam)
    }
  }, [searchParams])

  // Update URL when tab changes
  const handleTabChange = (tab) => {
    setActiveTab(tab)
    setSearchParams({ tab })
  }

  const allSelected =
    availableModels.length > 0 && availableModels.every((m) => selectedModels.includes(m.id))

  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1>Settings</h1>
        <p className="settings-subtitle">Customize your LLM Council experience</p>
      </div>

      <div className="settings-tabs">
        <button
          className={`settings-tab ${activeTab === 'general' ? 'active' : ''}`}
          onClick={() => handleTabChange('general')}
        >
          General
        </button>
        <button
          className={`settings-tab ${activeTab === 'models' ? 'active' : ''}`}
          onClick={() => handleTabChange('models')}
        >
          Models
        </button>
        <button
          className={`settings-tab ${activeTab === 'about' ? 'active' : ''}`}
          onClick={() => handleTabChange('about')}
        >
          About
        </button>
      </div>

      <div className="settings-content">
        {activeTab === 'general' && (
          <div className="settings-section">
            <h2>Appearance</h2>
            <div className="settings-option">
              <div className="settings-option-info">
                <h3>Theme</h3>
                <p>Choose between light and dark mode</p>
              </div>
              <div className="settings-option-control">
                <button
                  className={`theme-option ${theme === 'light' ? 'active' : ''}`}
                  onClick={() => theme !== 'light' && onToggleTheme()}
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <circle cx="12" cy="12" r="5" />
                    <line x1="12" y1="1" x2="12" y2="3" />
                    <line x1="12" y1="21" x2="12" y2="23" />
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                    <line x1="1" y1="12" x2="3" y2="12" />
                    <line x1="21" y1="12" x2="23" y2="12" />
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                  </svg>
                  Light
                </button>
                <button
                  className={`theme-option ${theme === 'dark' ? 'active' : ''}`}
                  onClick={() => theme !== 'dark' && onToggleTheme()}
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                  </svg>
                  Dark
                </button>
              </div>
            </div>

            <h2>Council Mode</h2>
            <div className="settings-option">
              <div className="settings-option-info">
                <h3>Default Mode</h3>
                <p>Choose how the AI models interact</p>
              </div>
              <div className="settings-option-control mode-options">
                <button
                  className={`mode-option ${mode === 'formal' ? 'active' : ''}`}
                  onClick={() => onModeChange('formal')}
                >
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <path d="M9 14l2 2 4-4" />
                  </svg>
                  <div className="mode-option-text">
                    <span>Formal Council</span>
                    <small>Structured debate with voting</small>
                  </div>
                </button>
                <button
                  className={`mode-option ${mode === 'chat' ? 'active' : ''}`}
                  onClick={() => onModeChange('chat')}
                >
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  </svg>
                  <div className="mode-option-text">
                    <span>Group Chat</span>
                    <small>Free-flowing conversation</small>
                  </div>
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'models' && (
          <div className="settings-section">
            <div className="section-header">
              <div>
                <h2>Models</h2>
                <p className="section-description">
                  Select which models participate in discussions
                </p>
              </div>
              <button className="select-all-btn" onClick={onSelectAllModels}>
                {allSelected ? 'Deselect All' : 'Select All'}
              </button>
            </div>

            <div className="models-table-container">
              <table className="models-table">
                <thead>
                  <tr>
                    <th>Model Name</th>
                    <th>Role</th>
                    <th>Enable</th>
                  </tr>
                </thead>
                <tbody>
                  {availableModels.map((model) => (
                    <tr
                      key={model.id}
                      className={selectedModels.includes(model.id) ? 'selected' : ''}
                    >
                      <td className="model-name-cell">{model.name}</td>
                      <td className="model-role-cell">
                        {model.is_chairman ? (
                          <span className="chairman-badge">Chairman</span>
                        ) : (
                          <span className="member-text">Member</span>
                        )}
                      </td>
                      <td className="model-toggle-cell">
                        <label className="toggle-switch">
                          <input
                            type="checkbox"
                            checked={selectedModels.includes(model.id)}
                            onChange={() => onToggleModel(model.id)}
                          />
                          <span className="toggle-slider"></span>
                        </label>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'about' && (
          <div className="settings-section about-section">
            <div className="about-logo">
              <h2>LLM Council</h2>
            </div>
            <p className="about-version">Version {FRONTEND_VERSION}</p>
            <p className="about-description">
              A platform for orchestrating discussions between multiple AI models, allowing them to
              debate, collaborate, and reach consensus on complex questions.
            </p>

            <div className="about-links">
              <a
                href="https://llm-council-docs.netlify.app/"
                target="_blank"
                rel="noopener noreferrer"
                className="about-link"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                </svg>
                Documentation
              </a>
              <a
                href="https://github.com/your-repo/llm-council"
                target="_blank"
                rel="noopener noreferrer"
                className="about-link"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                </svg>
                GitHub
              </a>
            </div>

            <div className="about-shortcuts">
              <h3>Keyboard Shortcuts</h3>
              <div className="shortcuts-list">
                <div className="shortcut-item">
                  <span className="shortcut-keys">
                    <kbd>Ctrl</kbd> + <kbd>K</kbd>
                  </span>
                  <span className="shortcut-desc">Command palette</span>
                </div>
                <div className="shortcut-item">
                  <span className="shortcut-keys">
                    <kbd>Ctrl</kbd> + <kbd>/</kbd>
                  </span>
                  <span className="shortcut-desc">Command palette (alt)</span>
                </div>
                <div className="shortcut-item">
                  <span className="shortcut-keys">
                    <kbd>Alt</kbd> + <kbd>N</kbd>
                  </span>
                  <span className="shortcut-desc">New chat</span>
                </div>
                <div className="shortcut-item">
                  <span className="shortcut-keys">
                    <kbd>Ctrl</kbd> + <kbd>Enter</kbd>
                  </span>
                  <span className="shortcut-desc">Send message</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Settings
