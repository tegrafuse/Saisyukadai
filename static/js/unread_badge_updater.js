/**
 * Update unread message badge after reading messages
 * Calls the unread count API and updates the badge in the navbar
 */

document.addEventListener('DOMContentLoaded', function() {
  // Function to update unread badge
  function updateUnreadBadge() {
    fetch('/api/unread-count')
      .then(response => response.json())
      .then(data => {
        const unreadCount = data.unread_count;
        const badgeElement = document.getElementById('unread-badge');
        
        if (badgeElement) {
          if (unreadCount > 0) {
            badgeElement.textContent = unreadCount;
            badgeElement.style.display = 'inline-block';
          } else {
            badgeElement.style.display = 'none';
          }
        }

        // Also update partner conversation list badges if on messages page
        const partners = document.querySelectorAll('[data-partner-username]');
        partners.forEach(partner => {
          const username = partner.dataset.partnerUsername;
          const badgeEl = partner.querySelector('.partner-unread-badge');
          if (badgeEl) {
            // Get unread count for this specific partner from the element
            const count = parseInt(badgeEl.dataset.unreadCount || 0);
            if (count > 0 && !badgeEl.textContent) {
              badgeEl.textContent = count;
            }
          }
        });
      })
      .catch(err => console.error('Failed to update unread badge:', err));
  }

  // Update badge on page load
  updateUnreadBadge();

  // If on messages thread or messages page, update badge after a short delay
  // (to account for the is_read flag being set on the server)
  const chatDiv = document.querySelector('.chat');
  if (chatDiv) {
    setTimeout(updateUnreadBadge, 500);
  }

  // Periodically update unread badge every 5 seconds while viewing messages
  if (chatDiv) {
    setInterval(updateUnreadBadge, 5000);
  }
});
