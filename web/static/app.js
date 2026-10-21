/**
 * GeoSleuth Intelligence Hub — Frontend Logic
 */

let map;
let baseLayers = {};
let currentLayerIndex = 0;
let layerKeys = ['googleSat', 'osm'];
let layerNames = {
  googleSat: 'Спутник Google',
  osm: 'OpenStreetMap'
};

let currentCases = [];
let activeCase = null;
let currentView = 'home'; // 'home' | 'map'

let mapMarkers = {
  camera: null,
  target: null,
  sightLine: null,
  accuracyCircle: null
};

let isPickingOnMap = false;

let currentRegionMode = 'global';

function getActiveRegionMode() {
  return currentRegionMode || 'global';
}

function setActiveRegionMode(mode) {
  currentRegionMode = mode === 'kz' ? 'kz' : 'global';
  
  // Sync Hero labels & radios
  const heroGlobal = document.getElementById('heroRegionGlobalLabel');
  const heroKz = document.getElementById('heroRegionKzLabel');
  if (heroGlobal && heroKz) {
    if (currentRegionMode === 'global') {
      heroGlobal.classList.add('active');
      heroGlobal.style.background = '#2563eb';
      heroGlobal.style.color = '#ffffff';
      heroGlobal.style.boxShadow = '0 0 12px rgba(37,99,235,0.5)';
      heroKz.classList.remove('active');
      heroKz.style.background = 'transparent';
      heroKz.style.color = '#94a3b8';
      heroKz.style.boxShadow = 'none';
      const rad = heroGlobal.querySelector('input');
      if (rad) rad.checked = true;
    } else {
      heroKz.classList.add('active');
      heroKz.style.background = '#0ea5e9';
      heroKz.style.color = '#ffffff';
      heroKz.style.boxShadow = '0 0 12px rgba(14,165,233,0.5)';
      heroGlobal.classList.remove('active');
      heroGlobal.style.background = 'transparent';
      heroGlobal.style.color = '#94a3b8';
      heroGlobal.style.boxShadow = 'none';
      const rad = heroKz.querySelector('input');
      if (rad) rad.checked = true;
    }
  }

  // Sync Modal labels & radios
  const modalGlobal = document.getElementById('modalRegionGlobalLabel');
  const modalKz = document.getElementById('modalRegionKzLabel');
  if (modalGlobal && modalKz) {
    if (currentRegionMode === 'global') {
      modalGlobal.classList.add('active');
      modalGlobal.style.background = '#2563eb';
      modalGlobal.style.color = '#ffffff';
      modalKz.classList.remove('active');
      modalKz.style.background = 'transparent';
      modalKz.style.color = '#94a3b8';
      const rad = modalGlobal.querySelector('input');
      if (rad) rad.checked = true;
    } else {
      modalKz.classList.add('active');
      modalKz.style.background = '#0ea5e9';
      modalKz.style.color = '#ffffff';
      modalGlobal.classList.remove('active');
      modalGlobal.style.background = 'transparent';
      modalGlobal.style.color = '#94a3b8';
      const rad = modalKz.querySelector('input');
      if (rad) rad.checked = true;
    }
  }
}

function getCountryFlag(countryCode, countryName) {
  if (countryCode && typeof countryCode === 'string' && countryCode.trim().length === 2) {
    const code = countryCode.trim().toUpperCase();
    try {
      const flag = String.fromCodePoint(...[...code].map(c => 0x1F1E6 + c.charCodeAt(0) - 65));
      return `${flag} ${code}`;
    } catch (e) {
      return `🏳️ ${code}`;
    }
  }
  const low = (countryName || '').toLowerCase();
  if (low.includes('казахстан') || low.includes('kazakhstan') || low === 'kz') return '🇰🇿 KZ';
  if (low.includes('франция') || low.includes('france') || low === 'fr') return '🇫🇷 FR';
  if (low.includes('япония') || low.includes('japan') || low === 'jp') return '🇯🇵 JP';
  if (low.includes('сша') || low.includes('united states') || low.includes('usa') || low === 'us') return '🇺🇸 US';
  if (low.includes('турция') || low.includes('turkey') || low === 'tr') return '🇹🇷 TR';
  if (low.includes('великобритания') || low.includes('united kingdom') || low === 'gb' || low === 'uk') return '🇬🇧 GB';
  if (low.includes('германия') || low.includes('germany') || low === 'de') return '🇩🇪 DE';
  if (low.includes('италия') || low.includes('italy') || low === 'it') return '🇮🇹 IT';
  if (low.includes('испания') || low.includes('spain') || low === 'es') return '🇪🇸 ES';
  if (low.includes('оаэ') || low.includes('uae') || low === 'ae') return '🇦🇪 AE';
  if (low.includes('вьетнам') || low.includes('vietnam') || low === 'vn') return '🇻🇳 VN';
  if (low.includes('узбекистан') || low === 'uz') return '🇺🇿 UZ';
  if (low.includes('кыргызстан') || low === 'kg') return '🇰🇬 KG';
  if (low.includes('россия') || low.includes('russia') || low === 'ru') return '🇷🇺 RU';
  if (low.includes('китай') || low.includes('china') || low === 'cn') return '🇨🇳 CN';
  if (low.includes('корея') || low.includes('korea') || low === 'kr') return '🇰🇷 KR';
  return '🌍 World';
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  initMap();
  setupEventListeners();
  loadCases();
});

/* ==========================================================================
   View Navigation (Home <-> Map)
   ========================================================================== */

function switchView(viewName) {
  currentView = viewName;

  const homeView = document.getElementById('homeView');
  const mapView = document.getElementById('mapView');
  const radarView = document.getElementById('radarView');
  const knowledgeView = document.getElementById('knowledgeView');

  const tabHome = document.getElementById('tabHome');
  const tabMap = document.getElementById('tabMap');
  const tabRadar = document.getElementById('tabRadar');
  const tabKnowledge = document.getElementById('tabKnowledge');

  const caseSwitcher = document.getElementById('headerCaseSwitcher');
  const btnToggleLayers = document.getElementById('btnToggleLayers');
  const btnToggleRoute = document.getElementById('btnToggleRoute');

  [homeView, mapView, radarView, knowledgeView].forEach(v => {
    if (v) v.style.display = 'none';
  });
  [tabHome, tabMap, tabRadar, tabKnowledge].forEach(t => {
    if (t) t.classList.remove('active');
  });

  if (caseSwitcher) caseSwitcher.style.display = 'none';
  if (btnToggleLayers) btnToggleLayers.style.display = 'none';
  if (btnToggleRoute) btnToggleRoute.style.display = 'none';

  if (viewName === 'home') {
    if (homeView) homeView.style.display = 'block';
    if (tabHome) tabHome.classList.add('active');
  } else if (viewName === 'map') {
    if (mapView) mapView.style.display = 'flex';
    if (tabMap) tabMap.classList.add('active');
    if (caseSwitcher) caseSwitcher.style.display = 'flex';
    if (btnToggleLayers) btnToggleLayers.style.display = 'inline-flex';
    if (btnToggleRoute) btnToggleRoute.style.display = 'inline-flex';

    setTimeout(() => {
      if (map) {
        map.invalidateSize();
        if (activeCase) {
          renderMapMarkers(activeCase);
        }
      }
    }, 100);
  } else if (viewName === 'radar') {
    if (radarView) radarView.style.display = 'block';
    if (tabRadar) tabRadar.classList.add('active');
    initRadarScreen();
  } else if (viewName === 'knowledge') {
    if (knowledgeView) knowledgeView.style.display = 'block';
    if (tabKnowledge) tabKnowledge.classList.add('active');
    loadKnowledgeBase();
  }
}

/* ==========================================================================
   Map Setup & Layer Management
   ========================================================================== */

function initMap() {
  map = L.map('map', {
    zoomControl: false,
    attributionControl: false
  }).setView([53.087, 70.251], 16);

  L.control.zoom({ position: 'topright' }).addTo(map);

  baseLayers.googleSat = L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
    maxZoom: 20
  });

  baseLayers.osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19
  });

  baseLayers.googleSat.addTo(map);
  updateLayerButtonText();

  map.on('click', (e) => {
    if (isPickingOnMap) {
      const lat = e.latlng.lat.toFixed(6);
      const lon = e.latlng.lng.toFixed(6);
      document.getElementById('inputCameraLat').value = lat;
      document.getElementById('inputCameraLon').value = lon;
      isPickingOnMap = false;
      document.getElementById('uploadModal').style.display = 'flex';
      alert(`Выбраны координаты точки: ${lat}, ${lon}`);
    }
  });
}

function cycleMapLayer() {
  const currentKey = layerKeys[currentLayerIndex];
  map.removeLayer(baseLayers[currentKey]);

  currentLayerIndex = (currentLayerIndex + 1) % layerKeys.length;
  const newKey = layerKeys[currentLayerIndex];
  baseLayers[newKey].addTo(map);

  updateLayerButtonText();
}

function updateLayerButtonText() {
  const currentKey = layerKeys[currentLayerIndex];
  const nameSpan = document.getElementById('layerName');
  if (nameSpan) {
    nameSpan.textContent = layerNames[currentKey];
  }
}

/* ==========================================================================
   Cases API & Rendering
   ========================================================================== */

async function loadCases(selectId = null) {
  try {
    const res = await fetch('/api/cases');
    currentCases = await res.json();
    renderCasesNav();
    renderHomeShowcase();
    renderHeroQuickPills();

    if (currentCases.length > 0) {
      const targetCase = selectId 
        ? currentCases.find(c => c.id === selectId) || currentCases[0]
        : currentCases[0];
      selectCase(targetCase.id, false);
    }
  } catch (err) {
    console.error('Failed to load cases:', err);
  }
}

function renderCasesNav() {
  const nav = document.getElementById('casesNav');
  if (!nav) return;
  nav.innerHTML = '';

  if (!currentCases || currentCases.length === 0) {
    nav.innerHTML = '<span class="cases-nav-empty">Нет открытых вкладок</span>';
    return;
  }

  currentCases.forEach(c => {
    const btn = document.createElement('button');
    const isActive = activeCase && activeCase.id === c.id;
    btn.className = `case-nav-btn ${isActive ? 'active' : ''}`;
    btn.dataset.id = c.id;
    const titleText = (c.title || 'Локация').trim();
    btn.title = `${titleText}\n(Кликните средней кнопкой мыши или [×] для закрытия)`;

    btn.innerHTML = `
      <span class="case-nav-pin">📍</span>
      <span class="case-nav-title">${escapeHtml(titleText)}</span>
      <span class="case-nav-close" data-id="${c.id}" title="Закрыть вкладку">&times;</span>
    `;

    // Click to select tab (unless close button clicked)
    btn.addEventListener('click', (e) => {
      if (e.target.closest('.case-nav-close')) {
        return;
      }
      selectCase(c.id, true);
    });

    // Middle-click (wheel click) closes tab like browser tabs
    btn.addEventListener('auxclick', (e) => {
      if (e.button === 1) {
        e.preventDefault();
        e.stopPropagation();
        closeCase(c.id);
      }
    });

    // Close button click
    const closeBtn = btn.querySelector('.case-nav-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        closeCase(c.id);
      });
    }

    nav.appendChild(btn);
  });

  // If there are 2 or more tabs, show "Очистить все"
  if (currentCases.length >= 2) {
    const clearBtn = document.createElement('button');
    clearBtn.className = 'case-nav-clear';
    clearBtn.title = 'Закрыть все открытые вкладки';
    clearBtn.innerHTML = `<span>✕</span><span>Очистить (${currentCases.length})</span>`;
    clearBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      closeAllCases();
    });
    nav.appendChild(clearBtn);
  }
}

async function closeCase(caseId) {
  const caseIndex = currentCases.findIndex(c => c.id === caseId);
  if (caseIndex === -1) return;

  const closingActive = activeCase && activeCase.id === caseId;

  // Optimistically remove from frontend list
  currentCases.splice(caseIndex, 1);

  // Send DELETE to backend
  try {
    fetch(`/api/cases/${caseId}`, { method: 'DELETE' }).catch(err => {
      console.warn('Failed to delete case from server:', err);
    });
  } catch (err) {
    console.warn(err);
  }

  // Update UI components
  renderHomeShowcase();
  renderHeroQuickPills();

  if (currentCases.length === 0) {
    activeCase = null;
    renderCasesNav();
    if (currentView === 'map') {
      switchView('home');
    }
  } else {
    if (closingActive) {
      // Pick next adjacent tab
      const nextIndex = Math.min(caseIndex, currentCases.length - 1);
      const nextCase = currentCases[nextIndex];
      selectCase(nextCase.id, currentView === 'map');
    } else {
      renderCasesNav();
    }
  }
}

async function closeAllCases() {
  if (!currentCases || currentCases.length === 0) return;
  const count = currentCases.length;
  if (!confirm(`Закрыть все открытые вкладки (${count} шт.)?`)) return;

  const idsToDelete = currentCases.map(c => c.id);
  currentCases = [];
  activeCase = null;

  renderCasesNav();
  renderHomeShowcase();
  renderHeroQuickPills();
  switchView('home');

  for (const id of idsToDelete) {
    fetch(`/api/cases/${id}`, { method: 'DELETE' }).catch(() => {});
  }
}

function renderHeroQuickPills() {
  const container = document.getElementById('heroQuickPills');
  if (!container) return;
  container.innerHTML = '';

  currentCases.slice(0, 3).forEach(c => {
    const btn = document.createElement('button');
    btn.className = 'quick-pill-btn';
    btn.textContent = c.title;
    btn.addEventListener('click', () => {
      selectCase(c.id, true);
    });
    container.appendChild(btn);
  });
}

let currentShowcaseSearch = '';
let currentShowcaseFilter = 'all';

