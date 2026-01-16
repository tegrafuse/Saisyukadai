// Message chat with auto-scroll
(function() {
  const chatDiv = document.querySelector('.chat');
  if (!chatDiv) return;
  
  // Get username - try multiple ways
  let username = document.body.dataset.otherUsername;
  if (!username) {
    const threadUsernameEl = document.getElementById('thread-username-data');
    username = threadUsernameEl ? threadUsernameEl.value : null;
  }
  
  if (!username) return;
  
  // Get current user ID
  const currentUserId = parseInt(document.body.dataset.currentUserId || 0);
  
  // Get the form
  const form = document.querySelector('form[action*="/messages"]');
  if (!form) return;
  
  // Helper: Scroll to bottom
  function scrollBottom() {
    chatDiv.scrollTop = chatDiv.scrollHeight;
  }
  
  // Helper: Check if at bottom
  function isAtBottom() {
    return (chatDiv.scrollHeight - chatDiv.scrollTop - chatDiv.clientHeight) < 100;
  }
  
  // Initial scroll on load - multiple attempts
  scrollBottom();
  setTimeout(scrollBottom, 0);
  setTimeout(scrollBottom, 10);
  setTimeout(scrollBottom, 50);
  setTimeout(scrollBottom, 100);
  setTimeout(scrollBottom, 200);
  
  window.addEventListener('load', () => {
    scrollBottom();
    setTimeout(scrollBottom, 50);
  });
  
  // Polling for new messages
  setInterval(() => {
    fetch(`/api/messages/${username}`)
      .then(r => r.json())
      .then(data => {
        if (!data.messages) return;
        
        const existing = new Set([...chatDiv.querySelectorAll('[data-message-id]')].map(el => parseInt(el.dataset.messageId)));
        const wasBottom = isAtBottom();
        let newAdded = false;
        
        data.messages.forEach(msg => {
          if (!existing.has(msg.id)) {
            existing.add(msg.id);
            newAdded = true;
            
            const msgEl = document.createElement('div');
            msgEl.className = 'd-flex mb-2';
            if (msg.sender_id === currentUserId) msgEl.className += ' justify-content-end';
            msgEl.dataset.messageId = msg.id;
            
            const isSender = msg.sender_id === currentUserId;
            const avatar = msg.sender_avatar ? `<img src="/uploads/${msg.sender_avatar}" class="rounded-circle" style="width:36px;height:36px;object-fit:cover">` : '<div class="logo" style="width:36px;height:36px"></div>';
            
            if (isSender) {
              msgEl.innerHTML = `
                <div class="me-2 text-end" style="max-width:70%">
                  <div class="bubble bubble-right">${escapeHtml(msg.body)}</div>
                  <div class="text-muted small mt-1">${msg.created_at}${msg.is_read ? '<span class="ms-1 text-info">✓✓</span>' : ''}</div>
                </div>
                <div>${avatar}</div>
              `;
            } else {
              msgEl.innerHTML = `
                <div>${avatar}</div>
                <div class="ms-2" style="max-width:70%">
                  <div class="bubble bubble-left">${escapeHtml(msg.body)}</div>
                  <div class="text-muted small mt-1">${msg.created_at}</div>
                </div>
              `;
            }
            
            chatDiv.appendChild(msgEl);
          }
        });
        
        if (newAdded && wasBottom) setTimeout(scrollBottom, 10);
      })
      .catch(e => console.log('poll error', e));
  }, 2000);
  
  // Form submission
  form.addEventListener('submit', e => {
    e.preventDefault();
    
    const textarea = form.querySelector('textarea[name="body"]');
    const msg = textarea.value.trim();
    if (!msg) return;
    
    const btn = form.querySelector('button');
    const wasBottom = isAtBottom();
    btn.disabled = true;
    
    fetch(form.action, { method: 'POST', body: new FormData(form) })
      .then(r => r.text())
      .then(() => {
        textarea.value = '';
        btn.disabled = false;
        if (wasBottom) setTimeout(scrollBottom, 50);
      })
      .catch(e => { console.error(e); btn.disabled = false; });
  });
  
  function escapeHtml(text) {
    const el = document.createElement('div');
    el.textContent = text;
    return el.innerHTML;
  }
})();
