// Image Carousel Gallery Functionality
document.addEventListener('DOMContentLoaded', function() {
  console.log('[image_carousel] Script loaded');
  
  // Modal and image gallery management
  const modal = document.getElementById('imageCarouselModal');
  if (!modal) {
    console.warn('[image_carousel] Modal element not found');
    return;
  }

  const carouselImage = document.getElementById('carouselMainImage');
  const imageCounter = document.getElementById('imageCounter');
  const prevBtn = document.getElementById('prevImageBtn');
  const nextBtn = document.getElementById('nextImageBtn');

  console.log('[image_carousel] Modal elements found:', {modal, carouselImage, imageCounter, prevBtn, nextBtn});

  let currentPostId = null;
  let currentImageIndex = 0;
  let galleryImages = []; // Array of {filename, order}

  // Fetch all images for a post via API
  async function fetchPostImages(postId) {
    try {
      console.log('[image_carousel] Fetching images for post:', postId);
      const response = await fetch(`/api/post/${postId}/images`);
      if (!response.ok) throw new Error('Failed to fetch images');
      const data = await response.json();
      console.log('[image_carousel] Fetched images:', data);
      return data.images || [];
    } catch (error) {
      console.error('[image_carousel] Error fetching images:', error);
      return [];
    }
  }

  // Fetch all images for a reply via API
  async function fetchReplyImages(replyId) {
    try {
      console.log('[image_carousel] Fetching images for reply:', replyId);
      const response = await fetch(`/api/reply/${replyId}/images`);
      if (!response.ok) throw new Error('Failed to fetch images');
      const data = await response.json();
      console.log('[image_carousel] Fetched images:', data);
      return data.images || [];
    } catch (error) {
      console.error('[image_carousel] Error fetching images:', error);
      return [];
    }
  }

  // Fetch images when a thumbnail is clicked
  async function openCarousel(thumbnail) {
    const postId = thumbnail.dataset.postId;
    const replyId = thumbnail.dataset.replyId;
    const imageFilename = thumbnail.dataset.imageFilename;

    console.log('[image_carousel] Opening carousel - postId:', postId, 'replyId:', replyId, 'image:', imageFilename);

    // Fetch images based on whether it's a post or reply
    if (replyId) {
      galleryImages = await fetchReplyImages(replyId);
    } else if (postId) {
      galleryImages = await fetchPostImages(postId);
    } else {
      galleryImages = [];
    }

    // Fallback: if no images returned, use the clicked one only
    if (!galleryImages || galleryImages.length === 0) {
      galleryImages = [{ filename: imageFilename, order: 0 }];
    }

    // Find the index of clicked image
    currentImageIndex = galleryImages.findIndex(img => img.filename === imageFilename);
    if (currentImageIndex === -1) {
      currentImageIndex = 0;
    }
    currentPostId = postId || replyId || null;

    console.log('[image_carousel] Carousel opened with', galleryImages.length, 'images, starting at index:', currentImageIndex);

    // Display the image
    displayImage();

    // Show the modal
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
  }

  // Display current image with counter
  function displayImage() {
    if (galleryImages.length === 0) return;

    const currentImage = galleryImages[currentImageIndex];
    const uploadType = currentImage.upload_type || 'posts'; // Default to 'posts' if not specified
    const imageUrl = `/uploads/${uploadType}/${currentImage.filename}`;
    carouselImage.src = imageUrl;
    imageCounter.textContent = `${currentImageIndex + 1} / ${galleryImages.length}`;

    // Update button states
    prevBtn.disabled = currentImageIndex === 0;
    nextBtn.disabled = currentImageIndex === galleryImages.length - 1;
  }

  // Navigation functions
  function showPreviousImage() {
    if (currentImageIndex > 0) {
      currentImageIndex--;
      displayImage();
      console.log('[image_carousel] Showing previous image, index:', currentImageIndex);
    }
  }

  function showNextImage() {
    if (currentImageIndex < galleryImages.length - 1) {
      currentImageIndex++;
      displayImage();
      console.log('[image_carousel] Showing next image, index:', currentImageIndex);
    }
  }

  // Event listeners for thumbnail clicks
  document.addEventListener('click', function(e) {
    if (e.target.classList.contains('post-image-thumbnail')) {
      console.log('[image_carousel] Thumbnail clicked');
      openCarousel(e.target);
    }
  });

  // Event listeners for carousel buttons
  prevBtn.addEventListener('click', showPreviousImage);
  nextBtn.addEventListener('click', showNextImage);

  // Keyboard navigation (arrow keys)
  document.addEventListener('keydown', function(e) {
    // Only when modal is visible
    if (!modal.classList.contains('show')) return;

    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      showPreviousImage();
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      showNextImage();
    }
  });
});