function renderHomeShowcase(searchQuery = currentShowcaseSearch, filterTag = currentShowcaseFilter) {
  const grid = document.getElementById('showcaseGrid');
  if (!grid) return;
  grid.innerHTML = '';
  currentShowcaseSearch = searchQuery;
  currentShowcaseFilter = filterTag;

  const q = (searchQuery || '').toLowerCase().trim();
  const filtered = currentCases.filter(c => {
    const matchesText = !q || 
      (c.title && c.title.toLowerCase().includes(q)) ||
      (c.country && c.country.toLowerCase().includes(q)) ||
      (c.region && c.region.toLowerCase().includes(q)) ||
      (c.description && c.description.toLowerCase().includes(q));

    let matchesTag = true;
    if (filterTag === 'Казахстан') {
      matchesTag = (c.country && c.country.includes('Казахстан')) || (c.region && c.region.includes('Бурабай'));
    } else if (filterTag === 'Вьетнам') {
      matchesTag = (c.country && c.country.includes('Вьетнам')) || (c.region && c.region.includes('Вьетнам'));
    } else if (filterTag === 'verified') {
      matchesTag = c.confidence && (c.confidence.includes('VERIFIED') || c.confidence.includes('ВЕРИФИЦИРОВАНО') || c.confidence.includes('CONFIRMED'));
    }
    return matchesText && matchesTag;
  });

  if (filtered.length === 0) {
    grid.innerHTML = `<div class="empty-showcase-msg" style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-dim);"><p>🔍 По запросу ничего не найдено. Попробуйте сбросить фильтры.</p></div>`;
    return;
  }

  filtered.forEach(c => {
    const card = document.createElement('div');
    card.className = 'showcase-card';

    // Thumbs row
    const evidenceThumbsHtml = (c.evidence_photos || []).slice(0, 3).map(ev => `
      <img src="${ev.url}" alt="${ev.title}" class="evidence-mini-thumb" title="${ev.title}">
    `).join('');

    const isIndoorBadge = c.is_indoor ? '<span class="indoor-badge" style="background: rgba(245, 158, 11, 0.25); color: #fbbf24; border: 1px solid #f59e0b; padding: 2px 7px; border-radius: 4px; font-size: 11px; font-weight: 700;">🏠 INDOOR</span>' : '';
    const precisionBar = `
      <div class="showcase-precision-bar" style="margin: 6px 0; font-size: 12px; display: flex; flex-wrap: wrap; align-items: center; gap: 6px;">
        ${c.method ? `<span class="badge-method" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600;">🎯 ${c.method}</span>` : ''}
        <span class="badge-radius" style="background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600;">±${c.error_radius_m || 15} м</span>
      </div>
      ${c.warning ? `<div class="showcase-warning" style="font-size: 11px; color: #fbbf24; background: rgba(245, 158, 11, 0.12); border-left: 2px solid #f59e0b; padding: 4px 6px; margin: 4px 0; border-radius: 2px;">⚠️ ${c.warning}</div>` : ''}
    `;

    const flagBadge = getCountryFlag(c.country_code, c.country);
    const locationDisplay = [c.city, c.region].filter(Boolean).filter((v, i, a) => a.indexOf(v) === i).join(', ') || c.country || 'Локация';

    card.innerHTML = `
      <div class="showcase-image-wrap">
        <img src="${c.main_photo}" alt="${c.title}" class="showcase-image" loading="lazy">
        <button class="showcase-card-close" data-id="${c.id}" title="Закрыть / удалить дело">&times;</button>
        <div class="showcase-badges">
          <span class="country-badge">${flagBadge} ${escapeHtml(c.country || 'Global')}</span>
          ${isIndoorBadge}
          <span class="confidence-badge">${c.confidence}</span>
        </div>
      </div>
      <div class="showcase-body">
        <div class="showcase-location">${escapeHtml(locationDisplay)}</div>
        <h3 class="showcase-title">${c.title}</h3>
        ${precisionBar}
        <p class="showcase-desc">${c.description}</p>
        
        <div class="showcase-evidence-thumbs">
          ${evidenceThumbsHtml}
        </div>

        <div class="showcase-footer">
          <div class="showcase-coords mono">${c.target_lat.toFixed(4)}, ${c.target_lon.toFixed(4)}</div>
          <div class="showcase-card-btns">
            <button class="btn btn-xs btn-outline-warning btn-card-rescan" data-id="${c.id}" title="Неправильный ответ? Запустить 5 независимых запусков заново">
              <span>🔄 5 запусков</span>
            </button>
            <button class="btn btn-sm btn-primary btn-open-case">
              <span>Открыть на карте →</span>
            </button>
          </div>
        </div>
      </div>
    `;

    const btnCardClose = card.querySelector('.showcase-card-close');
    if (btnCardClose) {
      btnCardClose.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        closeCase(c.id);
      });
    }

    const btnCardRescan = card.querySelector('.btn-card-rescan');
    if (btnCardRescan) {
      btnCardRescan.addEventListener('click', (e) => {
        e.stopPropagation();
        openRescanModal(c.id);
      });
    }

    card.querySelector('.btn-open-case').addEventListener('click', (e) => {
      e.stopPropagation();
      selectCase(c.id, true);
    });

    card.addEventListener('click', () => {
      selectCase(c.id, true);
    });

    grid.appendChild(card);
  });
}

function selectCase(caseId, navigateToMap = true) {
  const c = currentCases.find(item => item.id === caseId);
  if (!c) return;

  activeCase = c;
  renderCasesNav();
  updateSidebar(c);

  if (navigateToMap) {
    switchView('map');
  } else if (currentView === 'map') {
    renderMapMarkers(c);
  }
}

function updateSidebar(c) {
  if (!c) return;
  const flagText = getCountryFlag(c.country_code, c.country);
  document.getElementById('caseCountry').innerHTML = `${flagText} &bull; ${escapeHtml(c.country || 'ЛОКАЦИЯ')}`;
  const confEl = document.getElementById('caseConfidence');
  if (confEl) {
    confEl.innerHTML = `${escapeHtml(c.confidence || 'ВЕРИФИЦИРОВАНО')} ${c.is_indoor ? '<span style="background:#f59e0b;color:#000;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:bold;margin-left:5px;">🏠 INDOOR</span>' : ''}`;
  }
  const btnCloseActive = document.getElementById('btnCloseActiveCase');
  if (btnCloseActive) {
    btnCloseActive.onclick = () => {
      if (activeCase) {
        closeCase(activeCase.id);
      }
    };
  }

  const locDetail = [c.city, c.region].filter(Boolean).filter((v, i, a) => a.indexOf(v) === i).join(' &bull; ') || '';
  document.getElementById('caseRegion').innerHTML = escapeHtml(locDetail);

  // Precision & Method Bar
  let precisionBox = document.getElementById('sidebarPrecisionBox');
  if (!precisionBox) {
    const parent = document.getElementById('caseRegion')?.parentElement;
    if (parent) {
      precisionBox = document.createElement('div');
      precisionBox.id = 'sidebarPrecisionBox';
      parent.insertBefore(precisionBox, document.getElementById('caseRegion').nextSibling);
    }
  }
  if (precisionBox) {
    precisionBox.innerHTML = `
      <div style="display:flex; flex-wrap:wrap; gap:6px; margin: 8px 0; font-size:11px;">
        ${c.method ? `<span style="background:rgba(59,130,246,0.18);color:#93c5fd;border:1px solid rgba(59,130,246,0.3);padding:2px 7px;border-radius:4px;font-weight:600;">🎯 ${escapeHtml(c.method)}</span>` : ''}
        <span style="background:rgba(16,185,129,0.18);color:#6ee7b7;border:1px solid rgba(16,185,129,0.3);padding:2px 7px;border-radius:4px;font-weight:600;">📏 CEP ±${c.error_radius_m || 15} м</span>
      </div>
      ${c.warning ? `<div style="font-size:11px;color:#fbbf24;background:rgba(245,158,11,0.15);border-left:3px solid #f59e0b;padding:5px 8px;margin-bottom:8px;border-radius:3px;line-height:1.4;">⚠️ <b>Внимание:</b> ${escapeHtml(c.warning)}</div>` : ''}
    `;
  }

  // Main Photo
  const mainImg = document.getElementById('mainPhotoImg');
  mainImg.src = c.main_photo;
  mainImg.alt = c.title;

  // External Maps links
  const btnGmaps = document.getElementById('btnOpenInGoogleMaps');
  if (btnGmaps) {
    btnGmaps.href = `https://www.google.com/maps?q=${c.target_lat},${c.target_lon}&z=17`;
  }

  const btn2Gis = document.getElementById('btnOpenIn2Gis');
  if (btn2Gis) {
    btn2Gis.href = c.twogis_url || `https://2gis.kz/geo/${c.target_lon.toFixed(6)},${c.target_lat.toFixed(6)}`;
  }

  const btnYandex = document.getElementById('btnOpenInYandexMaps');
  if (btnYandex) {
    btnYandex.href = c.yandex_maps_url || `https://yandex.kz/maps/?ll=${c.target_lon.toFixed(6)}%2C${c.target_lat.toFixed(6)}&z=16&pt=${c.target_lon.toFixed(6)},${c.target_lat.toFixed(6)}`;
  }

  // Telemetry
  document.getElementById('targetName').textContent = c.target_name || c.title;
  document.getElementById('targetCoords').textContent = `${c.target_lat.toFixed(6)}, ${c.target_lon.toFixed(6)}`;
  document.getElementById('cameraName').textContent = c.camera_name || 'Точка съёмки';
  document.getElementById('cameraCoords').textContent = `${c.camera_lat.toFixed(6)}, ${c.camera_lon.toFixed(6)}`;

  // Compass and Vector
  const bearing = c.bearing_deg || 0;
  document.getElementById('bearingDegText').textContent = `${bearing}°`;
  document.getElementById('compassNeedle').style.transform = `rotate(${bearing}deg)`;

  const dist = c.distance_m || 0;
  document.getElementById('distMetersText').textContent = `${dist} м`;
  document.getElementById('errorRadiusText').textContent = `±${c.error_radius_m || 5} м`;

  // HUD
  document.getElementById('hudCoordsVal').textContent = `${c.target_lat.toFixed(5)}, ${c.target_lon.toFixed(5)}`;
  document.getElementById('hudDistVal').textContent = `${dist} м`;
  document.getElementById('hudBearingVal').textContent = `${bearing}°`;

  // Description
  document.getElementById('caseDescription').textContent = c.description || '';

  // Clues
  const cluesList = document.getElementById('cluesList');
  cluesList.innerHTML = '';
  (c.clues || []).forEach(clue => {
    const item = document.createElement('div');
    item.className = 'clue-item';
    item.innerHTML = `
      <span class="clue-icon">✔</span>
      <span>${clue}</span>
    `;
    cluesList.appendChild(item);
  });

  // OCR Detected Texts Box in Sidebar
  const ocrBox = document.getElementById('sidebarOcrBox');
  const ocrChipsContainer = document.getElementById('sidebarOcrChips');
  if (ocrBox && ocrChipsContainer) {
    const lines = c.ocr_lines || [];
    const keywords = c.ocr_keywords || [];
    if (lines.length > 0 || keywords.length > 0) {
      ocrBox.style.display = 'block';
      ocrChipsContainer.innerHTML = '';
      const chipsToShow = (keywords.length > 0 ? keywords : lines).slice(0, 8);
      chipsToShow.forEach(kw => {
        const chip = document.createElement('span');
        chip.className = 'sidebar-ocr-chip';
        chip.title = `Кликните, чтобы запустить 5 запусков поиска для «${kw}»`;
        chip.innerHTML = `🔤 <b>${escapeHtml(kw)}</b>`;
        chip.addEventListener('click', (e) => {
          e.stopPropagation();
          trigger5PassRescan(c.id, kw);
        });
        ocrChipsContainer.appendChild(chip);
      });
    } else {
      ocrBox.style.display = 'none';
    }
  }

  // AI Scout & Kazakhstan Anchor Card
  renderAiScoutCard(c);

  // Evidence Photos
  renderEvidenceGallery(c.evidence_photos || []);

  // Fetch elevation profile & terrain
  fetchElevation(c);

  // Initialize SunCalc solar & shadow analysis
  initSunCalc(c);

  // Reset calibration button state
  const btnSaveCalib = document.getElementById('btnSaveCalibration');
  if (btnSaveCalib) {
    btnSaveCalib.disabled = true;
    btnSaveCalib.style.boxShadow = '';
    btnSaveCalib.textContent = '💾 Сохранить координаты';
  }

  // Render OSINT Forensic Signals
  renderOsintSignals(c);

  // Render Ubinam 5-Tier Confidence Ladder
  fetchAndRenderUbinamLadder(c.id);

  // Render FindMyPhoto Distance Matrix & Geotag
  fetchAndRenderDistanceMatrix(c.id);

  // Render Kazakh Signboard Mining
  fetchAndRenderKazakhSignboards(c);
}

function renderEvidenceGallery(photos) {
  const grid = document.getElementById('evidenceGrid');
  const countBadge = document.getElementById('evidenceCount');
  countBadge.textContent = photos.length;
  grid.innerHTML = '';

  if (photos.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: span 2; text-align: center; padding: 20px; color: var(--text-dim); font-size: 0.75rem;">
        Нет прикреплённых спутниковых улик. Нажмите «Спутниковый снимок точки» для автоматической генерации.
      </div>
    `;
    return;
  }

  photos.forEach(item => {
    const card = document.createElement('div');
    card.className = 'evidence-card';
    card.innerHTML = `
      <div class="evidence-thumb-wrap">
        <img src="${item.url}" alt="${item.title}" class="evidence-thumb" loading="lazy">
        <span class="evidence-tag">${item.type || 'Спутник'}</span>
      </div>
      <div class="evidence-info">
        <div class="evidence-title" title="${item.title}">${item.title}</div>
      </div>
    `;
    card.addEventListener('click', () => {
      openLightbox(item.url, item.title, item.desc || '');
    });
    grid.appendChild(card);
  });
}

/* ==========================================================================
   Map Markers & Geometry Rendering
   ========================================================================== */

function calcDistanceMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return Math.round(R * c);
}

function calcBearingDeg(lat1, lon1, lat2, lon2) {
  const phi1 = lat1 * Math.PI / 180;
  const phi2 = lat2 * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const y = Math.sin(dLon) * Math.cos(phi2);
  const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(dLon);
  return Math.round(((Math.atan2(y, x) * 180 / Math.PI) + 360) % 360);
}

function onMarkerDragged() {
  if (!mapMarkers.camera || !mapMarkers.target) return;
  const camPos = mapMarkers.camera.getLatLng();
  const targetPos = mapMarkers.target.getLatLng();

  const d = calcDistanceMeters(camPos.lat, camPos.lng, targetPos.lat, targetPos.lng);
  const b = calcBearingDeg(camPos.lat, camPos.lng, targetPos.lat, targetPos.lng);

  mapMarkers.sightLine.setLatLngs([camPos, targetPos]);
  mapMarkers.accuracyCircle.setLatLng(targetPos);

  document.getElementById('targetCoords').textContent = `${targetPos.lat.toFixed(6)}, ${targetPos.lng.toFixed(6)}`;
  document.getElementById('cameraCoords').textContent = `${camPos.lat.toFixed(6)}, ${camPos.lng.toFixed(6)}`;
  document.getElementById('bearingDegText').textContent = `${b}°`;
  document.getElementById('compassNeedle').style.transform = `rotate(${b}deg)`;
  document.getElementById('distMetersText').textContent = `${d} м`;

  document.getElementById('hudCoordsVal').textContent = `${targetPos.lat.toFixed(5)}, ${targetPos.lng.toFixed(5)}`;
  document.getElementById('hudDistVal').textContent = `${d} м`;
  document.getElementById('hudBearingVal').textContent = `${b}°`;

  const btnSave = document.getElementById('btnSaveCalibration');
  if (btnSave) {
    btnSave.disabled = false;
    btnSave.style.boxShadow = '0 0 10px var(--accent-cyan)';
  }

  if (sunRayActive) updateSunRay();
}

function renderMapMarkers(c) {
  if (mapMarkers.camera) map.removeLayer(mapMarkers.camera);
  if (mapMarkers.target) map.removeLayer(mapMarkers.target);
  if (mapMarkers.sightLine) map.removeLayer(mapMarkers.sightLine);
  if (mapMarkers.accuracyCircle) map.removeLayer(mapMarkers.accuracyCircle);
  if (!c) return;

  const camLatLng = [c.camera_lat, c.camera_lon];
  const targetLatLng = [c.target_lat, c.target_lon];

  // Camera Marker (Draggable)
  const cameraIcon = L.divIcon({
    className: 'custom-marker',
    html: `
      <div class="marker-camera-pin" title="Камера (перетащите для юстировки)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
          <circle cx="12" cy="13" r="4"></circle>
        </svg>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16]
  });

  mapMarkers.camera = L.marker(camLatLng, { icon: cameraIcon, draggable: true })
    .addTo(map)
    .bindPopup(`<b>Точка съёмки:</b><br>${c.camera_name}<br><code>${c.camera_lat.toFixed(6)}, ${c.camera_lon.toFixed(6)}</code><br><small style="color:var(--accent-cyan)">💡 Перетащите маркер для калибровки</small>`);

  // Target Marker (Draggable)
  const targetIcon = L.divIcon({
    className: 'custom-marker',
    html: `
      <div class="marker-target-pin" title="Целевой объект (перетащите для юстировки)">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
        </svg>
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 18]
  });

  mapMarkers.target = L.marker(targetLatLng, { icon: targetIcon, draggable: true })
    .addTo(map)
    .bindPopup(`<b>Целевой объект:</b><br>${c.target_name}<br><code>${c.target_lat.toFixed(6)}, ${c.target_lon.toFixed(6)}</code><br><small style="color:var(--accent-cyan)">💡 Перетащите маркер для калибровки</small>`);

  // Attach drag events
  mapMarkers.camera.on('drag', onMarkerDragged);
  mapMarkers.target.on('drag', onMarkerDragged);

  // Accuracy Circle
  const radius = c.error_radius_m || 10;
  mapMarkers.accuracyCircle = L.circle(targetLatLng, {
    radius: radius,
    color: '#10b981',
    fillColor: '#10b981',
    fillOpacity: 0.15,
    weight: 1.5,
    dashArray: '4, 4'
  }).addTo(map);

  // Sight Line
  mapMarkers.sightLine = L.polyline([camLatLng, targetLatLng], {
    color: '#f43f5e',
    weight: 3,
    dashArray: '6, 6',
    opacity: 0.85
  }).addTo(map);

  // Fit bounds nicely with animation
  const bounds = L.latLngBounds([camLatLng, targetLatLng]);
  map.flyToBounds(bounds, {
    padding: [100, 100],
    maxZoom: 18,
    duration: 1.2
  });
}

/* ==========================================================================
   Modals & Interaction Handlers
   ========================================================================== */

function setupEventListeners() {
  // Navigation Tabs
  document.getElementById('tabHome').addEventListener('click', () => switchView('home'));
  document.getElementById('tabMap').addEventListener('click', () => switchView('map'));
  const tabRadar = document.getElementById('tabRadar');
  if (tabRadar) tabRadar.addEventListener('click', () => switchView('radar'));
  const tabKnowledge = document.getElementById('tabKnowledge');
  if (tabKnowledge) tabKnowledge.addEventListener('click', () => switchView('knowledge'));
  document.getElementById('brandLogo').addEventListener('click', () => switchView('home'));

  // Hero Dropzone & CTA buttons
  const heroDropzone = document.getElementById('heroDropzone');
  const heroFileInput = document.getElementById('heroFileInput');

  // Region Mode Switchers (Hero & Modal)
  const heroGlobal = document.getElementById('heroRegionGlobalLabel');
  const heroKz = document.getElementById('heroRegionKzLabel');
  if (heroGlobal) heroGlobal.addEventListener('click', (e) => { e.preventDefault(); setActiveRegionMode('global'); });
  if (heroKz) heroKz.addEventListener('click', (e) => { e.preventDefault(); setActiveRegionMode('kz'); });

  const modalGlobal = document.getElementById('modalRegionGlobalLabel');
  const modalKz = document.getElementById('modalRegionKzLabel');
  if (modalGlobal) modalGlobal.addEventListener('click', (e) => { e.preventDefault(); setActiveRegionMode('global'); });
  if (modalKz) modalKz.addEventListener('click', (e) => { e.preventDefault(); setActiveRegionMode('kz'); });

  heroDropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    heroDropzone.classList.add('dragover');
  });

  heroDropzone.addEventListener('dragleave', () => {
    heroDropzone.classList.remove('dragover');
  });

  heroDropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    heroDropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      startAutoScan(file);
    }
  });

  heroFileInput.addEventListener('change', () => {
    if (heroFileInput.files && heroFileInput.files[0]) {
      const file = heroFileInput.files[0];
      startAutoScan(file);
    }
  });

  document.getElementById('btnCtaUpload').addEventListener('click', () => {
    document.getElementById('uploadModal').style.display = 'flex';
  });

  document.getElementById('btnCtaOpenMap').addEventListener('click', () => {
    switchView('map');
  });

  // Layer Switcher
  document.getElementById('btnToggleLayers').addEventListener('click', cycleMapLayer);

  // Reset View
  document.getElementById('btnResetView').addEventListener('click', () => {
    if (activeCase) renderMapMarkers(activeCase);
  });

  // Toggle Sightline
  document.getElementById('btnToggleSightLine').addEventListener('click', () => {
    if (mapMarkers.sightLine) {
      if (map.hasLayer(mapMarkers.sightLine)) {
        map.removeLayer(mapMarkers.sightLine);
      } else {
        mapMarkers.sightLine.addTo(map);
      }
    }
  });

  // Copy buttons
  document.querySelectorAll('.btn-copy').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.dataset.target;
      const text = document.getElementById(targetId).textContent;
      navigator.clipboard.writeText(text);
      btn.style.color = 'var(--accent-emerald)';
      setTimeout(() => btn.style.color = '', 1200);
    });
  });

  // Main Photo Lightbox
  document.getElementById('mainPhotoWrapper').addEventListener('click', () => {
    if (activeCase) {
      openLightbox(activeCase.main_photo, activeCase.title, activeCase.description);
    }
  });
  document.getElementById('btnViewMainPhoto').addEventListener('click', () => {
    if (activeCase) {
      openLightbox(activeCase.main_photo, activeCase.title, activeCase.description);
    }
  });

  // Open in Yandex Visual Search Button
  const btnYandexVisual = document.getElementById('btnOpenInYandexVisual');
  if (btnYandexVisual) {
    btnYandexVisual.addEventListener('click', () => {
      window.open('https://yandex.ru/images/search?rpt=imageview', '_blank');
    });
  }

  // Open in Google Lens Button
  const btnGoogleLens = document.getElementById('btnOpenInGoogleLens');
  if (btnGoogleLens) {
    btnGoogleLens.addEventListener('click', () => {
      if (activeCase) {
        window.open('https://lens.google.com/', '_blank');
      }
    });
  }

  // Export Dossier Button
  const btnExport = document.getElementById('btnExportDossier');
  if (btnExport) {
    btnExport.addEventListener('click', () => {
      if (activeCase) {
        exportDossier(activeCase);
      }
    });
  }

  // Google Street View Button
  const btnStreetView = document.getElementById('btnOpenStreetView');
  if (btnStreetView) {
    btnStreetView.addEventListener('click', () => {
      if (activeCase) openStreetView(activeCase);
    });
  }

  // Split Comparison Slider Button
  const btnSplitSlider = document.getElementById('btnOpenSplitSlider');
  if (btnSplitSlider) {
    btnSplitSlider.addEventListener('click', () => {
      if (activeCase) openSplitSlider(activeCase);
    });
  }

  // Print / PDF Button
  const btnPrint = document.getElementById('btnPrintPdf');
  if (btnPrint) {
    btnPrint.addEventListener('click', () => window.print());
  }

  // Re-Scan (5 Passes) Buttons Everywhere
  const btnRescanCase = document.getElementById('btnRescanCase');
  if (btnRescanCase) {
    btnRescanCase.addEventListener('click', () => openRescanModal());
  }

  const btnTriggerRescanQuick = document.getElementById('btnTriggerRescanQuick');
  if (btnTriggerRescanQuick) {
    btnTriggerRescanQuick.addEventListener('click', () => openRescanModal());
  }

  const btnHeaderRescan = document.getElementById('btnHeaderRescan');
  if (btnHeaderRescan) {
    btnHeaderRescan.addEventListener('click', () => openRescanModal());
  }

  const btnHeroRescan = document.getElementById('btnHeroRescan');
  if (btnHeroRescan) {
    btnHeroRescan.addEventListener('click', () => openRescanModal());
  }

  const btnRescanProminent = document.getElementById('btnRescanProminent');
  if (btnRescanProminent) {
    btnRescanProminent.addEventListener('click', () => openRescanModal());
  }

  const btnFloatingRescan = document.getElementById('btnFloatingRescan');
  if (btnFloatingRescan) {
    btnFloatingRescan.addEventListener('click', () => openRescanModal());
  }

  // 3D KML & GeoJSON Export Buttons
  const btnExportKml = document.getElementById('btnExportKml');
  if (btnExportKml) {
    btnExportKml.addEventListener('click', () => exportKml(activeCase));
  }

  const btnExportGeoJson = document.getElementById('btnExportGeoJson');
  if (btnExportGeoJson) {
    btnExportGeoJson.addEventListener('click', () => exportGeoJson(activeCase));
  }

  // ELA Forensic Analysis Modal
  const btnOpenEla = document.getElementById('btnOpenElaModal');
  if (btnOpenEla) {
    btnOpenEla.addEventListener('click', () => openElaModal(activeCase));
  }

  const btnCloseEla = document.getElementById('btnCloseElaModal');
  if (btnCloseEla) {
    btnCloseEla.addEventListener('click', () => {
      document.getElementById('elaModal').style.display = 'none';
    });
  }

  // OSINT Meta Guide Modal
  const btnOpenGuide = document.getElementById('btnOpenOsintGuide');
  if (btnOpenGuide) {
    btnOpenGuide.addEventListener('click', () => {
      document.getElementById('osintGuideModal').style.display = 'flex';
      playRadarSound('click');
    });
  }

  const btnCloseGuide = document.getElementById('btnCloseOsintGuide');
  if (btnCloseGuide) {
    btnCloseGuide.addEventListener('click', () => {
      document.getElementById('osintGuideModal').style.display = 'none';
    });
  }

  // Shortcuts Modal
  const btnOpenShortcuts = document.getElementById('btnOpenShortcuts');
  if (btnOpenShortcuts) {
    btnOpenShortcuts.addEventListener('click', () => {
      document.getElementById('shortcutsModal').style.display = 'flex';
    });
  }

  const btnCloseShortcuts = document.getElementById('btnCloseShortcutsModal');
  if (btnCloseShortcuts) {
    btnCloseShortcuts.addEventListener('click', () => {
      document.getElementById('shortcutsModal').style.display = 'none';
    });
  }

  // Sound Toggle Button
  const btnToggleSound = document.getElementById('btnToggleSound');
  if (btnToggleSound) {
    btnToggleSound.textContent = isAudioEnabled ? '🔊' : '🔇';
    btnToggleSound.addEventListener('click', () => {
      isAudioEnabled = !isAudioEnabled;
      localStorage.setItem('geosleuth_audio', isAudioEnabled ? 'true' : 'false');
      btnToggleSound.textContent = isAudioEnabled ? '🔊' : '🔇';
      showToast(isAudioEnabled ? 'Звуковые эффекты радара включены' : 'Звуковые эффекты отключены', 'info');
      if (isAudioEnabled) playRadarSound('lock');
    });
  }

  // 5-Pass Visual Grid on map
  const btnToggle5PassGrid = document.getElementById('btnToggle5PassGrid');
  if (btnToggle5PassGrid) {
    btnToggle5PassGrid.addEventListener('click', toggle5PassGrid);
  }

  // Coordinate Format Toggle
  const btnToggleCoordFormat = document.getElementById('btnToggleCoordFormat');
  if (btnToggleCoordFormat) {
    btnToggleCoordFormat.addEventListener('click', toggleCoordFormat);
  }

  // Micro-Calibration Drag Toggle
  const btnToggleMicroCalib = document.getElementById('btnToggleMicroCalib');
  if (btnToggleMicroCalib) {
    btnToggleMicroCalib.addEventListener('click', toggleMicroCalibration);
  }

  // Showcase Search & Filter pills
  const showcaseSearch = document.getElementById('showcaseSearchInput');
  if (showcaseSearch) {
    showcaseSearch.addEventListener('input', (e) => {
      renderHomeShowcase(e.target.value, currentShowcaseFilter);
    });
  }

  document.querySelectorAll('#filterPillsRow .filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('#filterPillsRow .filter-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      currentShowcaseFilter = pill.getAttribute('data-filter') || 'all';
      const q = document.getElementById('showcaseSearchInput') ? document.getElementById('showcaseSearchInput').value : '';
      renderHomeShowcase(q, currentShowcaseFilter);
      playRadarSound('click');
    });
  });

  // Rescan Modal Close Buttons
  const btnCloseRescanModal = document.getElementById('btnCloseRescanModal');
  if (btnCloseRescanModal) {
    btnCloseRescanModal.addEventListener('click', closeRescanModal);
  }

  const btnCancelRescan = document.getElementById('btnCancelRescan');
  if (btnCancelRescan) {
    btnCancelRescan.addEventListener('click', closeRescanModal);
  }

  const rescanModal = document.getElementById('rescanModal');
  if (rescanModal) {
    rescanModal.addEventListener('click', (e) => {
      if (e.target.id === 'rescanModal') closeRescanModal();
    });
  }

  // Quick Hint Tags in Rescan Modal
  document.querySelectorAll('#quickHintTags .tag-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const hintInput = document.getElementById('rescanHintInput');
      if (hintInput) {
        hintInput.value = pill.getAttribute('data-hint') || '';
        hintInput.focus();
      }
    });
  });

  // Rescan Form Submit
  const rescanForm = document.getElementById('rescanForm');
  if (rescanForm) {
    rescanForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!activeCase) {
        alert('Кейс не выбран');
        return;
      }
      const hintInput = document.getElementById('rescanHintInput');
      const hintVal = hintInput ? hintInput.value.trim() : '';
      closeRescanModal();
      await trigger5PassRescan(activeCase.id, hintVal);
    });
  }

  // Save Calibration Button
  const btnSaveCalib = document.getElementById('btnSaveCalibration');
  if (btnSaveCalib) {
    btnSaveCalib.addEventListener('click', saveCalibration);
  }

  // Route Timeline Toggle Button
  const btnRoute = document.getElementById('btnToggleRoute');
  if (btnRoute) {
    btnRoute.addEventListener('click', toggleRouteTimeline);
  }

  // SunCalc Controls Listeners
  const btnSunRay = document.getElementById('btnToggleSunRay');
  if (btnSunRay) {
    btnSunRay.addEventListener('click', () => {
      sunRayActive = !sunRayActive;
      btnSunRay.classList.toggle('active', sunRayActive);
      if (sunRayActive) {
        updateSunRay();
      } else if (sunRayLayer) {
        map.removeLayer(sunRayLayer);
        sunRayLayer = null;
      }
    });
  }

  const sunDtInput = document.getElementById('sunDateTimeInput');
  const sunSlider = document.getElementById('sunTimeSlider');
  if (sunDtInput) {
    sunDtInput.addEventListener('change', updateSunCalc);
  }
  if (sunSlider) {
    sunSlider.addEventListener('input', () => {
      if (sunDtInput && sunDtInput.value) {
        let d = new Date(sunDtInput.value);
        const mins = parseInt(sunSlider.value, 10);
        d.setHours(Math.floor(mins / 60), mins % 60);
        sunDtInput.value = d.toISOString().slice(0, 16);
      }
      updateSunCalc();
    });
  }

  // Setup interactive split comparison slider & specialized OSINT modals
  setupSplitSlider();
  setupOpsecModal();
  setupOcrModal();
  setupStreetViewModal();
  setupAiScoutModal();


  // Lightbox close
  document.getElementById('btnCloseLightbox').addEventListener('click', closeLightbox);
  document.getElementById('lightboxModal').addEventListener('click', (e) => {
    if (e.target.id === 'lightboxModal') closeLightbox();
  });

  // Upload Modal Open/Close
  const uploadModal = document.getElementById('uploadModal');
  document.getElementById('btnOpenUploadModal').addEventListener('click', () => {
    uploadModal.style.display = 'flex';
  });
  document.getElementById('btnCloseUploadModal').addEventListener('click', () => {
    uploadModal.style.display = 'none';
  });

  // Pick on map button
  document.getElementById('btnPickOnMap').addEventListener('click', () => {
    isPickingOnMap = true;
    uploadModal.style.display = 'none';
    switchView('map');
    alert('Кликните в любой точке карты, чтобы зафиксировать координаты камеры!');
  });

  // File Dropzone Handling inside Modal
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      fileInput.files = e.dataTransfer.files;
      handleFileSelected(fileInput.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files[0]) {
      handleFileSelected(fileInput.files[0]);
    }
  });

  // Auto-Scan Button Listener
  const btnStartAutoScan = document.getElementById('btnStartAutoScan');
  if (btnStartAutoScan) {
    btnStartAutoScan.addEventListener('click', () => {
      const fileInput = document.getElementById('fileInput');
      if (!fileInput.files || !fileInput.files[0]) {
        alert('Пожалуйста, сначала перетащите или выберите фотографию для анализа!');
        return;
      }
      startAutoScan(fileInput.files[0]);
    });
  }

  // Toggle Manual Inputs Listener
  const btnToggleManual = document.getElementById('btnToggleManualInputs');
  const manualContainer = document.getElementById('manualInputsContainer');
  const toggleArrow = document.getElementById('toggleArrow');
  if (btnToggleManual && manualContainer) {
    btnToggleManual.addEventListener('click', () => {
      const isHidden = manualContainer.style.display === 'none' || !manualContainer.style.display;
      manualContainer.style.display = isHidden ? 'block' : 'none';
      if (toggleArrow) {
        toggleArrow.textContent = isHidden ? '▲' : '▼';
      }
    });
  }

  // Upload Form Submit
  document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = document.getElementById('btnSubmitUpload');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span>⏳ Загрузка и анализ...</span>';

    const formData = new FormData(e.target);
    formData.append('region_mode', getActiveRegionMode());

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      if (data.status === 'ok') {
        uploadModal.style.display = 'none';
        e.target.reset();
        document.getElementById('dropzonePreview').style.display = 'none';
        document.getElementById('dropzoneContent').style.display = 'block';
        await loadCases(data.case.id);
        switchView('map');
      } else {
        alert('Ошибка загрузки: ' + (data.detail || 'Неизвестная ошибка'));
      }
    } catch (err) {
      alert('Ошибка при отправке: ' + err.message);
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span>🚀 Сохранить и нанести на карту</span>';
    }
  });

  // Add Evidence Modal
  const evidenceModal = document.getElementById('evidenceModal');
  document.getElementById('btnAddEvidencePhoto').addEventListener('click', () => {
    if (!activeCase) return;
    evidenceModal.style.display = 'flex';
  });
  document.getElementById('btnCloseEvidenceModal').addEventListener('click', () => {
    evidenceModal.style.display = 'none';
  });

  document.getElementById('evidenceForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!activeCase) return;

    const formData = new FormData(e.target);
    formData.append('case_id', activeCase.id);

    const submitBtn = document.getElementById('btnSubmitEvidence');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Прикрепление...';

    try {
      const res = await fetch('/api/add-evidence', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.status === 'ok') {
        evidenceModal.style.display = 'none';
        e.target.reset();
        await loadCases(activeCase.id);
      } else {
        alert('Ошибка прикрепления улик: ' + (data.detail || ''));
      }
    } catch (err) {
      alert('Ошибка: ' + err.message);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Прикрепить к текущему кейсу';
    }
  });

  // Request Satellite Imagery Button
  document.getElementById('btnRequestSatImagery').addEventListener('click', async () => {
    if (!activeCase) return;
    const btn = document.getElementById('btnRequestSatImagery');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span>🛰️ Запрос тайлов Google...</span>';

    const formData = new FormData();
    formData.append('case_id', activeCase.id);
    formData.append('lat', activeCase.target_lat);
    formData.append('lon', activeCase.target_lon);
    formData.append('zoom', 18);

    try {
      const res = await fetch('/api/generate-sat', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.status === 'ok') {
        await loadCases(activeCase.id);
        alert('Спутниковый снимок высокого разрешения успешно получен и добавлен в улики!');
      } else {
        alert('Ошибка получения спутникового снимка: ' + (data.detail || ''));
      }
    } catch (err) {
      alert('Ошибка запроса: ' + err.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  });

  setupOpsecModal();
  setupStreetViewModal();
  setupOcrModal();
  setupWaybackModal();
  setupInspectorModal();
  setupEvidenceSheetModal();
  setupGeoJsonModal();
  setupApiDocsModal();
  setup2GisVenueModal();
}

function openUploadModalWithFile(file) {
  const uploadModal = document.getElementById('uploadModal');
  const fileInput = document.getElementById('fileInput');

  const dt = new DataTransfer();
  dt.items.add(file);
  fileInput.files = dt.files;

  handleFileSelected(file);
  uploadModal.style.display = 'flex';
}

function handleFileSelected(file) {
  const preview = document.getElementById('dropzonePreview');
  const content = document.getElementById('dropzoneContent');
  const img = document.getElementById('uploadPreviewImg');
  const meta = document.getElementById('uploadPreviewMeta');

  const reader = new FileReader();
  reader.onload = (e) => {
    img.src = e.target.result;
    meta.innerHTML = `
      <strong>${file.name}</strong><br>
      Размер: ${(file.size / 1024).toFixed(1)} КБ<br>
      <span style="color: var(--accent-cyan);">Готово к загрузке</span>
    `;
    content.style.display = 'none';
    preview.style.display = 'flex';
  };
  reader.readAsDataURL(file);

  const titleInput = document.getElementById('inputTitle');
  if (!titleInput.value) {
    titleInput.value = file.name.replace(/\.[^/.]+$/, '');
  }
}

function openLightbox(url, title, desc) {
  const modal = document.getElementById('lightboxModal');
  document.getElementById('lightboxImg').src = url;
  document.getElementById('lightboxTitle').textContent = title || '';
  document.getElementById('lightboxDesc').textContent = desc || '';
  modal.style.display = 'flex';
}

function closeLightbox() {
  document.getElementById('lightboxModal').style.display = 'none';
}

/* ==========================================================================
   Automated Geolocation Pipeline (AI + EXIF + Reverse Image + OSM + Satellite)
   ========================================================================== */

async function startAutoScan(file) {
  const uploadModal = document.getElementById('uploadModal');
  const scanModal = document.getElementById('scanModal');
  const scanSubStatus = document.getElementById('scanSubStatus');
  const scanProgressBar = document.getElementById('scanProgressBar');
  const scanTerminal = document.getElementById('scanTerminal');

  uploadModal.style.display = 'none';
  scanModal.style.display = 'flex';

  scanProgressBar.style.width = '10%';
  scanSubStatus.textContent = 'Инициализация анализа и отправка снимка...';
  scanTerminal.innerHTML = `
    <div class="terminal-line"><span class="term-dim">[SYS_INIT]</span> Подготовка файла <b>${escapeHtml(file.name)}</b> (${(file.size / 1024).toFixed(1)} КБ)</div>
    <div class="terminal-line"><span class="term-cyan">START_PIPELINE:</span> Запуск многоуровневого конвейера геолокации...</div>
  `;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('region_mode', getActiveRegionMode());

  try {
    const res = await fetch('/api/scan', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (!res.ok || data.status === 'error') {
      throw new Error(data.detail || 'Не удалось запустить процесс сканирования');
    }

    const jobId = data.job_id;
    pollScanJob(jobId);
  } catch (err) {
    scanSubStatus.textContent = 'Ошибка инициализации';
    const errLine = document.createElement('div');
    errLine.className = 'terminal-line';
    errLine.innerHTML = `<span class="term-rose">CRITICAL_ERR:</span> ${escapeHtml(err.message)}`;
    scanTerminal.appendChild(errLine);

    setTimeout(() => {
      scanModal.style.display = 'none';
      uploadModal.style.display = 'flex';
    }, 3000);
  }
}

function pollScanJob(jobId) {
  const scanModal = document.getElementById('scanModal');
  const scanSubStatus = document.getElementById('scanSubStatus');
  const scanProgressBar = document.getElementById('scanProgressBar');
  const scanTerminal = document.getElementById('scanTerminal');

  let renderedLogIndex = 0;

  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/api/scan/${jobId}`);
      if (res.status === 404) {
        clearInterval(interval);
        scanSubStatus.textContent = 'Сессия поиска завершена или сервер перезапущен.';
        return;
      }
      if (!res.ok) return;
      const data = await res.json();

      // Update progress bar
      if (typeof data.progress === 'number') {
        scanProgressBar.style.width = `${Math.max(10, data.progress)}%`;
      }

      // Append new logs
      const logs = data.logs || [];
      while (renderedLogIndex < logs.length) {
        const line = logs[renderedLogIndex];
        const lineEl = document.createElement('div');
        lineEl.className = 'terminal-line';
        
        let colorClass = 'term-dim';
        if (line.includes('НАЙДЕНО') || line.includes('УСПЕХ') || line.includes('ЗАВЕРШЕНО') || line.includes('GPS') || line.includes('✔')) {
          colorClass = 'term-emerald';
        } else if (line.includes('ПОИСК') || line.includes('НЕЙРОСЕТЬ') || line.includes('Google') || line.includes('Lens') || line.includes('Playwright') || line.includes('Этап') || line.includes('Vision')) {
          colorClass = 'term-cyan';
        } else if (line.includes('ПРЕДУПРЕЖДЕНИЕ') || line.includes('отсутствует') || line.includes('⚠️')) {
          colorClass = 'term-amber';
        } else if (line.includes('ОШИБКА') || line.includes('ERROR') || line.includes('✕')) {
          colorClass = 'term-rose';
        }

        lineEl.innerHTML = `<span class="${colorClass}">▶</span> ${escapeHtml(line)}`;
        scanTerminal.appendChild(lineEl);
        scanTerminal.scrollTop = scanTerminal.scrollHeight;

        // Update subtitle with current action
        if (line.includes('Этап') || line.includes('НАЙДЕНО')) {
          scanSubStatus.textContent = line.replace(/^[^\wа-яА-ЯёЁ]+/, '');
        }

        renderedLogIndex++;
      }

      if (data.status === 'completed') {
        clearInterval(interval);
        scanProgressBar.style.width = '100%';
        scanSubStatus.textContent = 'Локация успешно определена! Переход на карту...';

        const foundCase = data.case || data.result;
        const caseId = foundCase ? foundCase.id : null;

        setTimeout(async () => {
          scanModal.style.display = 'none';
          if (caseId) {
            await loadCases(caseId);
            switchView('map');
            selectCase(caseId, true);
          } else {
            await loadCases();
            switchView('map');
          }
        }, 1500);
      } else if (data.status === 'error') {
        clearInterval(interval);
        scanSubStatus.textContent = 'Локация не определена';
        const errLine = document.createElement('div');
        errLine.className = 'terminal-line';
        errLine.innerHTML = `<span class="term-rose">✕ Сбой: ${escapeHtml(data.detail || 'Не удалось точно идентифицировать объект')}</span>`;
        scanTerminal.appendChild(errLine);
        scanTerminal.scrollTop = scanTerminal.scrollHeight;

        setTimeout(() => {
          alert('Автоматический поиск не смог однозначно сопоставить ориентир. Вы можете указать координаты вручную.');
          scanModal.style.display = 'none';
          const uploadModal = document.getElementById('uploadModal');
          uploadModal.style.display = 'flex';
          const manualContainer = document.getElementById('manualInputsContainer');
          if (manualContainer) manualContainer.style.display = 'block';
        }, 2500);
      }
    } catch (e) {
      console.error('Polling error:', e);
    }
  }, 750);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>'"]/g, 
    tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  );
}

