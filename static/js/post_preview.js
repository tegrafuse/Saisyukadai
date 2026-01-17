document.addEventListener('DOMContentLoaded', function(){
  // Unified file input for post images and videos
  const postFileInput = document.getElementById('post-file-input');
  if(postFileInput){
    const mediaPreview = document.getElementById('post-media-preview');
    const imagesPreview = document.getElementById('post-images-preview');
    const videoPreview = document.getElementById('post-video-preview');
    const removeBtn = document.getElementById('post-remove-media');
    
    // Track selected files
    let selectedImages = [];
    let selectedVideo = null;
    
    function updatePreview() {
      imagesPreview.innerHTML = '';
      videoPreview.innerHTML = '';
      
      // Display images (max 4)
      selectedImages.slice(0, 4).forEach((file, idx) => {
        const url = URL.createObjectURL(file);
        const div = document.createElement('div');
        div.className = 'mb-2';
        div.innerHTML = `
          <div class="d-flex gap-2 align-items-center">
            <img src="${url}" class="img-thumbnail" style="width:80px;height:80px;object-fit:cover">
            <div>
              <p class="mb-1 small">${file.name}</p>
              <button type="button" class="btn btn-sm btn-outline-danger remove-image" data-index="${idx}">削除</button>
            </div>
          </div>
        `;
        imagesPreview.appendChild(div);
      });
      
      // Display video (max 1)
      if(selectedVideo) {
        const url = URL.createObjectURL(selectedVideo);
        videoPreview.innerHTML = `
          <div class="mb-2">
            <p class="mb-2 small">動画: ${selectedVideo.name}</p>
            <video controls style="max-width:300px;max-height:240px;border-radius:8px">
              <source src="${url}">
            </video>
            <div class="mt-2">
              <button type="button" class="btn btn-sm btn-outline-danger" id="remove-video">削除</button>
            </div>
          </div>
        `;
      }
      
      // Show/hide preview container
      if(selectedImages.length > 0 || selectedVideo) {
        mediaPreview.style.display = 'block';
      } else {
        mediaPreview.style.display = 'none';
        postFileInput.value = '';
      }
      
      // Attach event listeners to remove buttons
      document.querySelectorAll('.remove-image').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          const idx = parseInt(btn.dataset.index);
          selectedImages.splice(idx, 1);
          updatePreview();
          updateFileInput();
        });
      });
      
      const removeVideoBtn = document.getElementById('remove-video');
      if(removeVideoBtn) {
        removeVideoBtn.addEventListener('click', (e) => {
          e.preventDefault();
          selectedVideo = null;
          updatePreview();
          updateFileInput();
        });
      }
    }
    
    function updateFileInput() {
      // Create a new FileList-like object for form submission
      const dt = new DataTransfer();
      selectedImages.forEach(file => dt.items.add(file));
      if(selectedVideo) dt.items.add(selectedVideo);
      postFileInput.files = dt.files;
    }
    
    postFileInput.addEventListener('change', function(e){
      const files = Array.from(e.target.files);
      let hasImages = selectedImages.length > 0;
      let hasVideo = selectedVideo !== null;
      let newImages = [];
      let newVideo = null;
      
      files.forEach(file => {
        const isImage = file.type.startsWith('image/');
        const isVideo = file.type.startsWith('video/');
        
        if(isImage) {
          // Can't mix images and video
          if(hasVideo) {
            alert('動画が既に選択されています。画像と動画は同時に添付できません。');
            return;
          }
          // Max 4 images
          if(selectedImages.length + newImages.length < 4) {
            newImages.push(file);
          } else {
            alert('画像は最大4個まで選択できます。');
          }
        } else if(isVideo) {
          // Can't mix images and video
          if(hasImages || newImages.length > 0) {
            alert('画像が既に選択されています。画像と動画は同時に添付できません。');
            return;
          }
          // Max 1 video
          if(!hasVideo && !newVideo) {
            newVideo = file;
          } else {
            alert('動画は1つまでしか選択できません。');
          }
        }
      });
      
      selectedImages.push(...newImages);
      if(newVideo) selectedVideo = newVideo;
      
      updatePreview();
      updateFileInput();
    });
    
    if(removeBtn) {
      removeBtn.addEventListener('click', function(e){
        e.preventDefault();
        selectedImages = [];
        selectedVideo = null;
        updatePreview();
      });
    }
  }

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

  // post video preview (only on the feed page)
  const postVideoInput = document.getElementById('post-video-input');
  if(postVideoInput){
    const postVideoPreview = document.getElementById('post-video-preview');
    const postVideo = document.getElementById('post-preview-video');
    const postRemoveVideoBtn = document.getElementById('post-remove-video');
    postVideoInput.addEventListener('change', function(e){
      const file = e.target.files[0];
      if(!file) { postVideoPreview.style.display='none'; return }
      const url = URL.createObjectURL(file);
      postVideo.src = url; postVideoPreview.style.display='block';
    });
    if(postRemoveVideoBtn) postRemoveVideoBtn.addEventListener('click', function(){ postVideoInput.value=''; postVideo.src=''; postVideoPreview.style.display='none'; });
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
        btn.textContent = 'アバターを削除';
        btn.classList.remove('btn-danger');
        btn.classList.add('btn-outline-danger');
        if(currentImg) currentImg.style.display = '';
      } else {
        // mark for deletion
        hid.value = '1';
        btn.textContent = '削除取り消し';
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