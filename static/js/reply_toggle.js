// Toggle main reply form
document.addEventListener('DOMContentLoaded', function() {
  console.log('[reply_toggle] Script loaded');
  
  const mainReplyToggle = document.getElementById('main-reply-toggle');
  const mainReplyForm = document.getElementById('main-reply-form');
  
  console.log('[reply_toggle] mainReplyToggle:', mainReplyToggle);
  console.log('[reply_toggle] mainReplyForm:', mainReplyForm);
  
  if (mainReplyToggle && mainReplyForm) {
    mainReplyToggle.addEventListener('click', function() {
      console.log('[reply_toggle] Main reply toggle clicked');
      if (mainReplyForm.style.display === 'none') {
        mainReplyForm.style.display = 'block';
        mainReplyToggle.textContent = '💬 返信を隠す';
        console.log('[reply_toggle] Form shown');
      } else {
        mainReplyForm.style.display = 'none';
        mainReplyToggle.textContent = '💬 返信する';
        console.log('[reply_toggle] Form hidden');
      }
    });
  }

  // Toggle nested reply forms
  const replyToggleBtns = document.querySelectorAll('.reply-toggle-btn');
  console.log('[reply_toggle] Found ' + replyToggleBtns.length + ' nested reply toggle buttons');
  
  replyToggleBtns.forEach(function(btn) {
    btn.addEventListener('click', function() {
      const replyId = this.getAttribute('data-reply-id');
      const form = document.getElementById('reply-form-' + replyId);
      console.log('[reply_toggle] Nested reply toggle clicked for reply:', replyId, 'form:', form);
      if (form) {
        if (form.style.display === 'none') {
          form.style.display = 'block';
          this.textContent = '💬 返信を隠す';
          console.log('[reply_toggle] Form shown for reply:', replyId);
        } else {
          form.style.display = 'none';
          this.textContent = '💬 返信';
          console.log('[reply_toggle] Form hidden for reply:', replyId);
        }
      }
    });
  });
});