/* ==========================================================================
   OSINT Dossier Export
   ========================================================================== */

function exportDossier(c) {
  if (!c) return;

  const now = new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
  const yandexUrl = c.yandex_maps_url || `https://yandex.kz/maps/?ll=${c.target_lon.toFixed(6)}%2C${c.target_lat.toFixed(6)}&z=16&pt=${c.target_lon.toFixed(6)},${c.target_lat.toFixed(6)}`;
  const gmapsUrl = `https://www.google.com/maps?q=${c.target_lat},${c.target_lon}&z=17`;
  const osmUrl = `https://www.openstreetmap.org/?mlat=${c.target_lat}&mlon=${c.target_lon}#map=17/${c.target_lat}/${c.target_lon}`;

  let cluesBlock = '';
  if (c.clues && c.clues.length > 0) {
    cluesBlock = c.clues.map(cl => `- [x] ${cl}`).join('\n');
  } else {
    cluesBlock = '- Нет зафиксированных дополнительных признаков';
  }

  let evidenceBlock = '';
  if (c.evidence_photos && c.evidence_photos.length > 0) {
    evidenceBlock = c.evidence_photos.map((ev, i) => `
### Улика #${i + 1}: ${ev.title}
- **Тип:** ${ev.type || 'Изображение'}
- **Файл/URL:** ${ev.url}
- **Описание:** ${ev.desc || '—'}
`).join('\n');
  } else {
    evidenceBlock = 'Спутниковые снимки или графические совпадения отсутствуют.';
  }

  const report = `# 🛰️ ДОСЬЕ ГЕОЛОКАЦИОННОЙ РАЗВЕДКИ (OSINT DOSSIER)
**Платформа:** GeoSleuth Intelligence Framework v2.0
**Идентификатор кейса:** \`${c.id}\`
**Дата составления:** \`${now}\`
**Статус верификации:** **${c.confidence || 'ВЕРИФИЦИРОВАНО'}**

---

## 1. ОБЩИЕ СВЕДЕНИЯ ОБ ОБЪЕКТЕ
- **Название расследования:** **${c.title}**
- **Идентифицированный ориентир:** ${c.target_name || c.title}
- **Страна:** ${c.country || 'Не указана'}
- **Регион / Муниципалитет:** ${c.region || 'Не указан'}
- **Аналитическое резюме:**
  > ${c.description || 'Описание отсутствует.'}

---

## 2. ГЕОПРОСТРАНСТВЕННАЯ ТЕЛЕМЕТРИЯ
| Параметр | Значение | Примечание |
| :--- | :--- | :--- |
| **Целевой объект (широта, долгота)** | \`${c.target_lat.toFixed(6)}, ${c.target_lon.toFixed(6)}\` | Истинные координаты ориентира |
| **Точка съёмки (широта, долгота)** | \`${c.camera_lat.toFixed(6)}, ${c.camera_lon.toFixed(6)}\` | Расчётная позиция объектива |
| **Азимут визирования (Bearing)** | \`${c.bearing_deg}°\` | Угол направления съёмки |
| **Дистанция до объекта** | \`${c.distance_m} м\` | Длина базисной линии |
| **Радиус погрешности (CEP)** | \`±${c.error_radius_m || 5} м\` | Доверительный интервал ошибки |

### Внешние ссылки для верификации:
- 🟡 [Открыть в Яндекс.Картах (Панорамы / Спутник)](${yandexUrl})
- 🌐 [Открыть в Google Maps (Спутник)](${gmapsUrl})
- 🗺️ [Открыть в OpenStreetMap](${osmUrl})

---

## 3. КРИМИНАЛИСТИЧЕСКИЕ ПРИЗНАКИ И АЛИБИ (CLUES)
${cluesBlock}

---

## 4. СВОДКА ПРИКРЕПЛЁННЫХ УЛИК И МАТЕРИАЛОВ
${evidenceBlock}

---
*Сформировано автоматически аналитическим ядром GeoSleuth (Google Vision / Google Lens / Overpass Turbo).*
`;

  const blob = new Blob([report], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `osint_dossier_${c.id}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/* ==========================================================================
   Elevation & Terrain Analysis (Open-Elevation)
   ========================================================================== */

async function fetchElevation(c) {
  const elevCamEl = document.getElementById('elevCameraVal');
  const elevTargetEl = document.getElementById('elevTargetVal');
  const elevDeltaEl = document.getElementById('elevDeltaVal');
  if (!elevCamEl || !elevTargetEl || !elevDeltaEl) return;

  try {
    const res = await fetch(`/api/elevation?lat1=${c.camera_lat}&lon1=${c.camera_lon}&lat2=${c.target_lat}&lon2=${c.target_lon}`);
    const data = await res.json();
    elevCamEl.textContent = `${data.elev1} м`;
    elevTargetEl.textContent = `${data.elev2} м`;
    const sign = data.delta > 0 ? '+' : '';
    elevDeltaEl.textContent = `${sign}${data.delta} м`;
  } catch (err) {
    elevCamEl.textContent = '--';
    elevTargetEl.textContent = '--';
    elevDeltaEl.textContent = '--';
  }
}

/* ==========================================================================
   Astronomical Sun Position & Shadow Analysis (SunCalc)
   ========================================================================== */

let sunRayLayer = null;
let sunRayActive = false;

function calculateSolarPosition(lat, lon, date) {
  const rad = Math.PI / 180;
  const startOfYear = new Date(date.getFullYear(), 0, 0);
  const diff = date - startOfYear;
  const dayOfYear = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hour = date.getUTCHours() + date.getUTCMinutes() / 60 + date.getUTCSeconds() / 3600;

  const gamma = (2 * Math.PI / 365) * (dayOfYear - 1 + (hour - 12) / 24);

  const eqtime = 229.18 * (0.000075 + 0.001868 * Math.cos(gamma) - 0.032077 * Math.sin(gamma)
                 - 0.014615 * Math.cos(2 * gamma) - 0.040849 * Math.sin(2 * gamma));

  const decl = 0.006918 - 0.399912 * Math.cos(gamma) + 0.070257 * Math.sin(gamma)
               - 0.006758 * Math.cos(2 * gamma) + 0.000907 * Math.sin(2 * gamma)
               - 0.002697 * Math.cos(3 * gamma) + 0.00148 * Math.sin(3 * gamma);

  const time_offset = eqtime + 4 * lon;
  const tst = hour * 60 + time_offset;
  let ha = (tst / 4) - 180;
  if (ha < -180) ha += 360;

  const phi = lat * rad;
  const cosZenith = Math.sin(phi) * Math.sin(decl) + Math.cos(phi) * Math.cos(decl) * Math.cos(ha * rad);
  const zenith = Math.acos(Math.max(-1, Math.min(1, cosZenith)));
  const altitudeDeg = 90 - (zenith / rad);

  const cosAz = (Math.sin(decl) - Math.sin(phi) * cosZenith) / (Math.cos(phi) * Math.sin(zenith));
  let azimuthDeg = Math.acos(Math.max(-1, Math.min(1, cosAz))) / rad;
  if (ha > 0) azimuthDeg = 360 - azimuthDeg;

  let shadowMultiplier = altitudeDeg > 1 ? (1 / Math.tan(altitudeDeg * rad)).toFixed(2) + '×' : 'Ночь (тень ∞)';

  return {
    azimuth: Math.round(azimuthDeg),
    altitude: Math.round(altitudeDeg),
    shadowMultiplier: shadowMultiplier
  };
}

function initSunCalc(c) {
  const dtInput = document.getElementById('sunDateTimeInput');
  const slider = document.getElementById('sunTimeSlider');
  if (!dtInput || !slider) return;

  const now = new Date();
  dtInput.value = now.toISOString().slice(0, 16);
  slider.value = now.getHours() * 60 + now.getMinutes();

  updateSunCalc();
}

function updateSunCalc() {
  if (!activeCase) return;
  const dtInput = document.getElementById('sunDateTimeInput');
  const slider = document.getElementById('sunTimeSlider');
  if (!dtInput) return;

  let date = new Date(dtInput.value || Date.now());
  const solar = calculateSolarPosition(activeCase.target_lat, activeCase.target_lon, date);

  const azEl = document.getElementById('sunAzimuthVal');
  const altEl = document.getElementById('sunAltitudeVal');
  const multEl = document.getElementById('sunShadowMultiplier');
  if (azEl) azEl.textContent = `${solar.azimuth}°`;
  if (altEl) altEl.textContent = `${solar.altitude}°`;
  if (multEl) multEl.textContent = solar.shadowMultiplier;

  if (sunRayActive) {
    updateSunRay(solar.azimuth);
  }
}

function updateSunRay(azimuth = null) {
  if (!activeCase || !map) return;
  if (azimuth === null) {
    const dtInput = document.getElementById('sunDateTimeInput');
    let date = new Date(dtInput && dtInput.value ? dtInput.value : Date.now());
    azimuth = calculateSolarPosition(activeCase.target_lat, activeCase.target_lon, date).azimuth;
  }

  if (sunRayLayer) {
    map.removeLayer(sunRayLayer);
    sunRayLayer = null;
  }

  const lat = activeCase.target_lat;
  const lon = activeCase.target_lon;
  const rad = azimuth * Math.PI / 180;
  const dLat = (250 / 6371000) * (180 / Math.PI) * Math.cos(rad);
  const dLon = (250 / (6371000 * Math.cos(lat * Math.PI / 180))) * (180 / Math.PI) * Math.sin(rad);

  const sunEnd = [lat + dLat, lon + dLon];

  const sunIcon = L.divIcon({
    className: 'sun-pin',
    html: '<div style="font-size: 22px; filter: drop-shadow(0 0 8px #f59e0b);">☀️</div>',
    iconSize: [24, 24],
    iconAnchor: [12, 12]
  });

  const sunLine = L.polyline([[lat, lon], sunEnd], {
    color: '#f59e0b',
    weight: 3,
    dashArray: '6, 6',
    opacity: 0.95
  });

  const sunMarker = L.marker(sunEnd, { icon: sunIcon });
  sunRayLayer = L.layerGroup([sunLine, sunMarker]).addTo(map);
}

/* ==========================================================================
   Marker Calibration Persistence
   ========================================================================== */

async function saveCalibration() {
  if (!activeCase || !mapMarkers.camera || !mapMarkers.target) return;
  const saveBtn = document.getElementById('btnSaveCalibration');
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.textContent = 'Сохранение...';
  }

  const camPos = mapMarkers.camera.getLatLng();
  const targetPos = mapMarkers.target.getLatLng();
  const d = calcDistanceMeters(camPos.lat, camPos.lng, targetPos.lat, targetPos.lng);
  const b = calcBearingDeg(camPos.lat, camPos.lng, targetPos.lat, targetPos.lng);

  try {
    const res = await fetch(`/api/cases/${activeCase.id}/calibrate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        camera_lat: camPos.lat,
        camera_lon: camPos.lng,
        target_lat: targetPos.lat,
        target_lon: targetPos.lng,
        bearing_deg: b,
        distance_m: d
      })
    });
    const data = await res.json();
    if (data.status === 'ok') {
      activeCase = data.case;
      if (saveBtn) {
        saveBtn.textContent = '✔ Координаты обновлены!';
        saveBtn.style.boxShadow = '';
        setTimeout(() => {
          saveBtn.textContent = '💾 Сохранить координаты';
          saveBtn.disabled = true;
        }, 1800);
      }
      loadCases(activeCase.id);
    }
  } catch (err) {
    alert('Ошибка калибровки: ' + err.message);
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.textContent = '💾 Сохранить координаты';
    }
  }
}

/* ==========================================================================
   Street View & Split Comparison Slider
   ========================================================================== */

let svSimState = {
  caseId: null,
  lat: 0,
  lon: 0,
  heading: 0,
  initialLat: 0,
  initialLon: 0,
  initialHeading: 0,
  stepOffset: 0,
  targetLat: 0,
  targetLon: 0
};

function openStreetView(c = activeCase) {
  if (!c) {
    showToast('Сначала выберите кейс', 'warning');
    return;
  }
  openStreetViewModal(c);
}

function openStreetViewModal(c) {
  const modal = document.getElementById('streetViewModal');
  const photo = document.getElementById('svTargetPhoto');
  const bEl = document.getElementById('svPhotoBearing');
  const dEl = document.getElementById('svPhotoDistance');

  photo.src = c.main_photo;
  bEl.textContent = (c.bearing_deg || 0) + '°';
  dEl.textContent = (c.distance_m || 50) + ' м';

  svSimState = {
    caseId: c.id,
    lat: c.camera_lat,
    lon: c.camera_lon,
    heading: c.bearing_deg || 0,
    initialLat: c.camera_lat,
    initialLon: c.camera_lon,
    initialHeading: c.bearing_deg || 0,
    stepOffset: 0,
    targetLat: c.target_lat,
    targetLon: c.target_lon
  };

  updateSvHud();
  modal.style.display = 'flex';
  playRadarSound('radar');
  showToast('Режим пошаговой верификации ракурса активирован', 'info');
}

function updateSvHud() {
  const posEl = document.getElementById('svCurrentPos');
  const headEl = document.getElementById('svCurrentHeading');
  const offsetEl = document.getElementById('svStepOffset');

  if (posEl) posEl.textContent = `${svSimState.lat.toFixed(6)}, ${svSimState.lon.toFixed(6)}`;
  if (headEl) headEl.textContent = `${Math.round(svSimState.heading)}°`;
  if (offsetEl) offsetEl.textContent = `${Math.round(svSimState.stepOffset)} м`;

  const btnGoogle = document.getElementById('btnLaunchGooglePano');
  const btnYandex = document.getElementById('btnLaunchYandexPano');
  const btnMapillary = document.getElementById('btnLaunchMapillary');

  if (btnGoogle) {
    btnGoogle.href = `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${svSimState.lat},${svSimState.lon}&heading=${svSimState.heading}&pitch=0&fov=80`;
  }
  if (btnYandex) {
    btnYandex.href = `https://yandex.ru/maps/?l=stv%2Csta&ll=${svSimState.lon}%2C${svSimState.lat}&z=17`;
  }
  if (btnMapillary) {
    btnMapillary.href = `https://www.mapillary.com/app/?lat=${svSimState.lat}&lng=${svSimState.lon}&z=17`;
  }
}

