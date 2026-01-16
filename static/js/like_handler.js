// Like button handler using Ajax
document.addEventListener('DOMContentLoaded', function() {
  console.log('[like_handler] Script loaded');
  
  // Handle all like buttons with event delegation
  document.body.addEventListener('click', function(e) {
    const likeBtn = e.target.closest('.like-btn');
    if (!likeBtn) return;
    
    e.preventDefault();
    e.stopPropagation();
    
    console.log('[like_handler] Like button clicked');
    
    const postId = likeBtn.dataset.postId;
    const replyId = likeBtn.dataset.replyId;
    const isLiked = likeBtn.dataset.liked === 'true';
    
    console.log(`[like_handler] postId=${postId}, replyId=${replyId}, isLiked=${isLiked}`);
    
    let url;
    if (postId) {
      url = isLiked ? `/post/${postId}/unlike` : `/post/${postId}/like`;
    } else if (replyId) {
      url = isLiked ? `/reply/${replyId}/unlike` : `/reply/${replyId}/like`;
    } else {
      console.warn('[like_handler] Neither postId nor replyId found');
      return;
    }
    
    console.log(`[like_handler] Sending request to ${url}`);
    
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'same-origin'
    })
    .then(response => {
      console.log(`[like_handler] Response status: ${response.status}`);
      return response.json();
    })
    .then(data => {
      console.log('[like_handler] Response data:', data);
      
      if (data.success) {
        // Update button state
        likeBtn.dataset.liked = data.liked.toString();
        
        // Update button appearance
        if (data.liked) {
          likeBtn.classList.remove('btn-outline-secondary');
          likeBtn.classList.add('btn-danger');
        } else {
          likeBtn.classList.remove('btn-danger');
          likeBtn.classList.add('btn-outline-secondary');
        }
        
        // Update button text and count
        const icon = data.liked ? '❤️' : '🤍';
        const countText = data.like_count > 0 ? `<span class="like-count">${data.like_count}</span>` : '';
        likeBtn.innerHTML = `${icon} いいね ${countText}`;
        
        console.log('[like_handler] Button updated successfully');
      } else if (data.error) {
        console.error('[like_handler] Error:', data.error);
        alert(data.error);
      }
    })
    .catch(error => {
      console.error('[like_handler] Fetch error:', error);
      alert('エラーが発生しました');
    });
  });
});


