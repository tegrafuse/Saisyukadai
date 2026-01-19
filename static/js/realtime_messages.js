// Message chat with auto-scroll and partner badge updates
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
  
  // Update partner list badge (for the currently active conversation)
  function updatePartnerBadge() {
    fetch(`/api/partner-unread-count/${username}`)
      .then(r => r.json())
      .then(data => {
        const partnerLink = document.querySelector(`[data-partner-username="${username}"]`);
        if (!partnerLink) return;
        
        let badgeEl = partnerLink.querySelector('.partner-unread-badge');
        const unreadCount = data.unread_count || 0;
        
        if (unreadCount > 0) {
          if (!badgeEl) {
            // Create badge if it doesn't exist
            badgeEl = document.createElement('span');
            badgeEl.className = 'badge bg-danger rounded-pill partner-unread-badge';
            badgeEl.dataset.unreadCount = unreadCount;
            partnerLink.appendChild(badgeEl);
          }
          badgeEl.textContent = unreadCount;
          badgeEl.style.display = 'inline-block';
        } else {
          // Remove badge if count is 0
          if (badgeEl) {
            badgeEl.remove();
          }
        }
      })
      .catch(e => console.log('partner badge update error', e));
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
  
  // Store message states to track read status changes
  const messageStates = {};
  
  // Polling for new messages and read status updates
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
            // New message
            existing.add(msg.id);
            newAdded = true;
            messageStates[msg.id] = { is_read: msg.is_read, sender_id: msg.sender_id };
            
            const msgEl = document.createElement('div');
            msgEl.className = 'd-flex mb-2';
            if (msg.sender_id === currentUserId) msgEl.className += ' justify-content-end';
            msgEl.dataset.messageId = msg.id;
            
            const isSender = msg.sender_id === currentUserId;
            const senderUsername = isSender ? document.body.dataset.currentUsername : username;
            const avatarImg = msg.sender_avatar ? `<img src="/uploads/${msg.sender_avatar}" class="rounded-circle" style="width:36px;height:36px;object-fit:cover">` : '<div class="logo" style="width:36px;height:36px"></div>';
            const avatar = `<a href="/user/${senderUsername}" class="text-decoration-none">${avatarImg}</a>`;
            
            if (isSender) {
              msgEl.innerHTML = `
                <div class="me-2 text-end" style="max-width:70%">
                  <div class="bubble bubble-right">${escapeHtml(msg.body)}</div>
                  <div class="text-muted small mt-1"><span class="msg-time">${msg.created_at}</span><span class="msg-read-mark">${msg.recipient_id && msg.is_read ? '<span class="ms-1 text-muted" style="font-size:0.85em">✓ 既読</span>' : ''}</span></div>
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
          } else {
            // Existing message - check for read status changes
            if (messageStates[msg.id] !== undefined && !messageStates[msg.id].is_read && msg.is_read) {
              // Read status changed from false to true
              messageStates[msg.id].is_read = true;
              
              const msgEl = chatDiv.querySelector(`[data-message-id="${msg.id}"]`);
              if (msgEl) {
                const readMark = msgEl.querySelector('.msg-read-mark');
                if (readMark) {
                  readMark.innerHTML = '<span class="ms-1 text-muted" style="font-size:0.85em">✓ 既読</span>';
                }
              }
            } else if (messageStates[msg.id] === undefined) {
              // Initialize state for existing messages
              messageStates[msg.id] = { is_read: msg.is_read, sender_id: msg.sender_id };
            }
          }
        });
        
        // After new messages are added, update the partner badge
        if (newAdded) {
          updatePartnerBadge();
          if (wasBottom) setTimeout(scrollBottom, 10);
        }
      })
      .catch(e => console.log('poll error', e));
  }, 1000);
  
  // Update partner badge every 1 second to keep it in sync
  setInterval(updatePartnerBadge, 1000);
  
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