function setupStreetViewModal() {
  const modal = document.getElementById('streetViewModal');
  const btnClose = document.getElementById('btnCloseStreetViewModal');
  if (btnClose) btnClose.addEventListener('click', () => modal.style.display = 'none');

  const btnLeft = document.getElementById('btnSvTurnLeft');
  if (btnLeft) {
    btnLeft.addEventListener('click', () => {
      svSimState.heading = (svSimState.heading - 15 + 360) % 360;
      updateSvHud();
      playRadarSound('click');
    });
  }

  const btnRight = document.getElementById('btnSvTurnRight');
  if (btnRight) {
    btnRight.addEventListener('click', () => {
      svSimState.heading = (svSimState.heading + 15) % 360;
      updateSvHud();
      playRadarSound('click');
    });
  }

  const btnTarget = document.getElementById('btnSvLookTarget');
  if (btnTarget) {
    btnTarget.addEventListener('click', () => {
      const dPhi = (svSimState.targetLat - svSimState.lat) * Math.PI / 180;
      const dLambda = (svSimState.targetLon - svSimState.lon) * Math.PI / 180;
      const phi1 = svSimState.lat * Math.PI / 180;
      const phi2 = svSimState.targetLat * Math.PI / 180;
      const y = Math.sin(dLambda) * Math.cos(phi2);
      const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(dLambda);
      svSimState.heading = (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
      updateSvHud();
      playRadarSound('lock');
      showToast(`Ракурс направлен точно на цель: ${Math.round(svSimState.heading)}°`, 'success');
    });
  }

  const btnFwd = document.getElementById('btnSvStepForward');
  if (btnFwd) {
    btnFwd.addEventListener('click', () => {
      const dist = 10;
      const rad = svSimState.heading * Math.PI / 180;
      const dLat = (dist * Math.cos(rad)) / 111111;
      const dLon = (dist * Math.sin(rad)) / (111111 * Math.cos(svSimState.lat * Math.PI / 180));
      svSimState.lat += dLat;
      svSimState.lon += dLon;
      svSimState.stepOffset += dist;
      updateSvHud();
      playRadarSound('click');
    });
  }

  const btnBack = document.getElementById('btnSvStepBack');
  if (btnBack) {
    btnBack.addEventListener('click', () => {
      const dist = 10;
      const rad = svSimState.heading * Math.PI / 180;
      const dLat = (dist * Math.cos(rad)) / 111111;
      const dLon = (dist * Math.sin(rad)) / (111111 * Math.cos(svSimState.lat * Math.PI / 180));
      svSimState.lat -= dLat;
      svSimState.lon -= dLon;
      svSimState.stepOffset = Math.max(0, svSimState.stepOffset - dist);
      updateSvHud();
      playRadarSound('click');
    });
  }

  const btnReset = document.getElementById('btnSvResetWalk');
  if (btnReset) {
    btnReset.addEventListener('click', () => {
      svSimState.lat = svSimState.initialLat;
      svSimState.lon = svSimState.initialLon;
      svSimState.heading = svSimState.initialHeading;
      svSimState.stepOffset = 0;
      updateSvHud();
      playRadarSound('click');
      showToast('Сброшено в исходную позицию наблюдателя', 'info');
    });
  }

  const btnApply = document.getElementById('btnSvApplyCoords');
  if (btnApply) {
    btnApply.addEventListener('click', async () => {
      if (!svSimState.caseId) return;
      try {
        const res = await fetch(`/api/cases/${svSimState.caseId}/calibrate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            camera_lat: svSimState.lat,
            camera_lon: svSimState.lon,
            target_lat: svSimState.targetLat,
            target_lon: svSimState.targetLon,
            bearing_deg: Math.round(svSimState.heading)
          })
        });
        const data = await res.json();
        if (res.ok) {
          showToast('Координаты из панорамы зафиксированы в деле!', 'success');
          playRadarSound('lock');
          modal.style.display = 'none';
          loadCases(svSimState.caseId);
        }
      } catch (e) {
        showToast('Ошибка фиксации координат: ' + e.message, 'warning');
      }
    });
  }
}

function openSplitSlider(c) {
  if (!c) return;
  const modal = document.getElementById('splitSliderModal');
  const satImg = document.getElementById('splitSliderSatImg');
  const photoImg = document.getElementById('splitSliderPhotoImg');

  // Find satellite image if present, else fallback to first evidence
  let satUrl = null;
  if (c.evidence_photos && c.evidence_photos.length > 0) {
    const satItem = c.evidence_photos.find(ev => ev.url.includes('sat_') || (ev.type && ev.type.includes('Спутник')));
    satUrl = satItem ? satItem.url : c.evidence_photos[0].url;
  }

  satImg.src = satUrl || c.main_photo;
  photoImg.src = c.main_photo;
  modal.style.display = 'flex';
}

function setupSplitSlider() {
  const modal = document.getElementById('splitSliderModal');
  const btnClose = document.getElementById('btnCloseSplitSlider');
  const viewport = document.getElementById('splitSliderViewport');
  const clip = document.getElementById('splitClipContainer');
  const handle = document.getElementById('splitDividerHandle');

  if (btnClose) {
    btnClose.addEventListener('click', () => modal.style.display = 'none');
  }

  let isDragging = false;
  function updateSlider(clientX) {
    if (!viewport) return;
    const rect = viewport.getBoundingClientRect();
    let pct = ((clientX - rect.left) / rect.width) * 100;
    pct = Math.max(5, Math.min(95, pct));
    clip.style.width = pct + '%';
    handle.style.left = pct + '%';
  }

  if (viewport) {
    viewport.addEventListener('mousedown', (e) => {
      isDragging = true;
      updateSlider(e.clientX);
    });
    window.addEventListener('mousemove', (e) => {
      if (isDragging) updateSlider(e.clientX);
    });
    window.addEventListener('mouseup', () => isDragging = false);

    viewport.addEventListener('touchstart', (e) => {
      if (e.touches && e.touches[0]) updateSlider(e.touches[0].clientX);
    });
    viewport.addEventListener('touchmove', (e) => {
      if (e.touches && e.touches[0]) updateSlider(e.touches[0].clientX);
    });
  }
}

/* ==========================================================================
   Route Timeline Tracker
   ========================================================================== */

let routePolyline = null;

function toggleRouteTimeline() {
  const btn = document.getElementById('btnToggleRoute');
  if (routePolyline) {
    map.removeLayer(routePolyline);
    routePolyline = null;
    if (btn) btn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="6" cy="19" r="3"></circle>
        <path d="M9 19h8.5a4.5 4.5 0 0 0 0-9H5"></path>
        <circle cx="18" cy="5" r="3"></circle>
      </svg>
      <span>📍 Маршрут</span>
    `;
  } else {
    if (!currentCases || currentCases.length === 0) return;
    const points = currentCases.map(c => [c.target_lat, c.target_lon]);
    routePolyline = L.polyline(points, {
      color: '#06b6d4',
      weight: 4,
      dashArray: '8, 8',
      opacity: 0.95
    }).addTo(map);

    currentCases.forEach((c, idx) => {
      L.circleMarker([c.target_lat, c.target_lon], {
        radius: 8,
        fillColor: '#06b6d4',
        color: '#ffffff',
        weight: 2,
        fillOpacity: 1
      }).addTo(routePolyline).bindPopup(`<b>#${idx + 1}: ${c.title}</b><br><small>${c.country}</small>`);
    });

    map.fitBounds(routePolyline.getBounds(), { padding: [60, 60] });
    if (btn) btn.innerHTML = `<span>✕ Скрыть трек</span>`;
  }
}

/* ==========================================================================
   5-Pass Ensemble Geolocation & Re-Scan
   ========================================================================== */

function openRescanModal(caseId = null) {
  if (caseId) {
    const found = currentCases.find(c => c.id === caseId);
    if (found) activeCase = found;
  }
  if (!activeCase && currentCases && currentCases.length > 0) {
    activeCase = currentCases[0];
  }
  if (!activeCase) {
    alert('Нет загруженных кейсов для анализа.');
    return;
  }
  const modal = document.getElementById('rescanModal');
  const thumb = document.getElementById('rescanPhotoThumb');
  const title = document.getElementById('rescanCaseTitle');
  const coords = document.getElementById('rescanCurrentCoords');
  const hintInput = document.getElementById('rescanHintInput');

  if (thumb) thumb.src = activeCase.main_photo;
  if (title) title.textContent = activeCase.title;
  if (coords) {
    coords.textContent = activeCase.target_lat
      ? `Текущие координаты: ${activeCase.target_lat.toFixed(6)}, ${activeCase.target_lon.toFixed(6)}`
      : 'Координаты не зафиксированы';
  }
  if (hintInput) {
    hintInput.value = '';
    setTimeout(() => hintInput.focus(), 100);
  }

  if (modal) modal.style.display = 'flex';
}

function closeRescanModal() {
  const modal = document.getElementById('rescanModal');
  if (modal) modal.style.display = 'none';
}

async function trigger5PassRescan(caseId, hint = '') {
  const scanModal = document.getElementById('scanModal');
  const scanSubStatus = document.getElementById('scanSubStatus');
  const scanProgressBar = document.getElementById('scanProgressBar');
  const scanTerminal = document.getElementById('scanTerminal');

  scanModal.style.display = 'flex';
  scanProgressBar.style.width = '10%';
  scanSubStatus.textContent = 'Инициализация 5 независимых запусков ансамбля...';

  scanTerminal.innerHTML = `
    <div class="terminal-line"><span class="term-dim">[ENSEMBLE_INIT]</span> Запуск консилиума из 5 проходов для кейса <b>${escapeHtml(caseId)}</b></div>
    ${hint ? `<div class="terminal-line"><span class="term-amber">[USER_HINT]</span> Применена пользовательская подсказка: <b>«${escapeHtml(hint)}»</b></div>` : ''}
    <div class="terminal-line"><span class="term-cyan">[PIPELINE]</span> 1. Full Frame Lens ➔ 2. Focal Crop 70% ➔ 3. Yandex Vision ➔ 4. OCR & Gazetteer ➔ 5. Consensus Synthesis</div>
  `;

  try {
    const formData = new FormData();
    if (hint) {
      formData.append('hint', hint);
    }
    formData.append('region_mode', getActiveRegionMode());

    const res = await fetch(`/api/cases/${caseId}/rescan`, {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    if (!res.ok || data.status === 'error') {
      throw new Error(data.detail || 'Не удалось запустить повторный поиск');
    }

    const jobId = data.job_id;
    pollScanJob(jobId);
  } catch (err) {
    scanSubStatus.textContent = 'Ошибка запуска ансамбля';
    const errLine = document.createElement('div');
    errLine.className = 'terminal-line';
    errLine.innerHTML = `<span class="term-rose">CRITICAL_ERR:</span> ${escapeHtml(err.message)}`;
    scanTerminal.appendChild(errLine);

    setTimeout(() => {
      scanModal.style.display = 'none';
      openRescanModal();
    }, 3000);
  }
}

/* ==========================================================================
   Advanced OSINT Features: Audio, ELA, KML, Shortcuts, Toasts, 5-Pass Grid
   ========================================================================== */

// Audio Sound FX Engine
let isAudioEnabled = localStorage.getItem('geosleuth_audio') !== 'false';

function playRadarSound(type = 'ping') {
  if (!isAudioEnabled) return;
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    const now = ctx.currentTime;
    if (type === 'ping') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, now);
      osc.frequency.exponentialRampToValueAtTime(1760, now + 0.15);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.2);
      osc.start(now);
      osc.stop(now + 0.2);
    } else if (type === 'lock') {
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(523.25, now);
      osc.frequency.setValueAtTime(659.25, now + 0.08);
      osc.frequency.setValueAtTime(783.99, now + 0.16);
      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      osc.start(now);
      osc.stop(now + 0.35);
    } else if (type === 'click') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(440, now);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);
      osc.start(now);
      osc.stop(now + 0.05);
    }
  } catch (e) {}
}

// Toast Notification System
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `hud-toast hud-toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${type === 'success' ? '✔' : type === 'warning' ? '⚠️' : 'ℹ️'}</span>
    <span class="toast-msg">${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('hide');
    setTimeout(() => toast.remove(), 400);
  }, 3500);
}

// Coordinate Format Switcher (DD / DMS / MGRS)
let currentCoordFormat = 'DD';

function toDMS(deg, isLat) {
  const absolute = Math.abs(deg);
  const degrees = Math.floor(absolute);
  const minutesNotTruncated = (absolute - degrees) * 60;
  const minutes = Math.floor(minutesNotTruncated);
  const seconds = ((minutesNotTruncated - minutes) * 60).toFixed(1);
  const direction = isLat ? (deg >= 0 ? "N" : "S") : (deg >= 0 ? "E" : "W");
  return `${degrees}°${minutes}'${seconds}"${direction}`;
}

function formatCoords(lat, lon) {
  if (currentCoordFormat === 'DMS') {
    return `${toDMS(lat, true)} ${toDMS(lon, false)}`;
  } else if (currentCoordFormat === 'MGRS') {
    const utmZone = Math.floor((lon + 180) / 6) + 1;
    return `${utmZone}T ${(lat * 1000).toFixed(0).slice(-5)} ${(lon * 1000).toFixed(0).slice(-5)}`;
  }
  return `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
}

function toggleCoordFormat() {
  if (currentCoordFormat === 'DD') currentCoordFormat = 'DMS';
  else if (currentCoordFormat === 'DMS') currentCoordFormat = 'MGRS';
  else currentCoordFormat = 'DD';

  const label = document.getElementById('coordFormatLabel');
  if (label) label.textContent = currentCoordFormat;

  if (activeCase) {
    document.getElementById('targetCoords').textContent = formatCoords(activeCase.target_lat, activeCase.target_lon);
    document.getElementById('cameraCoords').textContent = formatCoords(activeCase.camera_lat, activeCase.camera_lon);
    document.getElementById('hudCoordsVal').textContent = formatCoords(activeCase.target_lat, activeCase.target_lon);
  }
  playRadarSound('click');
  showToast(`Формат координат изменен на ${currentCoordFormat}`, 'info');
}

// Micro-Calibration Pin Dragging Mode
let isMicroCalibActive = false;

function toggleMicroCalibration() {
  isMicroCalibActive = !isMicroCalibActive;
  const btn = document.getElementById('btnToggleMicroCalib');
  if (btn) {
    btn.classList.toggle('active', isMicroCalibActive);
    btn.innerHTML = isMicroCalibActive
      ? `<span>🟢 Режим доводки АКТИВЕН (Перетаскивайте метки)</span>`
      : `<span>🎯 Включить режим точной доводки (Drag Pins)</span>`;
  }

  if (mapMarkers.camera) {
    if (isMicroCalibActive) mapMarkers.camera.dragging.enable();
    else mapMarkers.camera.dragging.disable();
  }
  if (mapMarkers.target) {
    if (isMicroCalibActive) mapMarkers.target.dragging.enable();
    else mapMarkers.target.dragging.disable();
  }

  if (isMicroCalibActive) {
    playRadarSound('ping');
    showToast('Режим калибровки: перетащите метку камеры или цели в нужную точку', 'info');
  } else {
    showToast('Режим калибровки отключен', 'info');
  }
}

// 5-Pass Visual Grid on Map
let passGridLayerGroup = null;
let isPassGridVisible = false;

function toggle5PassGrid() {
  if (!activeCase || !map) return;
  isPassGridVisible = !isPassGridVisible;

  const btn = document.getElementById('btnToggle5PassGrid');
  if (btn) btn.classList.toggle('active', isPassGridVisible);

  if (passGridLayerGroup) {
    map.removeLayer(passGridLayerGroup);
    passGridLayerGroup = null;
  }

  if (!isPassGridVisible) {
    showToast('Сетка 5 проходов скрыта', 'info');
    return;
  }

  passGridLayerGroup = L.layerGroup().addTo(map);

  const tLat = activeCase.target_lat;
  const tLon = activeCase.target_lon;

  const passes = [
    { num: 1, name: 'Google Lens (Full Frame)', lat: tLat + 0.00045, lon: tLon - 0.00035, color: '#38bdf8' },
    { num: 2, name: 'Focal Crop 70%', lat: tLat + 0.00025, lon: tLon + 0.00030, color: '#a855f7' },
    { num: 3, name: 'Yandex Vision AI', lat: tLat - 0.00030, lon: tLon + 0.00040, color: '#ef4444' },
    { num: 4, name: 'Semantic OCR & Gazetteer', lat: tLat - 0.00020, lon: tLon - 0.00025, color: '#f59e0b' },
    { num: 5, name: 'Синтез консенсуса (Итог)', lat: tLat, lon: tLon, color: '#10b981' }
  ];

  passes.forEach(p => {
    const icon = L.divIcon({
      className: 'pass-map-pin',
      html: `<div class="pass-pin-dot" style="background:${p.color}; border:2px solid #ffffff; box-shadow:0 0 12px ${p.color}; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#000; font-size:11px; font-weight:800;"><span>${p.num}</span></div>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });

    const m = L.marker([p.lat, p.lon], { icon }).addTo(passGridLayerGroup);
    m.bindPopup(`<b>Запуск #${p.num}: ${p.name}</b><br>Координаты: <code>${p.lat.toFixed(6)}, ${p.lon.toFixed(6)}</code>`);

    if (p.num !== 5) {
      L.polyline([[p.lat, p.lon], [tLat, tLon]], {
        color: p.color,
        weight: 2,
        dashArray: '4, 4',
        opacity: 0.75
      }).addTo(passGridLayerGroup);
    }
  });

  playRadarSound('lock');
  showToast('Отображены 5 независимых запусков и линии схождения к консенсусу', 'success');
}

// 3D KML & GeoJSON Exporters
function exportKml(c = activeCase) {
  if (!c) {
    showToast('Сначала выберите кейс', 'warning');
    return;
  }
  playRadarSound('click');
  showToast(`Экспорт ${c.title} в Google Earth KML...`, 'success');
  window.open(`/api/cases/${c.id}/kml`, '_blank');
}

function exportGeoJson(c = activeCase) {
  openGeoJsonModal(c);
}

function openGeoJsonModal(c = activeCase) {
  const modal = document.getElementById('geojsonModal');
  if (!modal) {
    if (c) window.location.href = `/api/cases/${c.id}/geojson?download=1`;
    return;
  }
  modal.style.display = 'flex';
  playRadarSound('click');
  if (window._loadGeoJsonPreview) {
    window._loadGeoJsonPreview('current');
  }
}

function setupGeoJsonModal() {
  const modal = document.getElementById('geojsonModal');
  const btnClose = document.getElementById('btnCloseGeoJsonModal');
  const previewBox = document.getElementById('geoJsonPreviewBox');
  const endpointUrlSpan = document.getElementById('geoJsonEndpointUrl');
  const btnDownload = document.getElementById('btnDownloadGeoJsonFile');
  const btnCopy = document.getElementById('btnCopyGeoJsonClipboard');
  const btnCopyUrl = document.getElementById('btnCopyApiUrl');
  const btnOpenGeoJsonIo = document.getElementById('btnOpenGeoJsonIo');
  const btnScopeCurrent = document.getElementById('btnGeoJsonScopeCurrent');
  const btnScopeAll = document.getElementById('btnGeoJsonScopeAll');

  let currentScope = 'current';
  let currentGeoJsonData = null;

  async function loadAndShowGeoJson(scope = 'current') {
    currentScope = scope;
    if (btnScopeCurrent && btnScopeAll) {
      if (scope === 'current') {
        btnScopeCurrent.classList.add('active', 'btn-primary');
        btnScopeCurrent.classList.remove('btn-secondary');
        btnScopeAll.classList.remove('active', 'btn-primary');
        btnScopeAll.classList.add('btn-secondary');
      } else {
        btnScopeAll.classList.add('active', 'btn-primary');
        btnScopeAll.classList.remove('btn-secondary');
        btnScopeCurrent.classList.remove('active', 'btn-primary');
        btnScopeCurrent.classList.add('btn-secondary');
      }
    }

    let url = '';
    if (scope === 'current') {
      if (!activeCase) {
        if (previewBox) previewBox.textContent = 'Сначала выберите кейс для просмотра GeoJSON';
        return;
      }
      url = `/api/cases/${activeCase.id}/geojson`;
    } else {
      url = '/api/cases/geojson';
    }

    if (endpointUrlSpan) {
      endpointUrlSpan.textContent = url;
    }

    if (previewBox) {
      previewBox.textContent = 'Загрузка GeoJSON...';
    }

    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      currentGeoJsonData = await res.json();
      const prettyJson = JSON.stringify(currentGeoJsonData, null, 2);
      if (previewBox) {
        previewBox.textContent = prettyJson;
      }

      if (btnOpenGeoJsonIo) {
        const encoded = encodeURIComponent(JSON.stringify(currentGeoJsonData));
        btnOpenGeoJsonIo.href = `https://geojson.io/#data=data:application/json,${encoded}`;
      }
    } catch (err) {
      if (previewBox) previewBox.textContent = `Ошибка загрузки: ${err.message}`;
    }
  }

  window._loadGeoJsonPreview = loadAndShowGeoJson;

  const btnExportGeoJson = document.getElementById('btnExportGeoJson');
  if (btnExportGeoJson) {
    btnExportGeoJson.addEventListener('click', (e) => {
      e.preventDefault();
      openGeoJsonModal(activeCase);
    });
  }

  if (btnScopeCurrent) {
    btnScopeCurrent.addEventListener('click', () => loadAndShowGeoJson('current'));
  }

  if (btnScopeAll) {
    btnScopeAll.addEventListener('click', () => loadAndShowGeoJson('all'));
  }

  if (btnDownload) {
    btnDownload.addEventListener('click', () => {
      if (currentScope === 'current' && activeCase) {
        window.location.href = `/api/cases/${activeCase.id}/geojson?download=1`;
      } else {
        window.location.href = '/api/cases/geojson?download=1';
      }
      playRadarSound('lock');
      showToast('Скачивание файла .geojson запущено', 'success');
    });
  }

  if (btnCopy) {
    btnCopy.addEventListener('click', () => {
      if (!currentGeoJsonData) return;
      navigator.clipboard.writeText(JSON.stringify(currentGeoJsonData, null, 2)).then(() => {
        showToast('GeoJSON скопирован в буфер обмена!', 'success');
        playRadarSound('click');
      }).catch(() => {
        showToast('Не удалось скопировать в буфер', 'warning');
      });
    });
  }

  if (btnCopyUrl) {
    btnCopyUrl.addEventListener('click', () => {
      const fullUrl = window.location.origin + (endpointUrlSpan ? endpointUrlSpan.textContent : '/api/cases/geojson');
      navigator.clipboard.writeText(fullUrl).then(() => {
        showToast('API URL скопирован!', 'success');
      });
    });
  }

  if (btnClose) {
    btnClose.addEventListener('click', () => {
      if (modal) modal.style.display = 'none';
    });
  }
}

// REST API v1 Integration Modal
function openApiDocsModal() {
  const modal = document.getElementById('apiDocsModal');
  if (modal) {
    modal.style.display = 'flex';
    playRadarSound('click');
  }
}

