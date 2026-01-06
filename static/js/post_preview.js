document.addEventListener('DOMContentLoaded', function(){
  // post image preview (only on the feed page)
  const postInput = document.getElementById('post-image-input');
  if(postInput){
    const postPreview = document.getElementById('post-image-preview');
    const postImg = document.getElementById('post-preview-img');
    const postRemoveBtn = document.getElementById('post-remove-image');
    postInput.addEventListener('change', function(e){
      const file = e.target.files[0];
      if(!file) { postPreview.style.display='none'; return }
      const url = URL.createObjectURL(file);
      postImg.src = url; postPreview.style.display='block';
    });
    if(postRemoveBtn) postRemoveBtn.addEventListener('click', function(){ postInput.value=''; postImg.src=''; postPreview.style.display='none'; });
  }

  // register/settings avatar preview (handles both IDs)
  const avatarPairs = [
    {input: document.getElementById('register-avatar-input'), preview: document.getElementById('register-avatar-preview'), img: document.getElementById('register-avatar-img'), remove: document.getElementById('register-avatar-remove')},
    {input: document.getElementById('settings-avatar-input'), preview: document.getElementById('settings-avatar-preview'), img: document.getElementById('settings-avatar-img'), remove: document.getElementById('settings-avatar-remove')}
  ];
  avatarPairs.forEach(pair => {
    if(!pair.input) return;
    pair.input.addEventListener('change', function(e){
      const file = e.target.files[0];
      if(!file){ if(pair.preview) pair.preview.style.display='none'; return }
      const url = URL.createObjectURL(file);
      if(pair.img) pair.img.src = url;
      if(pair.preview) pair.preview.style.display='block';
    });
    if(pair.remove) pair.remove.addEventListener('click', function(){ pair.input.value=''; if(pair.img) pair.img.src=''; if(pair.preview) pair.preview.style.display='none'; });
  });

  // generic handler for avatar inputs with preview targets
  document.querySelectorAll('.avatar-input').forEach(function(input){
    const targetId = input.dataset.previewTarget;
    const preview = targetId ? document.getElementById(targetId) : null;
    const img = preview ? preview.querySelector('img') : null;
    const removeBtn = preview ? preview.querySelector('button') : null;
    input.addEventListener('change', function(e){
      const file = e.target.files[0];
      console.debug('[avatar-input] change', input.id, file);
      // clear any pending remove-avatar marks when a new file is chosen
      const modalRemove = document.getElementById('remove_avatar_input_modal');
      const settingsRemove = document.getElementById('remove_avatar_input_settings');
      if(modalRemove) modalRemove.value = '';
      if(settingsRemove) settingsRemove.value = '';

      if(!file){ if(preview) preview.style.display='none'; return }
      const url = URL.createObjectURL(file);
      if(img) {
        img.src = url;
        img.onload = function(){ URL.revokeObjectURL(url); };
      }
      if(preview) preview.style.display='block';
      // hide current avatar display while previewing new file
      const currentModal = document.getElementById('current-avatar-block-modal');
      const currentSettings = document.getElementById('current-avatar-block-settings');
      if(currentModal) currentModal.style.display='none';
      if(currentSettings) currentSettings.style.display='none';
    });
    if(removeBtn) removeBtn.addEventListener('click', function(){ input.value=''; if(img) img.removeAttribute('src'); if(preview) preview.style.display='none';
      // also clear any remove flag if user removed the selected file
      const modalRemove = document.getElementById('remove_avatar_input_modal');
      const settingsRemove = document.getElementById('remove_avatar_input_settings');
      if(modalRemove) modalRemove.value = '';
      if(settingsRemove) settingsRemove.value = '';
      // show current avatar block again
      const currentModal = document.getElementById('current-avatar-block-modal');
      const currentSettings = document.getElementById('current-avatar-block-settings');
      if(currentModal) currentModal.style.display = '';
      if(currentSettings) currentSettings.style.display = '';
    });
  });

  // handle delete-avatar buttons (mark/unmark for deletion, toggle UI)
  function toggleRemove(buttonId, inputId, currentImgId){
    const btn = document.getElementById(buttonId);
    const hid = document.getElementById(inputId);
    const currentImg = document.getElementById(currentImgId);
    if(!btn || !hid) return;
    btn.addEventListener('click', function(){
      if(hid.value === '1'){
        // undo
        hid.value = '';
        btn.textContent = 'Delete avatar';
        btn.classList.remove('btn-danger');
        btn.classList.add('btn-outline-danger');
        if(currentImg) currentImg.style.display = '';
      } else {
        // mark for deletion
        hid.value = '1';
        btn.textContent = 'Marked for deletion (undo)';
        btn.classList.remove('btn-outline-danger');
        btn.classList.add('btn-danger');
        if(currentImg) currentImg.style.display = 'none';
        // also clear any selected new file preview
        const previewModal = document.getElementById('user-edit-avatar-preview');
        const previewSettings = document.getElementById('settings-avatar-preview');
        if(previewModal) previewModal.style.display='none';
        if(previewSettings) previewSettings.style.display='none';
        const inputModal = document.getElementById('user-edit-avatar-input');
        const inputSettings = document.getElementById('settings-avatar-input');
        if(inputModal) inputModal.value='';
        if(inputSettings) inputSettings.value='';
      }
    });
  }
  toggleRemove('remove_avatar_modal_button', 'remove_avatar_input_modal', 'current-avatar-img-modal');
  toggleRemove('remove_avatar_button', 'remove_avatar_input_settings', 'current-avatar-img-settings');
});