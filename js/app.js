/* ── State ── */
const state = {
  currentCategory: 'all',
  searchQuery: '',
  filteredPhotos: [],
  renderedCount: 0,
  pageSize: 12,
  currentLightboxIndex: -1,
  lightboxPhotos: [],
  isLoading: false,
  hasMore: true,
};

/* ── DOM refs ── */
const grid = document.getElementById('galleryGrid');
const loader = document.getElementById('galleryLoader');
const photoCount = document.getElementById('photoCount');
const tabs = document.querySelectorAll('.tab');
const searchInput = document.getElementById('searchInput');
const lightbox = document.getElementById('lightbox');
const lightboxImage = document.getElementById('lightboxImage');
const lightboxTitle = document.getElementById('lightboxTitle');
const lightboxTag = document.getElementById('lightboxTag');
const lightboxCounter = document.getElementById('lightboxCounter');
const lightboxThumbs = document.getElementById('lightboxThumbs');
const lightboxClose = document.getElementById('lightboxClose');
const lightboxPrev = document.getElementById('lightboxPrev');
const lightboxNext = document.getElementById('lightboxNext');

/* ── Filtering ── */
function getFilteredPhotos() {
  let photos = [...allPhotos];

  if (state.currentCategory !== 'all') {
    photos = photos.filter(p => p.category === state.currentCategory);
  }

  if (state.searchQuery.trim()) {
    const q = state.searchQuery.trim().toLowerCase();
    photos = photos.filter(p =>
      p.title.toLowerCase().includes(q) ||
      p.tags.some(t => t.toLowerCase().includes(q)) ||
      p.categoryLabel.includes(q)
    );
  }

  return photos;
}

/* ── Render ── */
function renderBatch(start, count) {
  const fragment = document.createDocumentFragment();
  const end = Math.min(start + count, state.filteredPhotos.length);

  for (let i = start; i < end; i++) {
    const photo = state.filteredPhotos[i];
    const item = document.createElement('div');
    item.className = 'grid-item';
    item.dataset.index = i;
    item.innerHTML = `
      <img src="${photo.url}" alt="${photo.title}" loading="lazy">
      <div class="card-overlay">
        <div class="card-title">${photo.title}</div>
        <span class="card-tag">${photo.categoryLabel}</span>
      </div>
    `;
    item.addEventListener('click', () => openLightbox(i));
    fragment.appendChild(item);
  }

  grid.appendChild(fragment);
  state.renderedCount = end;
  photoCount.textContent = state.filteredPhotos.length;
  state.hasMore = end < state.filteredPhotos.length;

  if (!state.hasMore) {
    loader.classList.remove('active');
  }
}

function renderGallery(reset = true) {
  if (reset) {
    grid.innerHTML = '';
    state.renderedCount = 0;
    state.hasMore = true;
  }

  state.filteredPhotos = getFilteredPhotos();

  if (state.filteredPhotos.length === 0) {
    grid.innerHTML = '<div class="empty-state">沒有找到符合條件的照片</div>';
    photoCount.textContent = '0';
    loader.classList.remove('active');
    return;
  }

  renderBatch(0, state.pageSize);

  if (state.hasMore) {
    loader.classList.add('active');
  } else {
    loader.classList.remove('active');
  }
}

/* ── Load More (Infinite Scroll) ── */
function loadMore() {
  if (state.isLoading || !state.hasMore) return;
  state.isLoading = true;

  setTimeout(() => {
    renderBatch(state.renderedCount, state.pageSize);
    state.isLoading = false;
    if (!state.hasMore) loader.classList.remove('active');
  }, 400);
}

/* ── Intersection Observer ── */
const observer = new IntersectionObserver((entries) => {
  if (entries[0].isIntersecting && state.hasMore) {
    loadMore();
  }
}, { rootMargin: '200px' });

observer.observe(loader);

/* ── Tabs ── */
tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    state.currentCategory = tab.dataset.category;
    renderGallery(true);
  });
});

/* ── Search ── */
let searchTimer;
searchInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.searchQuery = searchInput.value;
    renderGallery(true);
  }, 300);
});

/* ── Lightbox ── */
function openLightbox(index) {
  state.lightboxPhotos = state.filteredPhotos;
  state.currentLightboxIndex = index;
  updateLightbox();
  lightbox.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  lightbox.classList.remove('open');
  document.body.style.overflow = '';
}

function updateLightbox() {
  const photo = state.lightboxPhotos[state.currentLightboxIndex];
  if (!photo) return;

  lightboxImage.src = photo.url;
  lightboxImage.alt = photo.title;
  lightboxTitle.textContent = photo.title;
  lightboxTag.textContent = photo.categoryLabel;
  lightboxCounter.textContent = `${state.currentLightboxIndex + 1} / ${state.lightboxPhotos.length}`;

  renderThumbnails();
  scrollThumbIntoView();
}

function prevPhoto() {
  if (state.currentLightboxIndex > 0) {
    state.currentLightboxIndex--;
    updateLightbox();
  }
}

function nextPhoto() {
  if (state.currentLightboxIndex < state.lightboxPhotos.length - 1) {
    state.currentLightboxIndex++;
    updateLightbox();
  }
}

function renderThumbnails() {
  lightboxThumbs.innerHTML = '';
  state.lightboxPhotos.forEach((photo, i) => {
    const thumb = document.createElement('div');
    thumb.className = 'lightbox-thumb' + (i === state.currentLightboxIndex ? ' active' : '');
    thumb.innerHTML = `<img src="${photo.url}" alt="">`;
    thumb.addEventListener('click', () => {
      state.currentLightboxIndex = i;
      updateLightbox();
    });
    lightboxThumbs.appendChild(thumb);
  });
}

function scrollThumbIntoView() {
  const activeThumb = lightboxThumbs.querySelector('.lightbox-thumb.active');
  if (activeThumb) {
    activeThumb.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
  }
}

lightboxClose.addEventListener('click', closeLightbox);
lightboxPrev.addEventListener('click', prevPhoto);
lightboxNext.addEventListener('click', nextPhoto);

lightbox.addEventListener('click', (e) => {
  if (e.target === lightbox) closeLightbox();
});

document.addEventListener('keydown', (e) => {
  if (!lightbox.classList.contains('open')) return;
  if (e.key === 'Escape') closeLightbox();
  if (e.key === 'ArrowLeft') prevPhoto();
  if (e.key === 'ArrowRight') nextPhoto();
});

/* ── Init ── */
renderGallery(true);