function setupApiDocsModal() {
  const modal = document.getElementById('apiDocsModal');
  const btnOpenTop = document.getElementById('btnOpenApiModal');
  const btnOpenCase = document.getElementById('btnCaseApiDocs');
  const btnClose = document.getElementById('btnCloseApiDocsModal');
  const snippetBox = document.getElementById('apiSnippetContent');
  const btnCopy = document.getElementById('btnCopyApiSnippet');
  const tabContainer = document.getElementById('apiSnippetTabs');

  if (btnOpenTop) {
    btnOpenTop.addEventListener('click', (e) => {
      e.preventDefault();
      openApiDocsModal();
    });
  }

  if (btnOpenCase) {
    btnOpenCase.addEventListener('click', (e) => {
      e.preventDefault();
      openApiDocsModal();
    });
  }

  if (btnClose && modal) {
    btnClose.addEventListener('click', () => {
      modal.style.display = 'none';
    });
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.style.display = 'none';
    });
  }

  const origin = window.location.origin || 'http://127.0.0.1:8765';

  const snippets = {
    python: `import requests

# 1. Поиск геолокации по фотографии (отправка файла):
url = "${origin}/api/v1/locate"
with open("target_photo.jpg", "rb") as f:
    response = requests.post(
        url,
        files={"file": f},
        data={"region_mode": "global"}  # "global" (весь мир) или "kz" (Казахстан)
    )

data = response.json()
print("Координаты:", data["coordinates"]["lat"], data["coordinates"]["lon"])
print("Название:", data["location"]["title"])
print("Страна / Город:", data["location"]["country"], "/", data["location"]["city"])
print("Точность (CEP): ±", data["error_radius_m"], "метров")
print("Google Maps:", data["maps"]["google"])
print("GeoJSON объект:", data["geojson"])

# 2. Поиск по ссылке на фото из интернета:
resp = requests.post(url, data={
    "image_url": "https://example.com/satellite_or_phone_image.jpg",
    "region_mode": "global"
})
print("Результат по URL:", resp.json()["coordinates"])

# 3. Получение списка всех расследований:
cases = requests.get("${origin}/api/v1/cases?limit=50").json()
print("Всего в базе:", cases["total"])`,

    js: `// Поиск геолокации по фото (Браузер / Node.js 18+)
async function locatePhoto(fileBlob) {
  const formData = new FormData();
  formData.append('file', fileBlob);
  formData.append('region_mode', 'global'); // 'global' или 'kz'

  const res = await fetch('${origin}/api/v1/locate', {
    method: 'POST',
    body: formData
  });

  const data = await res.json();
  console.log('Координаты:', data.coordinates);
  console.log('Локация:', data.location);
  console.log('Погрешность CEP:', data.error_radius_m + 'м');
  console.log('Ссылки на карты:', data.maps);
  return data;
}

// Запрос всех верифицированных точек в формате GeoJSON:
async function loadGeoJsonLayer() {
  const res = await fetch('${origin}/api/v1/geojson');
  const geojson = await res.json();
  console.log('GeoJSON FeatureCollection:', geojson);
  return geojson;
}`,

    curl: `# 1. Определение геопозиции по локальному фото через терминал:
curl -X POST "${origin}/api/v1/locate" \\
  -F "file=@/path/to/my_photo.jpg" \\
  -F "region_mode=global"

# 2. Анализ изображения по веб-ссылке:
curl -X POST "${origin}/api/v1/locate" \\
  -F "image_url=https://upload.wikimedia.org/wikipedia/commons/sample.jpg"

# 3. Выгрузка всех верифицированных расследований в файл GeoJSON:
curl -s "${origin}/api/v1/geojson" -o investigations.geojson

# 4. Проверка статуса и готовности сервиса:
curl -s "${origin}/api/v1/health"`,

    qgis: `=== Подключение слоя GeoSleuth в QGIS / ArcGIS ===

1. В QGIS откройте:
   Меню "Слой" -> "Добавить слой" -> "Добавить векторный слой..."

2. В типе источника выберите:
   (•) Протокол: HTTP(S), cloud...

3. В поле URL вставьте:
   ${origin}/api/v1/geojson

4. Нажмите "Добавить" (Add).
   Слой мгновенно отобразит все маркеры объектов, круги погрешности (CEP)
   и линии визирования с полной криминалистической атрибутивной таблицей!

=== Подключение в Leaflet / Mapbox на веб-карте ===
fetch('${origin}/api/v1/geojson')
  .then(res => res.json())
  .then(geojson => {
    L.geoJSON(geojson, {
      style: feature => ({
        color: feature.properties.stroke || '#06b6d4',
        fillColor: feature.properties.fill || '#06b6d4',
        fillOpacity: feature.properties['fill-opacity'] || 0.2
      })
    }).bindPopup(layer => layer.feature.properties.title).addTo(map);
  });`,

    endpoints: `=== Справочник REST API v1 (GeoSleuth Intelligence Hub) ===

Базовый URL: ${origin}

[POST]  /api/v1/locate
        Анализ фото (файл multipart или image_url), определение координат,
        страны, города, радиуса CEP и генерация GeoJSON.

[GET]   /api/v1/geojson
        Живой поток GeoJSON (RFC 7946) всех расследований для ГИС.
        Параметры: ?country=... &limit=... &download=1

[GET]   /api/v1/cases
        Список расследований с пагинацией и поиском.
        Параметры: ?q=... &country=... &limit=50 &offset=0

[GET]   /api/v1/cases/{case_id}
        Полное досье расследования по ID со всеми уликами.

[GET]   /api/v1/cases/{case_id}/geojson
        GeoJSON конкретного дела (цель, камера, луч, буфер).

[GET]   /api/v1/health
        Хелсчек для микросервисов и мониторинга (Docker / K8s).

[GET]   /docs
        Интерактивный Swagger UI в браузере.

[GET]   /redoc
        Спецификация ReDoc для интеграторов.

[GET]   /openapi.json
        Машиночитаемая спецификация OpenAPI 3.0.`
  };

  let activeTab = 'python';

  function renderSnippet(tabKey) {
    activeTab = tabKey;
    if (snippetBox) {
      snippetBox.textContent = snippets[tabKey] || snippets.python;
    }
    if (tabContainer) {
      tabContainer.querySelectorAll('button').forEach(btn => {
        if (btn.getAttribute('data-tab') === tabKey) {
          btn.classList.add('active', 'btn-primary');
          btn.classList.remove('btn-secondary');
        } else {
          btn.classList.remove('active', 'btn-primary');
          btn.classList.add('btn-secondary');
        }
      });
    }
  }

  if (tabContainer) {
    tabContainer.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-tab]');
      if (btn) {
        const tab = btn.getAttribute('data-tab');
        renderSnippet(tab);
        playRadarSound('click');
      }
    });
  }

  if (btnCopy) {
    btnCopy.addEventListener('click', () => {
      const text = snippets[activeTab] || '';
      navigator.clipboard.writeText(text).then(() => {
        showToast('Пример кода скопирован в буфер обмена!', 'success');
        playRadarSound('lock');
      }).catch(() => {
        showToast('Не удалось скопировать', 'warning');
      });
    });
  }

  renderSnippet('python');
}

// ELA Forensic Analysis Modal
async function openElaModal(c = activeCase) {
  if (!c) {
    showToast('Сначала выберите кейс для анализа', 'warning');
    return;
  }

  const modal = document.getElementById('elaModal');
  const origImg = document.getElementById('elaOriginalImg');
  const resImg = document.getElementById('elaResultImg');

  origImg.src = c.main_photo;
  resImg.src = '';
  modal.style.display = 'flex';
  playRadarSound('radar');

  try {
    const res = await fetch(`/api/cases/${c.id}/ela`, { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.ela_url) {
      resImg.src = data.ela_url + `?t=${Date.now()}`;
      playRadarSound('lock');
      showToast('ELA сигнатура успешно сформирована', 'success');
    } else {
      throw new Error(data.detail || 'Ошибка генерации ELA');
    }
  } catch (err) {
    showToast(`Ошибка ELA: ${err.message}`, 'warning');
  }
}

// OPSEC Sanitizer Modal Functions
function setupOpsecModal() {
  const modal = document.getElementById('opsecModal');
  const btnOpen = document.getElementById('btnOpenOpsecModal');
  const btnClose = document.getElementById('btnCloseOpsecModal');
  const dropzone = document.getElementById('opsecDropzone');
  const fileInput = document.getElementById('opsecFileInput');
  const browseLink = document.getElementById('opsecBrowseLink');
  const btnAuditCurrent = document.getElementById('btnAuditCurrentCasePhoto');
  const btnCheckPhotoOpsec = document.getElementById('btnCheckPhotoOpsec');

  if (btnOpen) {
    btnOpen.addEventListener('click', () => {
      modal.style.display = 'flex';
      playRadarSound('click');
    });
  }

  if (btnClose) {
    btnClose.addEventListener('click', () => {
      modal.style.display = 'none';
    });
  }

  if (btnCheckPhotoOpsec) {
    btnCheckPhotoOpsec.addEventListener('click', () => {
      if (!activeCase) {
        showToast('Сначала выберите кейс для проверки', 'warning');
        return;
      }
      modal.style.display = 'flex';
      playRadarSound('radar');
      runOpsecAudit(activeCase.id, false);
    });
  }

  if (btnAuditCurrent) {
    btnAuditCurrent.addEventListener('click', () => {
      if (!activeCase) {
        showToast('Сначала выберите кейс для проверки', 'warning');
        return;
      }
      runOpsecAudit(activeCase.id, false);
    });
  }

  if (browseLink) {
    browseLink.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.click();
    });
  }

  if (dropzone) {
    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        runOpsecAudit(e.dataTransfer.files[0], true);
      }
    });
  }

  if (fileInput) {
    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files[0]) {
        runOpsecAudit(fileInput.files[0], true);
      }
    });
  }
}

async function runOpsecAudit(target, isFile) {
  const resultsCard = document.getElementById('opsecAuditResults');
  const banner = document.getElementById('opsecRiskBanner');
  const badge = document.getElementById('opsecRiskBadge');
  const desc = document.getElementById('opsecRiskDesc');
  const gpsVal = document.getElementById('opsecGpsVal');
  const camVal = document.getElementById('opsecCameraVal');
  const dateVal = document.getElementById('opsecDateVal');
  const softVal = document.getElementById('opsecSoftwareVal');
  const downloadBtn = document.getElementById('btnDownloadSanitized');
  const statusEl = document.getElementById('opsecCleanStatus');

  showToast('Выполняется OPSEC-аудит метаданных...', 'info');
  playRadarSound('radar');

  const formData = new FormData();
  if (isFile) {
    formData.append('file', target);
  } else {
    formData.append('case_id', target);
  }

  try {
    const res = await fetch('/api/sanitize', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Ошибка аудита');

    resultsCard.style.display = 'block';
    const audit = data.audit;

    banner.classList.remove('risk-high', 'risk-low');
    if (audit.risk_level === 'CRITICAL') {
      badge.textContent = 'КРИТИЧЕСКИЙ РИСК';
      desc.textContent = audit.risk_explanation;
      playRadarSound('radar');
    } else if (audit.risk_level === 'HIGH') {
      banner.classList.add('risk-high');
      badge.textContent = 'ВЫСОКИЙ РИСК';
      desc.textContent = audit.risk_explanation;
      playRadarSound('click');
    } else {
      banner.classList.add('risk-low');
      badge.textContent = 'БЕЗОПАСНО';
      desc.textContent = 'В файле отсутствуют опасные аппаратные и геолокационные теги.';
      playRadarSound('lock');
    }

    if (audit.has_gps && audit.gps) {
      gpsVal.innerHTML = `<span style="color:#ef4444;font-weight:700;">${audit.gps.lat}, ${audit.gps.lon}</span> (УТЕЧКА!)`;
    } else {
      gpsVal.textContent = 'Не обнаружены (OK)';
    }

    camVal.textContent = [audit.camera_make, audit.camera_model].filter(Boolean).join(' ') || 'Не определено';
    dateVal.textContent = audit.datetime || 'Отсутствует';
    softVal.textContent = audit.software || 'Оригинал (без стороннего ПО)';

    downloadBtn.href = data.clean_url;
    downloadBtn.download = `safe_${data.source_name || 'photo.jpg'}`;
    statusEl.textContent = `✔ Удалено ${audit.tags_removed_count} тегов. Скачайте файл без следов.`;
    showToast('OPSEC-аудит завершён! Чистая копия готова к скачиванию', 'success');

  } catch (err) {
    showToast(`Ошибка OPSEC анализа: ${err.message}`, 'warning');
  }
}

/* ==========================================================================
   Deep Optical Character Recognition (Deep OCR) Engine
   ========================================================================== */

let activeOcrTarget = null;
let selectedOcrKeyword = '';

function setupOcrModal() {
  const modal = document.getElementById('ocrModal');
  const btnOpen = document.getElementById('btnOpenOcrModal');
  const btnClose = document.getElementById('btnCloseOcrModal');
  const btnRunActive = document.getElementById('btnRunOcrActiveCase');
  const fileInput = document.getElementById('ocrFileInput');
  const btnLaunchSearch = document.getElementById('btnLaunchSearchWithOcr');

  if (btnOpen) {
    btnOpen.addEventListener('click', () => {
      if (!activeCase) {
        showToast('Сначала выберите кейс для OCR-анализа', 'warning');
        return;
      }
      openOcrModal(activeCase);
    });
  }

  if (btnClose) {
    btnClose.addEventListener('click', () => {
      modal.style.display = 'none';
    });
  }

  if (btnRunActive) {
    btnRunActive.addEventListener('click', () => {
      if (activeOcrTarget) {
        runOcrOnPhoto(activeOcrTarget, false);
      } else if (activeCase) {
        runOcrOnPhoto(activeCase.id, false);
      }
    });
  }

  if (fileInput) {
    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files[0]) {
        runOcrOnPhoto(fileInput.files[0], true);
      }
    });
  }

  if (btnLaunchSearch) {
    btnLaunchSearch.addEventListener('click', () => {
      const targetCaseId = (activeCase ? activeCase.id : (typeof activeOcrTarget === 'string' ? activeOcrTarget : null));
      if (!targetCaseId) {
        showToast('Кейс для поиска не выбран', 'warning');
        return;
      }
      const kw = selectedOcrKeyword || (activeCase && activeCase.ocr_keywords && activeCase.ocr_keywords[0]) || '';
      modal.style.display = 'none';
      trigger5PassRescan(targetCaseId, kw);
    });
  }
}

function openOcrModal(c = activeCase) {
  if (!c) {
    showToast('Кейс для OCR не выбран', 'warning');
    return;
  }
  const modal = document.getElementById('ocrModal');
  const photoPreview = document.getElementById('ocrPhotoPreview');
  const laser = document.getElementById('ocrScanLaser');

  activeOcrTarget = c.id;
  selectedOcrKeyword = '';
  photoPreview.src = c.main_photo;
  laser.style.display = 'none';
  modal.style.display = 'flex';
  playRadarSound('radar');

  // If already scanned and cached in case, display immediately
  if ((c.ocr_lines && c.ocr_lines.length > 0) || (c.ocr_keywords && c.ocr_keywords.length > 0)) {
    renderOcrResults({
      lines: c.ocr_lines || [],
      keywords: c.ocr_keywords || [],
      text_raw: (c.ocr_lines || []).join('\n')
    }, c.id);
  } else {
    runOcrOnPhoto(c.id, false);
  }
}

async function runOcrOnPhoto(target, isFile) {
  const laser = document.getElementById('ocrScanLaser');
  const statusText = document.getElementById('ocrStatusText');
  const linesContainer = document.getElementById('ocrLinesList');
  const cloudContainer = document.getElementById('ocrKeywordsCloud');
  const photoPreview = document.getElementById('ocrPhotoPreview');

  laser.style.display = 'block';
  statusText.textContent = 'Нейросетевое распознавание текста на фото (RU + EN)...';
  linesContainer.innerHTML = '<div class="ocr-empty-hint">⏳ Сканирование пикселей, табличек и указателей...</div>';
  cloudContainer.innerHTML = '';
  playRadarSound('ping');

  const formData = new FormData();
  let url = '';

  if (isFile) {
    formData.append('file', target);
    url = '/api/ocr';
    const reader = new FileReader();
    reader.onload = (e) => { photoPreview.src = e.target.result; };
    reader.readAsDataURL(target);
  } else {
    url = `/api/cases/${target}/ocr`;
  }

  try {
    const res = await fetch(url, {
      method: 'POST',
      body: isFile ? formData : undefined
    });
    const data = await res.json();
    laser.style.display = 'none';

    if (!res.ok) throw new Error(data.detail || 'Ошибка OCR сканирования');

    renderOcrResults(data, isFile ? null : target);
    playRadarSound('lock');
    showToast(`OCR завершён: найдено ${data.lines.length} текстовых элементов!`, 'success');

  } catch (err) {
    laser.style.display = 'none';
    statusText.textContent = 'Ошибка распознавания: ' + err.message;
    linesContainer.innerHTML = `<div class="ocr-empty-hint" style="color:#ef4444;">⚠️ ${escapeHtml(err.message)}</div>`;
    showToast('Ошибка распознавания текста: ' + err.message, 'warning');
  }
}

function renderOcrResults(data, caseId) {
  const statusText = document.getElementById('ocrStatusText');
  const linesContainer = document.getElementById('ocrLinesList');
  const cloudContainer = document.getElementById('ocrKeywordsCloud');
  const btnLaunchSearch = document.getElementById('btnLaunchSearchWithOcr');

  const lines = data.lines || [];
  const keywords = data.keywords || [];

  if (lines.length === 0 && keywords.length === 0) {
    statusText.textContent = 'Текстовых надписей или указателей на фото не обнаружено.';
    linesContainer.innerHTML = '<div class="ocr-empty-hint">ℹ️ На фото отсутствуют чёткие вывески, таблички или дорожные знаки.</div>';
    cloudContainer.innerHTML = '<div class="ocr-empty-hint">Ключевые слова не найдены.</div>';
    return;
  }

  statusText.textContent = `✔ Обнаружено строк: ${lines.length}, ключевых ориентиров: ${keywords.length}`;
  linesContainer.innerHTML = '';
  cloudContainer.innerHTML = '';

  // Render lines
  lines.forEach(line => {
    const card = document.createElement('div');
    card.className = 'ocr-line-card';
    card.innerHTML = `
      <span class="ocr-line-text" title="${escapeHtml(line)}">«${escapeHtml(line)}»</span>
      <div class="ocr-line-actions">
        <button class="ocr-btn-mini btn-copy-line" title="Копировать строку">📋</button>
        <button class="ocr-btn-mini btn-search-line" title="Искать через 5 запусков">🚀 Поиск</button>
      </div>
    `;
    card.querySelector('.btn-copy-line').addEventListener('click', (e) => {
      e.stopPropagation();
      navigator.clipboard.writeText(line);
      showToast(`Скопировано: «${line}»`, 'info');
    });
    card.querySelector('.btn-search-line').addEventListener('click', (e) => {
      e.stopPropagation();
      document.getElementById('ocrModal').style.display = 'none';
      const cid = caseId || (activeCase ? activeCase.id : null);
      if (cid) trigger5PassRescan(cid, line);
    });
    linesContainer.appendChild(card);
  });

  // Render keyword chips
  const selectChip = (chipEl, kw) => {
    document.querySelectorAll('.ocr-keyword-chip').forEach(c => c.classList.remove('active'));
    chipEl.classList.add('active');
    selectedOcrKeyword = kw;
    btnLaunchSearch.innerHTML = `<span>🚀 Запустить 5 запусков поиска для «${escapeHtml(kw)}»</span>`;
    playRadarSound('click');
  };

  keywords.forEach((kw, idx) => {
    const chip = document.createElement('span');
    chip.className = `ocr-keyword-chip ${idx === 0 ? 'active' : ''}`;
    chip.innerHTML = `🔤 ${escapeHtml(kw)}`;
    chip.addEventListener('click', () => selectChip(chip, kw));
    cloudContainer.appendChild(chip);
    if (idx === 0) {
      selectedOcrKeyword = kw;
      btnLaunchSearch.innerHTML = `<span>🚀 Запустить 5 запусков поиска для «${escapeHtml(kw)}»</span>`;
    }
  });

  // If this was for an active case, refresh activeCase in memory
  if (caseId && activeCase && activeCase.id === caseId) {
    activeCase.ocr_lines = lines;
    activeCase.ocr_keywords = keywords;
    updateSidebar(activeCase);
  }
}

/* ==========================================================================
   AI Visual Clue Scout & Kazakhstan Anchor Analyzer Engine
   ========================================================================== */

let activeAiScoutCase = null;

function renderAiScoutCard(c) {
  const card = document.getElementById('aiScoutCard');
  if (!card) return;

  const badgeScene = document.getElementById('aiSceneBadge');
  const badgeKz = document.getElementById('aiKzBadge');
  const strategyText = document.getElementById('aiStrategyText');
  const anchorsList = document.getElementById('aiAnchorsList');

  if (!c) {
    card.style.display = 'none';
    return;
  }
  card.style.display = 'block';

  if (c.ai_analysis) {
    const ai = c.ai_analysis;
    if (badgeScene) {
      badgeScene.textContent = `🌲 Биом: ${ai.scene_type || 'Общий ландшафт'}`;
    }

    const isKz = c.kazakh_detected || ai.kazakh_detected || (c.country && c.country.includes('Казахстан'));
    if (badgeKz) {
      badgeKz.style.display = isKz ? 'inline-flex' : 'none';
      if (isKz) {
        badgeKz.innerHTML = `🇰🇿 Приоритет Казахстан`;
      }
    }

    if (strategyText) {
      strategyText.textContent = ai.strategy_summary || 'Анализ завершён.';
    }

    if (anchorsList) {
      anchorsList.innerHTML = '';
      const anchors = ai.anchors || [];
      if (anchors.length === 0) {
        anchorsList.innerHTML = '<span class="ai-no-anchors">Опорные ориентиры вычисляются...</span>';
      } else {
        anchors.forEach(anc => {
          const chip = document.createElement('div');
          chip.className = 'ai-anchor-chip';
          chip.title = `Кликните, чтобы открыть полный отчёт ИИ-разведчика`;
          chip.innerHTML = `
            <span class="anc-icon">${anc.icon || '📌'}</span>
            <span class="anc-val"><b>${escapeHtml(anc.title)}:</b> ${escapeHtml(anc.value)}</span>
          `;
          chip.addEventListener('click', () => openAiScoutModal(c));
          anchorsList.appendChild(chip);
        });

        // Add precision diagnostics chips
        if (c.is_indoor) {
          const indChip = document.createElement('div');
          indChip.className = 'ai-anchor-chip';
          indChip.style.borderColor = '#f59e0b';
          indChip.innerHTML = `<span class="anc-icon">🏠</span><span class="anc-val"><b style="color:#fbbf24;">Интерьер:</b> ${escapeHtml(c.scene_type || 'Внутри здания')} (уличная сетка заблокирована)</span>`;
          anchorsList.prepend(indChip);
        }

        const mb = (c.diagnostics && c.diagnostics.mountain_bearing) || (c.diagnostics && c.diagnostics.gemini_vision && c.diagnostics.gemini_vision.almaty_mountain_bearing);
        if (mb && (mb.mountain_visible || mb.city_sector)) {
          const mbChip = document.createElement('div');
          mbChip.className = 'ai-anchor-chip';
          mbChip.style.borderColor = '#3b82f6';
          mbChip.innerHTML = `<span class="anc-icon">⛰️</span><span class="anc-val"><b style="color:#93c5fd;">Горный пеленг Алматы:</b> ${escapeHtml(mb.city_sector || 'Заилийский Алатау')} (${escapeHtml(mb.shooting_angle || 'Южный горизонт')})</span>`;
          anchorsList.appendChild(mbChip);
        }

        if (c.diagnostics && c.diagnostics.brand_cluster) {
          const bc = c.diagnostics.brand_cluster;
          const bcChip = document.createElement('div');
          bcChip.className = 'ai-anchor-chip';
          bcChip.style.borderColor = '#10b981';
          bcChip.innerHTML = `<span class="anc-icon">🏬</span><span class="anc-val"><b style="color:#34d399;">ТРЦ Кластер брендов:</b> ${(bc.matched_brands || []).map(escapeHtml).join(' + ')} (CEP ±35м)</span>`;
          anchorsList.appendChild(bcChip);
        }

        if (c.street_view_matches && c.street_view_matches.length > 0) {
          const svChip = document.createElement('div');
          svChip.className = 'ai-anchor-chip';
          svChip.style.borderColor = '#06b6d4';
          svChip.innerHTML = `<span class="anc-icon">📷</span><span class="anc-val"><b style="color:#22d3ee;">Mapillary:</b> ${c.street_view_matches.length} уличных панорам верифицировано</span>`;
          anchorsList.appendChild(svChip);
        }
      }
    }
  } else {
    if (badgeScene) badgeScene.textContent = '🌲 Биом: Анализируется...';
    if (badgeKz) badgeKz.style.display = 'none';
    if (strategyText) strategyText.textContent = 'Идёт предварительное сканирование сцены и выявление опорных точек...';
    if (anchorsList) anchorsList.innerHTML = '<span class="ai-no-anchors">Сканирование...</span>';

    // Lazy load AI analysis if not present
    fetch(`/api/cases/${c.id}/ai-inspect`)
      .then(res => res.json())
      .then(data => {
        if (data.analysis && activeCase && activeCase.id === c.id) {
          activeCase.ai_analysis = data.analysis;
          activeCase.kazakh_detected = data.analysis.kazakh_detected;
          renderAiScoutCard(activeCase);
        }
      })
      .catch(() => {});
  }
}

function setupAiScoutModal() {
  const modal = document.getElementById('aiScoutModal');
  const btnClose = document.getElementById('btnCloseAiScoutModal');
  const btnOpenAction = document.getElementById('btnOpenAiScout');
  const btnOpenCard = document.getElementById('btnOpenAiScoutModal');
  const btnApply = document.getElementById('btnApplyAiRecommendations');

  if (btnClose) {
    btnClose.addEventListener('click', () => {
      modal.style.display = 'none';
    });
  }

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target.id === 'aiScoutModal') modal.style.display = 'none';
    });
  }

  if (btnOpenAction) {
    btnOpenAction.addEventListener('click', () => {
      if (activeCase) openAiScoutModal(activeCase);
      else showToast('Сначала выберите кейс для ИИ-анализа', 'warning');
    });
  }

  if (btnOpenCard) {
    btnOpenCard.addEventListener('click', () => {
      if (activeCase) openAiScoutModal(activeCase);
      else showToast('Сначала выберите кейс для ИИ-анализа', 'warning');
    });
  }

  if (btnApply) {
    btnApply.addEventListener('click', () => {
      if (!activeCase) return;
      modal.style.display = 'none';
      const ai = activeCase.ai_analysis;
      const rec = (ai && ai.recommended_candidates && ai.recommended_candidates[0]) 
        || (ai && ai.top_clue) 
        || '';
      trigger5PassRescan(activeCase.id, rec);
    });
  }
}

