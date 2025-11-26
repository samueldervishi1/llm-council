function TopBar({ onNewChat, onToggleSidebar }) {
  return (
    <div className="top-bar">
      <button className="menu-btn" onClick={onToggleSidebar}>
        &#9776;
      </button>
      <button className="new-chat-btn" onClick={onNewChat}>
        + New Chat
      </button>
    </div>
  )
}

export default TopBar