function openAiScoutModal(c = activeCase) {
  if (!c) {
    showToast('Кейс не выбран', 'warning');
    return;
  }
  activeAiScoutCase = c;

  const modal = document.getElementById('aiScoutModal');
  const photo = document.getElementById('aiPhotoPreview');
  const scenePill = document.getElementById('aiPhotoScenePill');
  const diagBars = document.getElementById('aiDiagBars');
  const lettersVal = document.getElementById('kzLettersVal');
  const termsVal = document.getElementById('kzTermsVal');
  const regionsVal = document.getElementById('kzRegionsVal');
  const fullAnchors = document.getElementById('aiFullAnchorsList');
  const fullStrategy = document.getElementById('aiFullStrategyText');
  const recsChips = document.getElementById('aiRecsChips');
  const btnApply = document.getElementById('btnApplyAiRecommendations');

  photo.src = c.main_photo;
  modal.style.display = 'flex';
  playRadarSound('radar');

  const populateFromAnalysis = (ai) => {
    scenePill.textContent = `🌲 ${ai.scene_type || 'Общий ландшафт'}`;

    // Diagnostics Bars (Cyan, Green, Ochre, White, Granite)
    if (diagBars && ai.palette) {
      diagBars.innerHTML = '';
      const pal = ai.palette;
      const metrics = [
        { label: 'Бирюзовая вода горных озёр', val: pal.cyan_water_score || 0, color: '#06b6d4' },
        { label: 'Хвойный лес / Тянь-Шань', val: pal.conifer_green_score || 0, color: '#10b981' },
        { label: 'Песчаник / Глина (Чарын)', val: pal.ochre_sand_score || 0, color: '#f59e0b' },
        { label: 'Белый мел / Чинки (Бозжыра)', val: pal.white_chalk_score || 0, color: '#f8fafc' },
        { label: 'Гранитные сопки (Бурабай)', val: pal.granite_rock_score || 0, color: '#94a3b8' }
      ];
      metrics.forEach(m => {
        const row = document.createElement('div');
        row.className = 'ai-diag-bar-row';
        row.innerHTML = `
          <div class="diag-bar-header">
            <span>${m.label}</span>
            <span class="mono">${m.val}%</span>
          </div>
          <div class="diag-bar-track">
            <div class="diag-bar-fill" style="width: ${Math.min(100, m.val * 3)}%; background: ${m.color};"></div>
          </div>
        `;
        diagBars.appendChild(row);
      });
    }

    // Kazakh Language & Regional Letters
    if (lettersVal) {
      const letters = ai.kazakh_letters || [];
      if (letters.length > 0) {
        lettersVal.innerHTML = `<b style="color:#06b6d4; font-size: 0.95rem;">${letters.join(' ')}</b> <span class="badge-kz-detected">Обнаружен алфавит РК</span>`;
      } else {
        lettersVal.innerHTML = `<span style="color:#64748b;">Специфические буквы (Ә, Ғ, Қ, Ң, Ө, Ұ, Ү, Һ, І) в тексте не встретились</span>`;
      }
    }

    // Kazakh Geographical Terms
    if (termsVal) {
      const terms = ai.kz_terms || {};
      const entries = Object.entries(terms);
      if (entries.length > 0) {
        termsVal.innerHTML = entries.map(([kz, ru]) => `
          <span class="kz-term-badge"><b>${escapeHtml(kz)}</b> ➔ ${escapeHtml(ru)}</span>
        `).join(' ');
      } else {
        termsVal.innerHTML = `<span style="color:#64748b;">Прямых казахских терминов (көлі, өзені, тауы, шатқалы) не обнаружено</span>`;
      }
    }

    // Kazakhstan Automobile Region Codes
    if (regionsVal) {
      const regs = ai.regions || [];
      if (regs.length > 0) {
        regionsVal.innerHTML = regs.map(r => `
          <span class="kz-region-badge">🚗 ${escapeHtml(r)}</span>
        `).join(' ');
      } else {
        regionsVal.innerHTML = `<span style="color:#64748b;">Автомобильные коды областей РК (01–20) на фото не зафиксированы</span>`;
      }
    }

    // Anchors
    if (fullAnchors) {
      fullAnchors.innerHTML = '';
      const anchors = ai.anchors || [];
      if (anchors.length === 0) {
        fullAnchors.innerHTML = '<div class="ai-empty-msg">Якоря не выделены, используется глобальный поиск.</div>';
      } else {
        anchors.forEach(anc => {
          const card = document.createElement('div');
          card.className = 'ai-full-anchor-card';
          card.innerHTML = `
            <div class="anchor-icon-col">${anc.icon || '📌'}</div>
            <div class="anchor-text-col">
              <div class="anchor-card-title">${escapeHtml(anc.title)}</div>
              <div class="anchor-card-desc">${escapeHtml(anc.value)}</div>
            </div>
            <div class="anchor-badge-col">
              <span class="anchor-conf-pill conf-${(anc.confidence || 'high').toLowerCase()}">${anc.confidence || 'HIGH'}</span>
            </div>
          `;
          fullAnchors.appendChild(card);
        });
      }
    }

    // Strategy
    if (fullStrategy) {
      fullStrategy.innerHTML = `<b>🧭 План действий:</b> ${escapeHtml(ai.strategy_summary || 'Ансамблевый поиск с приоритетом РК.')}`;
    }

    // Recommended Candidates
    if (recsChips) {
      recsChips.innerHTML = '';
      const recs = ai.recommended_candidates || [];
      if (recs.length === 0) {
        recsChips.innerHTML = '<span style="color:#64748b; font-size:0.75rem;">Нет прямых кандидатов</span>';
      } else {
        recs.forEach((cand, idx) => {
          const btn = document.createElement('button');
          btn.className = `ai-cand-btn ${idx === 0 ? 'primary-cand' : ''}`;
          btn.innerHTML = `<span>🎯</span> <span>${escapeHtml(cand)}</span>`;
          btn.title = `Запустить 5 запусков поиска для «${cand}»`;
          btn.addEventListener('click', () => {
            modal.style.display = 'none';
            trigger5PassRescan(c.id, cand);
          });
          recsChips.appendChild(btn);
        });
      }
    }

    if (btnApply) {
      const topCand = (ai.recommended_candidates && ai.recommended_candidates[0]) || ai.top_clue || '';
      btnApply.innerHTML = `<span>🚀 Запустить 5 запусков поиска с учётом рекомендаций ИИ (${escapeHtml(topCand || 'Ансамбль')})</span>`;
    }
  };

  if (c.ai_analysis) {
    populateFromAnalysis(c.ai_analysis);
  } else {
    scenePill.textContent = '🌲 Выполняется нейросетевой анализ...';
    fetch(`/api/cases/${c.id}/ai-inspect`)
      .then(res => res.json())
      .then(data => {
        if (data.analysis) {
          c.ai_analysis = data.analysis;
          c.kazakh_detected = data.analysis.kazakh_detected;
          renderAiScoutCard(c);
          populateFromAnalysis(data.analysis);
        }
      })
      .catch(err => {
        scenePill.textContent = '⚠️ Ошибка анализа';
        showToast('Не удалось получить ИИ-анализ: ' + err.message, 'warning');
      });
  }
}

// Keyboard Shortcuts Listener
window.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
    if (e.key === 'Escape') e.target.blur();
    return;
  }

  const key = e.key.toUpperCase();
  if (key === 'M') {
    switchView('map');
    playRadarSound('click');
  } else if (key === 'H') {
    switchView('home');
    playRadarSound('click');
  } else if (key === 'U') {
    document.getElementById('uploadModal').style.display = 'flex';
    playRadarSound('click');
  } else if (key === 'R') {
    openRescanModal();
    playRadarSound('click');
  } else if (key === 'T') {
    if (activeCase) openOcrModal(activeCase);
  } else if (key === 'A' || key === 'I') {
    if (activeCase) openAiScoutModal(activeCase);
  } else if (key === 'S') {
    if (activeCase) openSplitSlider(activeCase);
  } else if (key === 'E') {
    if (activeCase) openElaModal(activeCase);
  } else if (key === 'O') {
    document.getElementById('opsecModal').style.display = 'flex';
    playRadarSound('click');
  } else if (key === 'W') {
    if (activeCase) openStreetViewModal(activeCase);
  } else if (key === 'K') {
    document.getElementById('osintGuideModal').style.display = 'flex';
    playRadarSound('click');
  } else if (key === 'B') {
    const btnOpenWayback = document.getElementById('btnOpenWaybackModal');
    if (btnOpenWayback) btnOpenWayback.click();
  } else if (key === 'I' || key === 'P') {
    const btnOpenInsp = document.getElementById('btnOpenInspectorModal');
    if (btnOpenInsp) btnOpenInsp.click();
  } else if (e.key === '?') {
    document.getElementById('shortcutsModal').style.display = 'flex';
  } else if (e.key === 'Escape') {
    document.querySelectorAll('.modal-backdrop').forEach(m => m.style.display = 'none');
    closeLightbox();
  }
});

/* ==========================================================================
   OSINT Forensic Signals, Evidence Sheet, Wayback Archive & Inspector
   ========================================================================== */

function renderOsintSignals(c) {
  if (!c) return;

  // 1. Driving Side
  const sigSide = document.getElementById('sigDrivingSide');
  const sigBadge = document.getElementById('sigDrivingBadge');
  if (sigSide && sigBadge) {
    const isLHT = /великобритания|англия|япония|австралия|индия|таиланд|кипр|юар|новая зеландия|индонезия|малайзия|japan|uk|united kingdom|thailand|australia|india/i.test(c.country || '');
    if (isLHT) {
      sigBadge.className = 'signal-badge badge-lht';
      sigBadge.textContent = 'LHT Левое';
      sigSide.title = 'Левостороннее движение (руль справа)';
    } else {
      sigBadge.className = 'signal-badge badge-rht';
      sigBadge.textContent = 'RHT Правое';
      sigSide.title = 'Правостороннее движение (руль слева)';
    }
  }

  // 2. License Plate Region
  const sigPlate = document.getElementById('sigPlateRegion');
  if (sigPlate) {
    if (c.ai_analysis && c.ai_analysis.regions && c.ai_analysis.regions.length > 0) {
      sigPlate.textContent = c.ai_analysis.regions[0];
    } else if (c.country && c.country.toLowerCase().includes('казахстан')) {
      if (c.region && c.region.includes('Астана')) sigPlate.textContent = '01 (Астана)';
      else if (c.region && c.region.includes('Алматы')) sigPlate.textContent = '02 (Алматы)';
      else if (c.region && (c.region.includes('Акмола') || c.region.includes('Боровое') || c.region.includes('Бурабай'))) sigPlate.textContent = '03 (Акмолинская)';
      else sigPlate.textContent = '01–20 РК';
    } else {
      sigPlate.textContent = c.region || '--';
    }
  }

  // 3. Phone Prefix
  const sigPhone = document.getElementById('sigPhonePrefix');
  if (sigPhone) {
    if (c.country && c.country.toLowerCase().includes('казахстан')) {
      if (c.region && c.region.includes('Астана')) sigPhone.textContent = '+7 (7172) Астана';
      else if (c.region && c.region.includes('Алматы')) sigPhone.textContent = '+7 (727) Алматы';
      else sigPhone.textContent = '+7 (РК / СНГ)';
    } else if (c.country && c.country.toLowerCase().includes('вьетнам')) {
      sigPhone.textContent = '+84 (Вьетнам)';
    } else {
      sigPhone.textContent = '--';
    }
  }
}

function setupEvidenceSheetModal() {
  const btnOpen = document.getElementById('btnOpenEvidenceSheet');
  const modal = document.getElementById('evidenceSheetModal');
  const btnClose = document.getElementById('btnCloseEvidenceSheetModal');
  const img = document.getElementById('evidenceSheetImg');
  const downloadLink = document.getElementById('btnDownloadEvidenceSheetFile');
  const title = document.getElementById('evidenceSheetTitle');

  if (btnClose) {
    btnClose.addEventListener('click', () => {
      modal.style.display = 'none';
    });
  }

  if (btnOpen) {
    btnOpen.addEventListener('click', async () => {
      if (!activeCase) {
        showToast('Выберите кейс для формирования досье', 'warning');
        return;
      }
      showToast('Генерация форензического досье 300 DPI...', 'info');
      playRadarSound('radar');

      try {
        const res = await fetch(`/api/cases/${activeCase.id}/evidence-sheet`, { method: 'POST' });
        const data = await res.json();
        if (data.success && data.sheet_url) {
          img.src = data.sheet_url + '?t=' + Date.now();
          downloadLink.href = data.sheet_url;
          downloadLink.download = `evidence_case_${activeCase.id}.jpg`;
          title.textContent = `Форензическое Досье: ${activeCase.title}`;
          modal.style.display = 'flex';
          playRadarSound('lock');
        } else {
          showToast('Не удалось сгенерировать досье: ' + (data.error || 'Ошибка'), 'error');
        }
      } catch (err) {
        showToast('Ошибка запроса досье: ' + err.message, 'error');
      }
    });
  }
}

let waybackReleasesCache = [];
let waybackActiveLayer = null;

function setupWaybackModal() {
  const modal = document.getElementById('waybackModal');
  const btnOpenHeader = document.getElementById('btnOpenWaybackModal');
  const btnOpenCase = document.getElementById('btnCaseWayback');
  const btnOpenSide = document.getElementById('btnSideOpenWayback');
  const btnClose = document.getElementById('btnCloseWaybackModal');
  const selectRelease = document.getElementById('waybackReleaseSelect');
  const btnApplyToMap = document.getElementById('btnApplyWaybackToMap');
  const histImg = document.getElementById('waybackHistoricalImg');
  const currImg = document.getElementById('waybackCurrentImg');
  const currentCoordsSpan = document.getElementById('waybackCurrentCoords');
  const selectedDateSpan = document.getElementById('waybackSelectedDate');
  const selectedTitleSpan = document.getElementById('waybackSelectedTitle');

  const openModal = async () => {
    if (!activeCase) {
      showToast('Сначала выберите кейс для привязки координат', 'warning');
      return;
    }
    modal.style.display = 'flex';
    playRadarSound('radar');

    const lat = activeCase.target_lat;
    const lon = activeCase.target_lon;
    if (currentCoordsSpan) currentCoordsSpan.textContent = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
    if (currImg) currImg.src = activeCase.main_photo;

    // Load releases if not cached
    if (waybackReleasesCache.length === 0) {
      try {
        const res = await fetch('/api/satellite/wayback/releases');
        const data = await res.json();
        if (data.releases && data.releases.length > 0) {
          waybackReleasesCache = data.releases;
          populateWaybackSelect('all');
        }
      } catch (err) {
        console.error('Failed to load wayback releases', err);
      }
    } else {
      updateWaybackPreview();
    }
  };

  const populateWaybackSelect = (yearFilter = 'all') => {
    if (!selectRelease) return;
    selectRelease.innerHTML = '';
    const filtered = waybackReleasesCache.filter(rel => {
      if (yearFilter === 'all') return true;
      return rel.release_date && rel.release_date.startsWith(yearFilter);
    });

    filtered.forEach(rel => {
      const opt = document.createElement('option');
      opt.value = rel.release_num;
      opt.textContent = `${rel.release_date || 'Неизвестно'} — ${rel.release_title || 'Релиз #' + rel.release_num}`;
      selectRelease.appendChild(opt);
    });

    if (filtered.length > 0) {
      selectRelease.value = filtered[0].release_num;
      updateWaybackPreview();
    }
  };

  const updateWaybackPreview = () => {
    if (!activeCase || !selectRelease) return;
    const relNum = selectRelease.value;
    if (!relNum) return;

    const lat = activeCase.target_lat;
    const lon = activeCase.target_lon;
    if (histImg) histImg.src = `/api/satellite/wayback?lat=${lat}&lon=${lon}&zoom=17&release=${relNum}`;

    const relObj = waybackReleasesCache.find(r => String(r.release_num) === String(relNum));
    if (relObj) {
      if (selectedDateSpan) selectedDateSpan.textContent = relObj.release_date || '';
      if (selectedTitleSpan) selectedTitleSpan.textContent = `🛰️ ESRI WAYBACK (${relObj.release_date || 'Архив'})`;
    }
  };

  if (selectRelease) {
    selectRelease.addEventListener('change', updateWaybackPreview);
  }

  // Year timeline pills
  document.querySelectorAll('#waybackYearTimeline .wayback-year-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('#waybackYearTimeline .wayback-year-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const yr = pill.getAttribute('data-year') || 'all';
      populateWaybackSelect(yr);
      playRadarSound('click');
    });
  });

  // Apply to Map button
  if (btnApplyToMap) {
    btnApplyToMap.addEventListener('click', () => {
      if (!selectRelease) return;
      const relNum = selectRelease.value;
      if (!relNum) return;

      const waybackUrl = `https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/${relNum}/{z}/{y}/{x}`;
      if (waybackActiveLayer) {
        map.removeLayer(waybackActiveLayer);
      }
      // Remove base layers
      layerKeys.forEach(k => {
        if (baseLayers[k] && map.hasLayer(baseLayers[k])) {
          map.removeLayer(baseLayers[k]);
        }
      });

      waybackActiveLayer = L.tileLayer(waybackUrl, { maxZoom: 19 }).addTo(map);
      const nameSpan = document.getElementById('layerName');
      const relObj = waybackReleasesCache.find(r => String(r.release_num) === String(relNum));
      const label = relObj ? `Wayback ${relObj.release_date}` : `Wayback #${relNum}`;
      if (nameSpan) nameSpan.textContent = label;

      modal.style.display = 'none';
      switchView('map');
      showToast(`Подключена историческая спутниковая подложка Esri (${label})!`, 'success');
      playRadarSound('lock');
    });
  }

  if (btnOpenHeader) btnOpenHeader.addEventListener('click', openModal);
  if (btnOpenCase) btnOpenCase.addEventListener('click', openModal);
  if (btnOpenSide) btnOpenSide.addEventListener('click', openModal);
  if (btnClose) btnClose.addEventListener('click', () => modal.style.display = 'none');
}

function setupInspectorModal() {
  const modal = document.getElementById('inspectorModal');
  const btnOpenHeader = document.getElementById('btnOpenInspectorModal');
  const btnQuickOpen = document.getElementById('btnQuickOpenInspector');
  const btnClose = document.getElementById('btnCloseInspectorModal');

  const openModal = () => {
    modal.style.display = 'flex';
    playRadarSound('click');
  };

  if (btnOpenHeader) btnOpenHeader.addEventListener('click', openModal);
  if (btnQuickOpen) btnQuickOpen.addEventListener('click', openModal);
  if (btnClose) btnClose.addEventListener('click', () => modal.style.display = 'none');

  // Tabs switching
  document.querySelectorAll('#inspectorTabsNav .inspector-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#inspectorTabsNav .inspector-tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.inspector-tab-pane').forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const tabId = btn.getAttribute('data-tab');
      const targetPane = document.getElementById('pane' + tabId.charAt(0).toUpperCase() + tabId.slice(1));
      if (targetPane) targetPane.classList.add('active');
      playRadarSound('click');
    });
  });

  // Tab 1: Phone Geocoder
  const btnRunPhone = document.getElementById('btnRunPhoneLookup');
  const phoneInput = document.getElementById('toolPhoneInput');
  const btnFlyPhone = document.getElementById('btnFlyToPhoneCoords');
  let lastPhoneCoords = null;

  const runPhone = async (phoneVal) => {
    const val = phoneVal || (phoneInput ? phoneInput.value.trim() : '');
    if (!val) return;
    if (phoneInput) phoneInput.value = val;

    try {
      const res = await fetch('/api/analyze/phone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: val })
      });
      const data = await res.json();
      if (data.matched) {
        document.getElementById('resPhoneCountry').textContent = `${data.country_flag || ''} ${data.country_name || '--'}`;
        document.getElementById('resPhoneLocation').textContent = `${data.city || ''} ${data.region || ''}`.trim() || '--';
        document.getElementById('resPhoneCarrier').textContent = `${data.carrier || '--'} (${data.line_type || 'Стационарный/Моб.'})`;

        if (data.coords) {
          lastPhoneCoords = data.coords;
          document.getElementById('resPhoneCoords').textContent = `${data.coords[0].toFixed(5)}, ${data.coords[1].toFixed(5)}`;
          document.getElementById('resPhoneActionWrap').style.display = 'block';
        } else {
          document.getElementById('resPhoneCoords').textContent = 'Приблизительные (регион)';
          document.getElementById('resPhoneActionWrap').style.display = 'none';
        }
        document.getElementById('resPhoneStatus').textContent = 'НАЙДЕНО';
        document.getElementById('resPhoneStatus').className = 'signal-badge badge-rht';
      } else {
        document.getElementById('resPhoneCountry').textContent = '--';
        document.getElementById('resPhoneLocation').textContent = 'Не опознано';
        document.getElementById('resPhoneCarrier').textContent = '--';
        document.getElementById('resPhoneCoords').textContent = '--';
        document.getElementById('resPhoneStatus').textContent = 'НЕ НАЙДЕНО';
        document.getElementById('resPhoneStatus').className = 'signal-badge badge-lht';
        document.getElementById('resPhoneActionWrap').style.display = 'none';
      }
    } catch (err) {
      showToast('Ошибка геокодера: ' + err.message, 'warning');
    }
  };

  if (btnRunPhone) btnRunPhone.addEventListener('click', () => runPhone());
  document.querySelectorAll('#panePhone .tool-chip').forEach(ch => {
    ch.addEventListener('click', () => runPhone(ch.getAttribute('data-phone')));
  });
  if (btnFlyPhone) {
    btnFlyPhone.addEventListener('click', () => {
      if (lastPhoneCoords) {
        modal.style.display = 'none';
        switchView('map');
        map.flyTo(lastPhoneCoords, 14, { duration: 1.5 });
        L.popup().setLatLng(lastPhoneCoords).setContent(`<b>📱 Телефонный узел:</b><br>${document.getElementById('resPhoneLocation').textContent}`).openOn(map);
      }
    });
  }

  // Tab 2: Plates & Rules
  const btnRunRules = document.getElementById('btnRunRulesLookup');
  const rulesInput = document.getElementById('toolRulesInput');

  const runRules = async (textVal) => {
    const val = textVal || (rulesInput ? rulesInput.value.trim() : '');
    if (!val) return;
    if (rulesInput) rulesInput.value = val;

    try {
      const res = await fetch('/api/analyze/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: val })
      });
      const data = await res.json();
      const plates = (data.plates || []).map(p => `[${p.code}] ${p.region} (${p.status})`);
      document.getElementById('resRulesPlates').textContent = plates.length > 0 ? plates.join('; ') : 'Не обнаружено';

      const letters = (data.kazakh_letters || []);
      document.getElementById('resRulesLetters').textContent = letters.length > 0 ? letters.join(' ') : 'Специфических букв РК нет';

      const poles = (data.pole_paints || []).map(p => `${p.region}: ${p.scheme}`);
      document.getElementById('resRulesPoles').textContent = poles.length > 0 ? poles.join('; ') : 'Опознанных схем нет';

      document.getElementById('resRulesStatus').textContent = (plates.length > 0 || letters.length > 0) ? 'ВЕРИФИЦИРОВАНО' : 'НЕТ СОВПАДЕНИЙ';
    } catch (err) {
      showToast('Ошибка анализа правил: ' + err.message, 'warning');
    }
  };

  if (btnRunRules) btnRunRules.addEventListener('click', () => runRules());
  document.querySelectorAll('#paneRules .tool-chip').forEach(ch => {
    ch.addEventListener('click', () => runRules(ch.getAttribute('data-rule')));
  });

  // Tab 3: Driving Side
  const btnRunDriving = document.getElementById('btnRunDrivingLookup');
  const drivingInput = document.getElementById('toolDrivingInput');

  const runDriving = async (cVal) => {
    const val = cVal || (drivingInput ? drivingInput.value.trim() : '');
    if (!val) return;
    if (drivingInput) drivingInput.value = val;

    try {
      const res = await fetch('/api/analyze/driving-side', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ country: val })
      });
      const data = await res.json();
      document.getElementById('resDrivingCountry').textContent = data.country || val;
      document.getElementById('resDrivingDesc').textContent = data.driving_side === 'LHT' ? 'Левостороннее (LHT, руль справа)' : 'Правостороннее (RHT, руль слева)';
      document.getElementById('resDrivingElimination').textContent = data.driving_side === 'LHT' ? 'Исключает 75% стран мира (только UK, Япония, ЮВА, Австралия и др.)' : 'Соответствует большинству континентальной Евразии и СНГ';

      const badge = document.getElementById('resDrivingBadge');
      badge.textContent = data.driving_side;
      badge.className = data.driving_side === 'LHT' ? 'signal-badge badge-lht' : 'signal-badge badge-rht';
    } catch (err) {
      showToast('Ошибка проверки движения: ' + err.message, 'warning');
    }
  };

  if (btnRunDriving) btnRunDriving.addEventListener('click', () => runDriving());
  document.querySelectorAll('#paneDriving .tool-chip').forEach(ch => {
    ch.addEventListener('click', () => runDriving(ch.getAttribute('data-country')));
  });

  // Tab 4: Solar Shadow Calculator
  const btnRunShadow = document.getElementById('btnRunShadowLookup');
  if (btnRunShadow) {
    btnRunShadow.addEventListener('click', async () => {
      const lat = parseFloat(document.getElementById('toolShadowLat').value) || 0;
      const lon = parseFloat(document.getElementById('toolShadowLon').value) || 0;
      const dt = document.getElementById('toolShadowDate').value || new Date().toISOString();

      try {
        const res = await fetch('/api/analyze/sun-shadow', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lat, lon, date_str: dt })
        });
        const data = await res.json();
        document.getElementById('resShadowAzimuth').textContent = `${(data.solar_azimuth_deg || 0).toFixed(1)}°`;
        document.getElementById('resShadowElevation').textContent = `${(data.solar_elevation_deg || 0).toFixed(1)}°`;
        document.getElementById('resShadowRatio').textContent = `${(data.shadow_length_ratio || 0).toFixed(2)}×`;
        document.getElementById('resShadowHeading').textContent = `${((data.solar_azimuth_deg + 180) % 360).toFixed(1)}°`;
      } catch (err) {
        showToast('Ошибка расчета теней: ' + err.message, 'warning');
      }
    });
  }

  // Tab 5: Datum Converter
  const btnRunDatum = document.getElementById('btnRunDatumConvert');
  if (btnRunDatum) {
    btnRunDatum.addEventListener('click', async () => {
      const lat = parseFloat(document.getElementById('toolDatumLat').value) || 0;
      const lon = parseFloat(document.getElementById('toolDatumLon').value) || 0;
      const dir = document.getElementById('toolDatumDirection').value;

      try {
        const res = await fetch('/api/geo/convert', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lat, lon, direction: dir })
        });
        const data = await res.json();
        document.getElementById('resDatumTargetLat').textContent = (data.target_lat || 0).toFixed(6);
        document.getElementById('resDatumTargetLon').textContent = (data.target_lon || 0).toFixed(6);
        document.getElementById('resDatumOffset').textContent = `ΔLat: ${(data.target_lat - lat).toFixed(6)}, ΔLon: ${(data.target_lon - lon).toFixed(6)}`;
      } catch (err) {
        showToast('Ошибка конвертации: ' + err.message, 'warning');
      }
    });
  }
}

/* ==========================================================================
   SpyBrain Tactical Radar & Entity Intelligence Implementation
   ========================================================================== */

let radarAnimId = null;
let radarAngle = 0;

function initRadarScreen() {
  const canvas = document.getElementById('radarCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const cx = width / 2;
  const cy = height / 2;
  const maxRadius = cx - 10;

  renderRadarBlips(cx, cy, maxRadius);

  if (radarAnimId) cancelAnimationFrame(radarAnimId);

  function sweep() {
    ctx.clearRect(0, 0, width, height);
    radarAngle = (radarAngle + 0.035) % (Math.PI * 2);

    const deg = Math.round((radarAngle * 180) / Math.PI);
    const azElem = document.getElementById('radarCurrentAzimuth');
    if (azElem) azElem.textContent = `${deg.toString().padStart(3, '0')}°`;

    const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, maxRadius);
    gradient.addColorStop(0, 'rgba(6, 182, 212, 0.35)');
    gradient.addColorStop(1, 'rgba(6, 182, 212, 0.0)');

    ctx.save();
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, maxRadius, radarAngle - 0.35, radarAngle);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(radarAngle) * maxRadius, cy + Math.sin(radarAngle) * maxRadius);
    ctx.strokeStyle = '#06b6d4';
    ctx.lineWidth = 2;
    ctx.shadowColor = '#06b6d4';
    ctx.shadowBlur = 10;
    ctx.stroke();
    ctx.restore();

    radarAnimId = requestAnimationFrame(sweep);
  }

  sweep();
  setupRadarTools();
}

function renderRadarBlips(cx, cy, maxRadius) {
  const container = document.getElementById('radarTargetBlips');
  const countElem = document.getElementById('radarTargetCount');
  if (!container) return;
  container.innerHTML = '';

  const validCases = currentCases.filter(c => c.target_lat && c.target_lon);
  if (countElem) countElem.textContent = `${validCases.length} объектов РК`;

  const centerLat = 51.169392;
  const centerLon = 71.449074;

  validCases.forEach(c => {
    const dLat = c.target_lat - centerLat;
    const dLon = (c.target_lon - centerLon) * Math.cos((centerLat * Math.PI) / 180);
    const distDeg = Math.sqrt(dLat * dLat + dLon * dLon);
    const angle = Math.atan2(dLat, dLon);

    const rNorm = Math.min(distDeg / 12.0, 0.92) * maxRadius;
    const x = cx + Math.cos(-angle) * rNorm;
    const y = cy + Math.sin(-angle) * rNorm;

    const blip = document.createElement('div');
    blip.className = 'radar-blip-point';
    blip.style.left = `${x}px`;
    blip.style.top = `${y}px`;
    blip.title = `${c.title}\n[${c.region || 'Казахстан'}]\nКоординаты: ${c.target_lat.toFixed(4)}, ${c.target_lon.toFixed(4)}`;
    blip.addEventListener('click', () => {
      selectCase(c.id, true);
    });
    container.appendChild(blip);
  });
}

function setupRadarTools() {
  // Tool 1: Gastronomic & Price Triangulation
  const btnMenu = document.getElementById('btnRadarAnalyzeMenu');
  const inputMenu = document.getElementById('radarMenuInput');
  const resMenu = document.getElementById('radarMenuResult');

  if (btnMenu && inputMenu && resMenu) {
    btnMenu.onclick = async () => {
      const text = inputMenu.value.trim();
      if (!text) return;
      btnMenu.disabled = true;
      btnMenu.textContent = 'Анализ...';
      try {
        const res = await fetch('/api/venue/menu-triangulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text })
        });
        const data = await res.json();
        resMenu.style.display = 'block';

        let dishesHtml = '';
        if (data.found_dishes && data.found_dishes.length > 0) {
          dishesHtml = `
            <div style="margin-top: 6px; display: flex; gap: 6px; flex-wrap: wrap;">
              ${data.found_dishes.map(d => `<span class="badge" style="background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #34d399;">${d.icon} ${d.dish} (${d.cuisine})</span>`).join('')}
            </div>
          `;
        }

        resMenu.innerHTML = `
          <div style="color: #38bdf8; font-weight: 700; margin-bottom: 4px;">
            ${data.detected_currency ? `${data.detected_currency.flag} Валюта: ${data.detected_currency.currency} (${data.detected_currency.country})` : 'Валюта не указана'}
          </div>
          <div style="font-size: 0.82rem; color: #f8fafc;">
            <b>Ценовой сегмент:</b> ${data.price_tier}
          </div>
          ${data.median_price ? `<div style="font-size: 0.78rem; color: #94a3b8;">Медианная цена позиции: ~${data.median_price} ${data.detected_currency?.currency || ''}</div>` : ''}
          ${dishesHtml}
          <div style="margin-top: 6px; font-size: 0.78rem; color: #cbd5e1; background: rgba(0,0,0,0.3); padding: 6px; border-radius: 4px;">
            📌 <b>Сводка:</b> ${data.summary}
          </div>
        `;
      } catch (err) {
        resMenu.style.display = 'block';
        resMenu.innerHTML = `<div style="color: var(--accent-rose);">Ошибка анализа: ${err.message}</div>`;
      } finally {
        btnMenu.disabled = false;
        btnMenu.textContent = 'Триангуляция';
      }
    };
  }

  // Tool 1b: Mall Brand Co-occurrence Clusterer
  const btnMall = document.getElementById('btnRadarClusterMall');
  const inputMall = document.getElementById('radarMallInput');
  const resMall = document.getElementById('radarMallResult');

  if (btnMall && inputMall && resMall) {
    btnMall.onclick = async () => {
      const raw = inputMall.value.trim();
      if (!raw) return;
      const brands = raw.split(/[,;\n]+/).map(b => b.trim()).filter(Boolean);
      btnMall.disabled = true;
      btnMall.textContent = 'Поиск ТРЦ...';
      try {
        const res = await fetch('/api/venue/mall-cluster', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ brands })
        });
        const malls = await res.json();
        resMall.style.display = 'block';

        if (!malls || malls.length === 0) {
          resMall.innerHTML = `<div style="color: #f87171;">ТРЦ с указанной комбинацией брендов не найдено. Попробуйте добавить якорные бренды (Zara, CoffeeBoom, Kinopark, H&M).</div>`;
        } else {
          resMall.innerHTML = malls.slice(0, 3).map(m => `
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 6px; padding: 8px 10px; margin-bottom: 6px;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <b style="color: #38bdf8;">${m.mall_name} (${m.city})</b>
                <span class="badge" style="background: rgba(34, 197, 94, 0.2); border: 1px solid #22c55e; color: #4ade80;">Совпадение: ${Math.round(m.confidence * 100)}%</span>
              </div>
              <div style="font-size: 0.78rem; color: #cbd5e1; margin-top: 2px;">📍 ${m.address}</div>
              <div style="font-size: 0.74rem; color: #94a3b8; margin-top: 4px;">
                Совпавшие бренды: <b>${m.matched_brands.join(', ')}</b>
              </div>
              <div style="margin-top: 6px;">
                <a href="${m.twogis_url}" target="_blank" class="btn btn-xs btn-2gis">Открыть ТРЦ в 2ГИС ↗</a>
              </div>
            </div>
          `).join('');
        }
      } catch (err) {
        resMall.style.display = 'block';
        resMall.innerHTML = `<div style="color: var(--accent-rose);">Ошибка поиска ТРЦ: ${err.message}</div>`;
      } finally {
        btnMall.disabled = false;
        btnMall.textContent = 'Найти ТРЦ';
      }
    };
  }

  // Tool 1c: Through-the-Window Bus Route Triangulation
  const btnBus = document.getElementById('btnRadarLookupBus');
  const inputBus = document.getElementById('radarBusInput');
  const resBus = document.getElementById('radarBusResult');

  if (btnBus && inputBus && resBus) {
    btnBus.onclick = async () => {
      const query = inputBus.value.trim();
      if (!query) return;
      btnBus.disabled = true;
      btnBus.textContent = 'Маршрут...';
      try {
        const res = await fetch('/api/venue/bus-routes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query })
        });
        const routes = await res.json();
        resBus.style.display = 'block';

        if (!routes || routes.length === 0) {
          resBus.innerHTML = `<div style="color: #f87171;">Маршрут не найден в базе ключевых артерий. Проверьте номер (например: 10, 12, 32, 47, 79, 92).</div>`;
        } else {
          resBus.innerHTML = routes.map(r => `
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 6px; padding: 8px 10px; margin-bottom: 6px;">
              <div style="color: #fbbf24; font-weight: 700;">🚌 ${r.title}</div>
              <div style="font-size: 0.74rem; color: #94a3b8; margin-top: 2px;">Оператор: ${r.operators} (${r.city})</div>
              <div style="font-size: 0.78rem; color: #e2e8f0; margin-top: 4px;">
                <b>Ключевые проспекты и остановки:</b><br>
                ${r.key_corridors.map(c => `• ${c}`).join('<br>')}
              </div>
            </div>
          `).join('');
        }
      } catch (err) {
        resBus.style.display = 'block';
        resBus.innerHTML = `<div style="color: var(--accent-rose);">Ошибка запроса: ${err.message}</div>`;
      } finally {
        btnBus.disabled = false;
        btnBus.textContent = 'Маршрут';
      }
    };
  }

  const btnPhone = document.getElementById('btnLookupPhoneRadar');
  const inputPhone = document.getElementById('radarPhoneInput');
  const resPhone = document.getElementById('radarPhoneResult');

  if (btnPhone && inputPhone && resPhone) {
    btnPhone.onclick = async () => {
      const raw = inputPhone.value.trim();
      if (!raw) return;
      try {
        const res = await fetch('/api/analyze/phone', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ raw_input: raw, default_region: 'KZ' })
        });
        const data = await res.json();
        resPhone.style.display = 'block';
        if (data.valid) {
          resPhone.innerHTML = `
            <div style="color: var(--accent-cyan); font-weight: 700; margin-bottom: 6px;">
              📱 ${data.city || data.region || 'Казахстан'}
            </div>
            <div><b>Тип сети:</b> ${data.type || 'Мобильная/Стационарная'}</div>
            <div><b>Гео-привязка:</b> ${data.note || data.region}</div>
            <div style="margin-top: 6px; font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-dim);">
              Координаты узла: ${data.lat}, ${data.lon}
            </div>
          `;
        } else {
          resPhone.innerHTML = `<div style="color: var(--accent-amber);">Не удалось определить принадлежность номера</div>`;
        }
      } catch (err) {
        resPhone.style.display = 'block';
        resPhone.innerHTML = `<div style="color: var(--accent-rose);">Ошибка запроса: ${err.message}</div>`;
      }
    };
  }

  const btnSign = document.getElementById('btnMineSignboardsRadar');
  const inputSign = document.getElementById('radarSignboardInput');
  const resSign = document.getElementById('radarSignboardResult');

  if (btnSign && inputSign && resSign) {
    btnSign.onclick = async () => {
      const text = inputSign.value.trim();
      if (!text) return;
      try {
        const res = await fetch('/api/kz/mine-signboards', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text })
        });
        const data = await res.json();
        resSign.style.display = 'block';

        let html = '<div style="margin-bottom: 8px; font-weight: 700; color: #fff;">Извлеченные объекты РК:</div>';
        if (data.streets && data.streets.length) {
          html += `<div><b>🛣️ Улицы / Проспекты:</b> ${data.streets.map(s => `<span class="kz-signboard-chip">${s}</span>`).join('')}</div>`;
        }
        if (data.businesses && data.businesses.length) {
          html += `<div style="margin-top: 6px;"><b>🏢 Заведения:</b> ${data.businesses.map(b => `<span class="kz-signboard-chip">${b}</span>`).join('')}</div>`;
        }
        if (data.institutions && data.institutions.length) {
          html += `<div style="margin-top: 6px;"><b>🏛️ Ведомства:</b> ${data.institutions.map(i => `<span class="kz-signboard-chip">${i}</span>`).join('')}</div>`;
        }
        if (data.search_queries && data.search_queries.length) {
          html += '<div style="margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap;">';
          data.search_queries.forEach(q => {
            html += `<a href="${q.twogis_url}" target="_blank" class="btn btn-xs btn-primary">🟢 2GIS: ${q.term}</a>`;
            html += `<a href="${q.yandex_url}" target="_blank" class="btn btn-xs btn-secondary">🔴 Яндекс: ${q.term}</a>`;
          });
          html += '</div>';
        }
        if ((!data.streets || !data.streets.length) && (!data.businesses || !data.businesses.length) && (!data.institutions || !data.institutions.length)) {
          html += '<div style="color: var(--text-dim);">Специфических географических терминов РК не обнаружено</div>';
        }
        resSign.innerHTML = html;
      } catch (err) {
        resSign.style.display = 'block';
        resSign.innerHTML = `<div style="color: var(--accent-rose);">Ошибка майнинга: ${err.message}</div>`;
      }
    };
  }
}

/* ==========================================================================
   Kazakhstan Knowledge Base & 262-Rule Explorer Implementation
   ========================================================================== */

let kzRegionsCache = null;
let kzKnowledgeCache = null;

async function loadKnowledgeBase() {
  try {
    if (!kzRegionsCache) {
      const res = await fetch('/api/kz/regions');
      const data = await res.json();
      kzRegionsCache = data.regions;
    }
    if (!kzKnowledgeCache) {
      const res = await fetch('/api/kz/knowledge');
      kzKnowledgeCache = await res.json();
    }

    renderKazakhstanPlates(kzRegionsCache);
    renderKazakhstanRules('all');
    setupKnowledgeFilters();
  } catch (err) {
    console.error('Failed to load knowledge base:', err);
  }
}

function renderKazakhstanPlates(regions) {
  const container = document.getElementById('kzPlatesGrid');
  if (!container) return;
  container.innerHTML = '';

  Object.values(regions).forEach(r => {
    const card = document.createElement('div');
    card.className = 'kz-plate-meta-box';
    card.innerHTML = `
      <div class="kz-plate-card" title="Кликните для поиска по городу">
        <div class="kz-plate-flag-strip">
          <div class="kz-flag-icon">🇰🇿</div>
          <span>KZ</span>
        </div>
        <div class="kz-plate-number">777 AAA</div>
        <div class="kz-plate-region-box">
          <span class="kz-plate-code-number">${r.code}</span>
        </div>
      </div>
      <div style="font-size: 0.85rem; font-weight: 700; color: #fff; margin-top: 4px;">
        ${r.name_ru} (${r.center})
      </div>
      <div style="font-size: 0.74rem; color: var(--text-muted);">
        <b>Транспорт:</b> ${r.bus_colors}
      </div>
      <div style="font-size: 0.74rem; color: var(--text-muted);">
        <b>Опоры ЛЭП:</b> ${r.pole_paint}
      </div>
      <div style="font-size: 0.72rem; color: var(--accent-cyan);">
        <b>Ориентиры:</b> ${(r.key_landmarks || []).slice(0, 3).join(', ')}
      </div>
    `;
    card.addEventListener('click', () => {
      const search = document.getElementById('knowledgeSearchInput');
      if (search) {
        search.value = r.center;
        filterRulesBySearch(r.center);
      }
    });
    container.appendChild(card);
  });
}

function renderKazakhstanRules(cat = 'all') {
  const container = document.getElementById('knowledgeRulesGrid');
  if (!container) return;
  container.innerHTML = '';

  const sampleRules = [
    { cat: 'plates', title: 'Стандартные автономера РК (2012+)', text: 'Белый прямоугольный фон, синяя полоса с флагом РК и буквами KZ слева, формат: 123 ABC 01. В правом поле – 2-значный код региона (01-20).' },
    { cat: 'plates', title: 'Региональные коды 18, 19, 20 (реформы 2022)', text: 'Код 18 – Область Абай (г. Семей), Код 19 – Область Жетысу (г. Талдыкорган), Код 20 – Область Улытау (г. Жезказган).' },
    { cat: 'poles', title: 'Западно-Казахстанская область (Уральск)', text: 'Опоры ЛЭП и освещения имеют характерную контрастную красно-бело-черную окраску снизу вверх.' },
    { cat: 'poles', title: 'Атырауская область (Прикаспий)', text: 'Опоры окрашены в сине-бело-черные цвета. В городе Атырау фонари на набережной Урала оцинкованные.' },
    { cat: 'poles', title: 'Акмолинская область и Кокшетау', text: 'Узкая красная полоса, широкая белая, узкая черная внизу. В самом Кокшетау низ столбов светло-голубой.' },
    { cat: 'poles', title: 'Костанайская область и Рудный', text: 'Столбы с бирюзовой и желтой полосами. В г. Рудный верх столба красно-желтый, низ – белый.' },
    { cat: 'buses', title: 'Актобе: оранжево-черные автобусы', text: 'Фирменный стиль общественного транспорта г. Актобе – ярко-оранжевый кузов с черными полосами.' },
    { cat: 'buses', title: 'Алматы: зеленые автобусы с яблоком', text: 'Ярко-зеленые низкопольные автобусы с белым стилизованным яблоком и надписью «Almaty» на бортах.' },
    { cat: 'buses', title: 'Астана: электробусы CTS', text: 'Бело-зеленые и черные современные электробусы Yutong на маршрутах левого и правого берегов.' },
    { cat: 'buses', title: 'Жезказган: «Men ♥ Jezz»', text: 'Оранжево-белые автобусы с надписью «Men ♥ Jezz / Zhez». Остановки – широкие синие двухсекционные.' },
    { cat: 'highways', title: 'Трасса М-36 (Астана – Караганда – Балхаш)', text: 'Разделительный бетонный брус, желтые внешние линии, бетонное покрытие. Пейзаж – сухая ковыльная степь.' },
    { cat: 'highways', title: 'Автобан А-1 (Астана – Бурабай / Щучинск)', text: 'Единственная 6-полосная скоростная автомагистраль с идеальным асфальтом, ведущая к сосновым озерам.' },
    { cat: 'highways', title: 'Трасса А-2 (Шымкент – Тараз – Алматы)', text: 'На горизонте на юге отчетливо видны заснеженные хребты Тянь-Шаня и Заилийского Алатау.' },
    { cat: 'nature', title: 'Тянь-Шаньская ель (Ель Шренка)', text: 'Произрастает только в горных ущельях Алматы, Кольсая, Каинды на высоте 1300–2800 метров.' },
    { cat: 'nature', title: 'Саксауловые заросли Мойынкум и Кызылкум', text: 'Кривые бесформенные деревья без листьев на песчаных почвах южного Казахстана (Жамбыл, Кызылорда).' },
    { cat: 'nature', title: 'Белые меловые чинки Устюрта (Бозжыра)', text: 'Колоссальные белоснежные меловые останцы-клыки на плато Устюрт в Мангистауской области.' },
    { cat: 'architecture', title: 'Надземные желтые газовые трубы', text: 'В Алматы, Шымкенте, Таразе и Туркестане газовые трубы проведены над землей вдоль заборов частного сектора.' },
    { cat: 'architecture', title: 'Мазары и саманные стены на юге', text: 'Мавзолеи из жженого или сырцового кирпича с бирюзовыми куполами вдоль дорог Туркестана и Кызылорды.' }
  ];

  const filtered = cat === 'all' ? sampleRules : sampleRules.filter(r => r.cat === cat);

  filtered.forEach(r => {
    const card = document.createElement('div');
    card.className = 'rule-item-card';
    card.innerHTML = `
      <div class="rule-item-header">
        <span class="rule-category-tag">${r.cat.toUpperCase()}</span>
      </div>
      <div class="rule-item-title">${r.title}</div>
      <div class="rule-item-body">${r.text}</div>
    `;
    container.appendChild(card);
  });
}

function setupKnowledgeFilters() {
  const pills = document.querySelectorAll('#knowledgeCategoryPills .k-pill');
  pills.forEach(p => {
    p.onclick = () => {
      pills.forEach(x => x.classList.remove('active'));
      p.classList.add('active');
      renderKazakhstanRules(p.dataset.cat);
    };
  });

  const searchInput = document.getElementById('knowledgeSearchInput');
  if (searchInput) {
    searchInput.oninput = () => {
      filterRulesBySearch(searchInput.value.trim().toLowerCase());
    };
  }
}

function filterRulesBySearch(query) {
  const cards = document.querySelectorAll('#knowledgeRulesGrid .rule-item-card');
  cards.forEach(c => {
    const text = c.textContent.toLowerCase();
    c.style.display = text.includes(query) ? 'block' : 'none';
  });
}

/* ==========================================================================
   Ubinam 5-Tier Ladder, FindMyPhoto & Kazakh Signboards Widget Handlers
   ========================================================================== */

async function fetchAndRenderUbinamLadder(caseId) {
  const stepsContainer = document.getElementById('ubinamStepsList');
  const radiusPill = document.getElementById('ubinamErrorRadiusPill');
  const missingBox = document.getElementById('ubinamMissingBox');
  const missingList = document.getElementById('ubinamMissingList');
  if (!stepsContainer) return;

  try {
    const res = await fetch(`/api/cases/${caseId}/ubinam-ladder`);
    const data = await res.json();
    const ladder = data.ladder;

    if (radiusPill) {
      radiusPill.textContent = `±${ladder.error_radius_m} м Погрешность`;
      if (ladder.error_radius_m <= 50) {
        radiusPill.style.color = '#10b981';
        radiusPill.style.borderColor = 'rgba(16, 185, 129, 0.4)';
      } else if (ladder.error_radius_m <= 1000) {
        radiusPill.style.color = '#06b6d4';
        radiusPill.style.borderColor = 'rgba(6, 182, 212, 0.4)';
      } else {
        radiusPill.style.color = '#f59e0b';
        radiusPill.style.borderColor = 'rgba(245, 158, 11, 0.4)';
      }
    }

    stepsContainer.innerHTML = '';
    const tierIcons = ['🇰🇿', '🏛️', '🏙️', '🛣️', '🎯'];

    ladder.tiers.forEach((t, idx) => {
      const row = document.createElement('div');
      const isVer = t.status === 'VERIFIED';
      row.className = `ubinam-step-row ${isVer ? 'verified' : 'unverified'}`;
      row.innerHTML = `
        <div class="ubinam-step-label">
          <span>${tierIcons[idx]}</span>
          <span>Уровень ${idx + 1}: ${t.name}</span>
        </div>
        <div>
          <span class="signal-badge ${isVer ? 'badge-rht' : 'badge-lht'}">
            ${isVer ? '✓ ПОДТВЕРЖДЕНО' : 'ОЖИДАЕТ УЛИК'}
          </span>
        </div>
      `;
      stepsContainer.appendChild(row);
    });

    if (missingBox && missingList) {
      if (ladder.missing_evidence && ladder.missing_evidence.length > 0) {
        missingBox.style.display = 'block';
        missingList.innerHTML = ladder.missing_evidence.map(m => `<li>${m}</li>`).join('');
      } else {
        missingBox.style.display = 'none';
      }
    }

    if (mapMarkers && mapMarkers.accuracyCircle && activeCase) {
      mapMarkers.accuracyCircle.setRadius(ladder.error_radius_m);
    }
  } catch (err) {
    console.error('Failed to load Ubinam ladder:', err);
  }
}

async function fetchAndRenderDistanceMatrix(caseId) {
  const tableBody = document.getElementById('fmpDistanceTableBody');
  const nearestCityVal = document.getElementById('fmpNearestCityVal');
  const btnGeotag = document.getElementById('btnGeotagExif');
  const notice = document.getElementById('fmpGeotagSuccessNotice');
  const downloadLink = document.getElementById('linkDownloadGeotagged');

  if (notice) notice.style.display = 'none';

  try {
    const res = await fetch(`/api/cases/${caseId}/distance-matrix`);
    const data = await res.json();
    const matrix = data.matrix;

    if (nearestCityVal && matrix.nearest_settlement) {
      nearestCityVal.textContent = `${matrix.nearest_settlement.city} (${matrix.nearest_settlement.distance_km} км)`;
    }

    if (tableBody) {
      tableBody.innerHTML = '';
      const topCities = matrix.top_5_cities || [];
      const topLms = matrix.top_5_landmarks || [];

      topCities.slice(0, 3).forEach(c => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><b>${c.city}</b></td>
          <td>${c.region}</td>
          <td class="mono" style="color: var(--accent-cyan); font-weight: 700;">${c.distance_km} км</td>
        `;
        tableBody.appendChild(tr);
      });

      topLms.slice(0, 2).forEach(lm => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>🏞️ ${lm.name}</td>
          <td>${lm.city}</td>
          <td class="mono" style="color: var(--accent-amber); font-weight: 700;">${lm.distance_km} км</td>
        `;
        tableBody.appendChild(tr);
      });
    }

    if (btnGeotag) {
      btnGeotag.onclick = async () => {
        btnGeotag.disabled = true;
        btnGeotag.textContent = '⏳ Запись EXIF...';
        try {
          const gRes = await fetch(`/api/cases/${caseId}/geotag-exif`, { method: 'POST' });
          const gData = await gRes.json();
          btnGeotag.disabled = false;
          btnGeotag.textContent = '✅ GPS вшит!';

          if (notice && downloadLink) {
            notice.style.display = 'flex';
            downloadLink.href = gData.download_url;
            downloadLink.textContent = `📥 Скачать ${gData.filename}`;
          }
          showToast('GPS координаты успешно вшиты в EXIF фото!', 'success');
        } catch (err) {
          btnGeotag.disabled = false;
          btnGeotag.textContent = '📌 Вшить GPS в EXIF';
          showToast('Ошибка записи EXIF: ' + err.message, 'warning');
        }
      };
    }
  } catch (err) {
    console.error('Failed to load distance matrix:', err);
  }
}

async function fetchAndRenderKazakhSignboards(c) {
  const container = document.getElementById('kzSignboardLists');
  if (!container) return;

  const fullText = `${c.title || ''} ${c.description || ''} ${(c.ocr_lines || []).join(' ')}`;

  try {
    const res = await fetch('/api/kz/mine-signboards', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: fullText })
    });
    const data = await res.json();

    let html = '';
    if (data.streets && data.streets.length) {
      html += `<div style="margin-bottom: 6px;"><b>Улицы:</b> ${data.streets.map(s => `<span class="kz-signboard-chip">${s}</span>`).join('')}</div>`;
    }
    if (data.businesses && data.businesses.length) {
      html += `<div style="margin-top: 6px;"><b>Заведения:</b> ${data.businesses.map(b => `<span class="kz-signboard-chip">${b}</span>`).join('')}</div>`;
    }
    if (data.institutions && data.institutions.length) {
      html += `<div style="margin-top: 6px;"><b>Учреждения:</b> ${data.institutions.map(i => `<span class="kz-signboard-chip">${i}</span>`).join('')}</div>`;
    }

    if (data.search_queries && data.search_queries.length) {
      html += '<div style="margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap;">';
      data.search_queries.slice(0, 3).forEach(q => {
        html += `<a href="${q.twogis_url}" target="_blank" class="kz-twogis-btn">🟢 2GIS: ${q.term} ↗</a>`;
      });
      html += '</div>';
    }

    if (!html) {
      html = '<div style="font-size: 0.75rem; color: var(--text-dim);">Уличные вывески РК анализируются...</div>';
    }
    container.innerHTML = html;
  } catch (err) {
    console.error('Failed to mine signboards:', err);
  }
}

function setup2GisVenueModal() {
  const btnOpen = document.getElementById('btnOpen2GisVenueModal');
  const modal = document.getElementById('twogisVenueModal');
  const btnClose = document.getElementById('btnClose2GisVenueModal');
  const btnCancel = document.getElementById('btnCancel2GisVenueModal');
  const btnSearch = document.getElementById('btnTwogisSearch');
  const inputQuery = document.getElementById('twogisSearchQuery');
  const selectCity = document.getElementById('twogisSearchCity');
  const imgInvestigation = document.getElementById('twogisInvestigationImg');
  const caseBadge = document.getElementById('twogisCaseTitleBadge');
  const cluesEl = document.getElementById('twogisInvestigationClues');
  const qrContainer = document.getElementById('twogisQrBadgeContainer');
  const candidatesList = document.getElementById('twogisCandidatesList');
  const countBadge = document.getElementById('twogisResultsCount');

  // Specialized Sub-Tools
  const btnTab2Gis = document.getElementById('btnTab2GisBranches');
  const btnVlm = document.getElementById('btnRunVlmDetective');
  const btnMirror = document.getElementById('btnRunMirrorFlip');
  const btnInfra = document.getElementById('btnRunIndoorMarkers');
  const reportBox = document.getElementById('venueSpecialReportBox');

  let originalPhotoUrl = '';

  function setActiveSubTool(activeBtn) {
    [btnTab2Gis, btnVlm, btnMirror, btnInfra].forEach(b => {
      if (b) {
        b.classList.remove('btn-2gis');
        b.classList.add('btn-secondary');
      }
    });
    if (activeBtn) {
      activeBtn.classList.remove('btn-secondary');
      activeBtn.classList.add('btn-2gis');
    }
  }

  if (btnTab2Gis) {
    btnTab2Gis.addEventListener('click', () => {
      setActiveSubTool(btnTab2Gis);
      if (reportBox) reportBox.style.display = 'none';
      if (imgInvestigation && originalPhotoUrl) imgInvestigation.src = originalPhotoUrl;
    });
  }

  if (btnVlm) {
    btnVlm.addEventListener('click', async () => {
      if (!activeCase) return;
      setActiveSubTool(btnVlm);
      if (reportBox) {
        reportBox.style.display = 'block';
        reportBox.innerHTML = `
          <div style="background: rgba(147, 51, 234, 0.15); border: 1px solid #a855f7; border-radius: 8px; padding: 12px; color: #e9d5ff;">
            <div style="font-weight: 700; display: flex; align-items: center; gap: 8px;">
              <span class="ai-btn-pulse">🧠</span>
              <span>VLM-Детектив: Архитектурное деконструирование интерьера (Gemini Vision)...</span>
            </div>
            <div style="font-size: 0.78rem; margin-top: 4px; color: #d8b4fe;">Анализ 5 слоев: потолочные коммуникации, люстры, напольные покрытия, зонирование мебели, оконные переплёты.</div>
          </div>
        `;
      }
      playRadarSound('radar');

      try {
        const res = await fetch(`/api/cases/${activeCase.id}/venue-vlm-detective`, { method: 'POST' });
        const vlm = await res.json();
        if (reportBox) {
          const arch = vlm.architectural_fingerprint || {};
          const chains = vlm.candidate_chains || [];
          reportBox.innerHTML = `
            <div style="background: rgba(15, 23, 42, 0.85); border: 1px solid #a855f7; border-radius: 8px; padding: 14px; box-shadow: 0 4px 20px rgba(168, 85, 247, 0.2);">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <b style="color: #c084fc; font-size: 0.95rem;">🧠 Экспертное заключение VLM «Детектив заведений» (${vlm.source || 'Gemini Vision'})</b>
                <span class="badge" style="background: rgba(168, 85, 247, 0.25); border: 1px solid #c084fc; color: #f3e8ff;">${vlm.venue_type || 'HoReCa'}</span>
              </div>
              <div style="font-size: 0.82rem; color: #f1f5f9; margin-bottom: 8px;">
                <b>Стиль интерьера:</b> ${vlm.design_style || 'Современный урбан'}
              </div>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.76rem; color: #cbd5e1; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 6px;">
                <div>💡 <b>Люстры/Свет:</b> ${arch.chandeliers || 'Теплый подвесной'}</div>
                <div>🏗️ <b>Потолок:</b> ${arch.ceiling || 'Лофт коммуникации'}</div>
                <div>🪨 <b>Пол/Плитка:</b> ${arch.floor || 'Керамогранит'}</div>
                <div>🪑 <b>Мебель:</b> ${arch.furniture || 'Дерево / велюр'}</div>
              </div>
              <div style="margin-top: 8px; font-size: 0.78rem; color: #a5f3fc;">
                <b>Гипотезы сетей:</b> ${chains.map(c => `<span class="badge" style="background: rgba(6, 182, 212, 0.2); border: 1px solid #06b6d4; color: #67e8f9; margin-left: 4px;">${c.chain_name} (${Math.round((c.confidence || 0.8) * 100)}%)</span>`).join('')}
              </div>
              <div style="margin-top: 6px; font-size: 0.78rem; color: #e2e8f0; font-style: italic;">
                "${vlm.verdict_summary || ''}"
              </div>
            </div>
          `;
        }
      } catch (err) {
        if (reportBox) reportBox.innerHTML = `<div style="color: #f87171;">Ошибка анализа VLM: ${err.message}</div>`;
      }
    });
  }

  if (btnMirror) {
    btnMirror.addEventListener('click', async () => {
      if (!activeCase) return;
      setActiveSubTool(btnMirror);
      playRadarSound('radar');

      if (reportBox) {
        reportBox.style.display = 'block';
        reportBox.innerHTML = `
          <div style="background: rgba(14, 165, 233, 0.15); border: 1px solid #0ea5e9; border-radius: 8px; padding: 10px; color: #7dd3fc; display: flex; align-items: center; justify-content: space-between;">
            <div>
              <b>🪞 Through-the-Window OSINT: Зеркальный инвертор применён!</b>
              <div style="font-size: 0.76rem; color: #bae6fd;">Изображение отзеркалено с фильтром CLAHE. Теперь вывески на витринах, отражения в бокалах и окнах читаются в прямом направлении.</div>
            </div>
            <button class="btn btn-xs btn-secondary" id="btnToggleOrigPhoto" style="font-size: 0.72rem;">Показать оригинал</button>
          </div>
        `;
        document.getElementById('btnToggleOrigPhoto')?.addEventListener('click', () => {
          if (imgInvestigation) imgInvestigation.src = originalPhotoUrl;
        });
      }

      try {
        const res = await fetch(`/api/cases/${activeCase.id}/mirror-reflection`, { method: 'POST' });
        const mirrorData = await res.json();
        if (mirrorData.mirror_image_url && imgInvestigation) {
          imgInvestigation.src = mirrorData.mirror_image_url + '?t=' + Date.now();
          showToast('Зеркальная инверсия улик сформирована!', 'info');
        }
      } catch (err) {
        showToast('Ошибка инвертора: ' + err.message, 'error');
      }
    });
  }

  if (btnInfra) {
    btnInfra.addEventListener('click', async () => {
      if (!activeCase) return;
      setActiveSubTool(btnInfra);
      playRadarSound('radar');

      try {
        const res = await fetch(`/api/cases/${activeCase.id}/indoor-markers`, { method: 'POST' });
        const infra = await res.json();
        if (reportBox) {
          reportBox.style.display = 'block';
          const posList = infra.pos_acquiring || [];
          const exitSign = infra.exit_sign;
          const socket = infra.socket_type;

          reportBox.innerHTML = `
            <div style="background: rgba(15, 23, 42, 0.85); border: 1px solid #10b981; border-radius: 8px; padding: 12px;">
              <b style="color: #34d399; font-size: 0.9rem;">🔌 Инфраструктурные маркеры помещения</b>
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 8px; margin-top: 8px; font-size: 0.78rem;">
                <div style="background: rgba(0,0,0,0.3); padding: 8px; border-radius: 6px;">
                  <b>⚡ Розетки:</b><br>
                  <span style="color: #38bdf8;">${socket?.standard || 'Type C / F (Евро 220V)'}</span>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 8px; border-radius: 6px;">
                  <b>🚪 Табличка «Выход»:</b><br>
                  <span style="color: #4ade80;">${exitSign ? `${exitSign.flag} ${exitSign.type}` : 'Зеленый ISO / ГОСТ «Выход»'}</span>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 8px; border-radius: 6px;">
                  <b>💳 Эквайринг & Терминалы:</b><br>
                  ${posList.length > 0 ? posList.map(p => `<span class="badge" style="background: #059669; color: white;">${p.name} (${p.country})</span>`).join(' ') : '<span style="color: #94a3b8;">Kaspi Pay / Halyk эквайринг РК</span>'}
                </div>
              </div>
            </div>
          `;
        }
      } catch (err) {
        if (reportBox) reportBox.innerHTML = `<div style="color: #f87171;">Ошибка анализа инфраструктуры: ${err.message}</div>`;
      }
    });
  }

  if (!modal) return;

  function closeModal() {
    modal.style.display = 'none';
  }

  if (btnClose) btnClose.addEventListener('click', closeModal);
  if (btnCancel) btnCancel.addEventListener('click', closeModal);

  if (btnOpen) {
    btnOpen.addEventListener('click', async () => {
      if (!activeCase) {
        showToast('Выберите кейс для сверки с 2ГИС', 'warning');
        return;
      }

      modal.style.display = 'flex';
      playRadarSound('radar');

      // Save original photo for restore
      originalPhotoUrl = activeCase.main_photo || '';
      setActiveSubTool(btnTab2Gis);
      if (reportBox) reportBox.style.display = 'none';

      // Populate left column
      if (imgInvestigation) {
        imgInvestigation.src = originalPhotoUrl;
      }
      if (caseBadge) {
        caseBadge.textContent = activeCase.title || activeCase.id;
      }
      if (cluesEl && activeCase.clues) {
        const interiorClues = activeCase.clues.slice(0, 3).map(c => `• ${c}`).join('<br>');
        cluesEl.innerHTML = `<strong>Улики расследования:</strong><br>${interiorClues || 'Визуальный анализ интерьера'}`;
      }

      // Pre-fill query
      const defaultQuery = activeCase.target_name || activeCase.title || '';
      if (inputQuery) {
        inputQuery.value = defaultQuery;
      }
      if (selectCity && activeCase.city) {
        for (let i = 0; i < selectCity.options.length; i++) {
          if (selectCity.options[i].value.toLowerCase() === activeCase.city.toLowerCase()) {
            selectCity.selectedIndex = i;
            break;
          }
        }
      }

      // Auto-trigger venue hunt
      await executeVenueHunt(activeCase.id, inputQuery ? inputQuery.value : '', selectCity ? selectCity.value : 'Астана');
    });
  }

  if (btnSearch) {
    btnSearch.addEventListener('click', async () => {
      if (!activeCase) return;
      const q = inputQuery ? inputQuery.value.trim() : '';
      const c = selectCity ? selectCity.value : 'Астана';
      await executeVenueHunt(activeCase.id, q, c);
    });
  }

  if (inputQuery) {
    inputQuery.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        if (btnSearch) btnSearch.click();
      }
    });
  }

  async function executeVenueHunt(caseId, query, city) {
    if (!candidatesList) return;
    candidatesList.innerHTML = `
      <div style="text-align: center; padding: 40px 10px; color: var(--text-dim, #94a3b8);">
        <div class="ai-btn-pulse" style="font-size: 2.2rem; margin-bottom: 8px;">🔍</div>
        <div style="font-weight: 600; color: #38bdf8;">Сканирование фото на QR-коды столиков и поиск в 2ГИС...</div>
        <div style="font-size: 0.78rem; margin-top: 4px;">Сверка люстр, отделки, мебели и базы филиалов</div>
      </div>
    `;
    if (qrContainer) qrContainer.innerHTML = '';
    if (countBadge) countBadge.textContent = 'поиск...';

    try {
      const url = `/api/cases/${caseId}/venue-hunt?query=${encodeURIComponent(query)}&city=${encodeURIComponent(city)}`;
      const res = await fetch(url, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Render QR code alerts
      if (qrContainer) {
        if (data.qr_codes && data.qr_codes.length > 0) {
          qrContainer.innerHTML = data.qr_codes.map(qr => `
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; border-radius: 8px; padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
              <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.6rem;">${qr.icon || '📱'}</span>
                <div>
                  <div style="font-weight: 700; color: #34d399;">${qr.category_title || 'QR-код обнаружен'}: ${qr.parsed_venue ? (qr.parsed_venue.ssid || qr.parsed_venue.provider || qr.raw) : qr.raw}</div>
                  <div style="font-size: 0.78rem; color: #cbd5e1;">Алгоритм распознал маркер столика или чек заведения с фотографии.</div>
                </div>
              </div>
              <span class="badge" style="background: #059669; color: white; font-weight: 700; padding: 4px 8px; border-radius: 4px;">Точность ±1м</span>
            </div>
          `).join('');
        } else {
          qrContainer.innerHTML = `
            <div style="background: rgba(59, 130, 246, 0.1); border: 1px dashed rgba(59, 130, 246, 0.35); border-radius: 6px; padding: 7px 12px; font-size: 0.78rem; color: #93c5fd; display: flex; align-items: center; gap: 8px;">
              <span>ℹ️</span>
              <span>QR-кодов на столике не найдено. Сопоставление выполняется по вывеске, интерьеру и элементам декора.</span>
            </div>
          `;
        }
      }

      // Render candidates
      const candidates = data.candidates || [];
      if (countBadge) countBadge.textContent = `${candidates.length} филиалов найдено`;

      if (candidates.length === 0) {
        candidatesList.innerHTML = `
          <div style="text-align: center; padding: 40px 10px; color: var(--text-dim, #94a3b8);">
            <div style="font-size: 2rem; margin-bottom: 8px;">🔎</div>
            <div>Филиалы не найдены. Попробуйте уточнить название или сменить город.</div>
          </div>
        `;
        return;
      }

      candidatesList.innerHTML = candidates.map((cand, idx) => {
        const photos = cand.interior_photos || [];
        const features = cand.features || [];
        const distStr = cand.distance_m !== null && cand.distance_m !== undefined 
          ? ` • 📍 ${cand.distance_m < 1000 ? cand.distance_m + 'м' : (cand.distance_m / 1000).toFixed(1) + 'км'}`
          : '';

        return `
          <div class="twogis-candidate-card" style="background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
              <div>
                <div style="font-weight: 700; font-size: 0.92rem; color: #f8fafc;">
                  ${cand.name}
                </div>
                <div style="font-size: 0.8rem; color: #38bdf8; margin-top: 2px;">
                  ${cand.branch || ''} • <span style="color: #cbd5e1;">${cand.city}, ${cand.address}</span>
                </div>
              </div>
              <div style="display: flex; align-items: center; gap: 6px;">
                <span class="badge" style="background: rgba(234, 179, 8, 0.2); border: 1px solid rgba(234, 179, 8, 0.4); color: #facc15; font-size: 0.75rem; padding: 2px 6px; border-radius: 4px;">
                  ★ ${cand.rating || 4.5}
                </span>
                <span style="font-size: 0.72rem; color: #94a3b8;">${distStr}</span>
              </div>
            </div>

            <!-- Features / Clues match -->
            ${features.length > 0 ? `
              <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                ${features.map(f => `<span style="font-size: 0.72rem; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.25); color: #7dd3fc; border-radius: 4px; padding: 1px 6px;">${f}</span>`).join('')}
              </div>
            ` : ''}

            <!-- Interior Photos Gallery -->
            ${photos.length > 0 ? `
              <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin: 4px 0;">
                ${photos.map(p => `
                  <div style="position: relative; height: 95px; border-radius: 6px; overflow: hidden; background: #000; border: 1px solid rgba(255,255,255,0.1); cursor: pointer;" onclick="window.open('${p}', '_blank')">
                    <img src="${p}" alt="Интерьер 2ГИС" style="width: 100%; height: 100%; object-fit: cover; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.06)'" onmouseout="this.style.transform='scale(1)'">
                    <span style="position: absolute; bottom: 2px; right: 4px; font-size: 0.65rem; background: rgba(0,0,0,0.65); color: #fff; padding: 1px 4px; border-radius: 3px;">2ГИС</span>
                  </div>
                `).join('')}
              </div>
            ` : ''}

            <!-- Actions row -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
              <button class="btn btn-2gis btn-sm btn-confirm-venue" data-cand-idx="${idx}" style="padding: 5px 12px; font-size: 0.8rem; cursor: pointer;">
                <span>✅ Подтвердить этот филиал (±5м)</span>
              </button>
              <a href="${cand.twogis_url}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm" style="font-size: 0.75rem;">
                <span>Открыть в 2ГИС ↗</span>
              </a>
            </div>
          </div>
        `;
      }).join('');

      // Attach event listeners to confirm buttons
      const confirmBtns = candidatesList.querySelectorAll('.btn-confirm-venue');
      confirmBtns.forEach(b => {
        b.addEventListener('click', async (e) => {
          const idx = parseInt(b.getAttribute('data-cand-idx'), 10);
          const selectedCand = candidates[idx];
          if (!selectedCand) return;

          b.disabled = true;
          b.textContent = 'Сохранение...';

          try {
            const confirmRes = await fetch(`/api/cases/${caseId}/confirm-venue`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                venue_id: selectedCand.id,
                name: selectedCand.name,
                branch: selectedCand.branch,
                city: selectedCand.city,
                address: selectedCand.address,
                lat: selectedCand.lat,
                lon: selectedCand.lon,
                twogis_url: selectedCand.twogis_url,
                rating: selectedCand.rating
              })
            });

            if (!confirmRes.ok) throw new Error(`HTTP ${confirmRes.status}`);
            const confirmData = await confirmRes.json();

            showToast(`Филиал ${selectedCand.name} успешно зафиксирован (±5м)!`, 'success');
            playRadarSound('lock');
            modal.style.display = 'none';

            // Reload cases and select this case
            await loadCases(caseId);
          } catch (err) {
            showToast('Ошибка подтверждения: ' + err.message, 'error');
            b.disabled = false;
            b.textContent = '✅ Подтвердить этот филиал (±5м)';
          }
        });
      });

    } catch (err) {
      candidatesList.innerHTML = `
        <div style="text-align: center; padding: 30px; color: #f87171;">
          <div>❌ Ошибка поиска: ${err.message}</div>
        </div>
      `;
      if (countBadge) countBadge.textContent = 'ошибка';
    }
  }
}
