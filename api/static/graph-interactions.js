// api/static/graph-interactions.js
// Graph User Interactions - Tooltips, Events, UI Controls

window.GraphInteractions = (function () {
    'use strict';

    // ===== STATE =====
    let tooltip;
    let isInitialized = false;

    // ===== INITIALIZATION =====
    function initialize() {
        console.log('🎯 Initializing graph interactions...');

        tooltip = d3.select('#tooltip');
        setupEventListeners();

        isInitialized = true;
        console.log('✅ Graph interactions initialized');
        return true;
    }

    function setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', handleRefresh);
        }

        // Search input
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            const debounce = window.GraphConfig?.debounce || ((func, wait) => {
                let timeout;
                return function executedFunction(...args) {
                    const later = () => {
                        clearTimeout(timeout);
                        func(...args);
                    };
                    clearTimeout(timeout);
                    timeout = setTimeout(later, wait);
                };
            });

            searchInput.addEventListener('input', debounce(handleSearch, 300));
        }

        // Window resize
        window.addEventListener('resize', debounce(handleResize, 250));

        // Hide tooltip on click anywhere
        document.addEventListener('click', hideTooltip);
    }

    // ===== TOOLTIP MANAGEMENT =====
    function showEntityTooltip(event, d) {
        const truncate = window.GraphConfig?.truncateText || ((text, max) =>
            text?.length > max ? text.slice(0, max) + '...' : text || '');

        const content = `
            <div class="tooltip-title">${d.name}</div>
            <div class="tooltip-type">Typ: ${d.type}</div>
            <div class="tooltip-confidence">Confidence: ${(d.confidence * 100).toFixed(1)}%</div>
            ${d.aliases?.length > 0 ? `<div>Aliasy: ${d.aliases.slice(0, 3).join(', ')}</div>` : ''}
            ${d.description ? `<div class="tooltip-description">${truncate(d.description, 100)}</div>` : ''}
        `;

        showTooltip(event, content);
    }

    function showRelationshipTooltip(event, d) {
        const sourceName = getEntityName(d.source);
        const targetName = getEntityName(d.target);
        const truncate = window.GraphConfig?.truncateText || ((text, max) =>
            text?.length > max ? text.slice(0, max) + '...' : text || '');

        const content = `
            <div class="tooltip-title">${d.type}</div>
            <div>${sourceName} → ${targetName}</div>
            <div class="tooltip-confidence">Confidence: ${(d.confidence * 100).toFixed(1)}%</div>
            ${d.evidence ? `<div class="tooltip-description">"${truncate(d.evidence, 80)}"</div>` : ''}
            ${d.discovery_method ? `<div style="font-size:11px; opacity:0.7;">Metoda: ${d.discovery_method}</div>` : ''}
        `;

        showTooltip(event, content);
    }

    function showTooltip(event, content) {
        if (!tooltip) return;

        tooltip
            .style('display', 'block')
            .html(content);

        // Position tooltip
        const tooltipNode = tooltip.node();
        const rect = tooltipNode.getBoundingClientRect();

        let left = event.pageX + 15;
        let top = event.pageY - 10;

        // Keep tooltip within viewport
        if (left + rect.width > window.innerWidth) {
            left = event.pageX - rect.width - 15;
        }
        if (top + rect.height > window.innerHeight) {
            top = event.pageY - rect.height - 10;
        }

        tooltip
            .style('left', left + 'px')
            .style('top', top + 'px');
    }

    function hideTooltip() {
        if (tooltip) {
            tooltip.style('display', 'none');
        }
    }

    // ===== FILTER MANAGEMENT =====
    function setupFilters(entityTypes, relationshipTypes) {
        console.log('🎛️ Setting up filters...');

        setupEntityFilters(entityTypes);
        setupRelationshipFilters(relationshipTypes);
    }

    function setupEntityFilters(entityTypes) {
        const container = document.getElementById('entity-filters');
        if (!container) return;

        container.innerHTML = '';

        entityTypes.forEach(type => {
            const label = document.createElement('label');
            label.innerHTML = `<input type="checkbox" value="${type}" checked><span>${type}</span>`;
            label.setAttribute('data-type', type);

            // Apply color to the span element
            if (window.GraphConfig?.getEntityColor) {
                const span = label.querySelector('span');
                if (span) {
                    span.style.color = window.GraphConfig.getEntityColor(type);
                }
            }

            // Add event listener
            const checkbox = label.querySelector('input');
            checkbox.addEventListener('change', (event) => {
                handleEntityTypeFilter(type, event.target.checked);
            });

            container.appendChild(label);
        });
    }

    function setupRelationshipFilters(relationshipTypes) {
        const container = document.getElementById('relationship-filters');
        if (!container) return;

        container.innerHTML = '';

        relationshipTypes.forEach(type => {
            const label = document.createElement('label');
            label.innerHTML = `<input type="checkbox" value="${type}" checked> ${type}`;

            // Add event listener
            const checkbox = label.querySelector('input');
            checkbox.addEventListener('change', (event) => {
                handleRelationshipTypeFilter(type, event.target.checked);
            });

            container.appendChild(label);
        });
    }

    // ===== EVENT HANDLERS =====
    function handleRefresh() {
        console.log('🔄 Refresh button clicked');
        if (window.GraphMain?.loadData) {
            window.GraphMain.loadData();
        }
    }

    function handleSearch(event) {
        const query = event.target.value.trim();
        console.log('🔍 Search query:', query);

        if (window.GraphData?.setSearchQuery) {
            window.GraphData.setSearchQuery(query);
        }
    }

    function handleEntityTypeFilter(type, active) {
        console.log('🎛️ Entity filter changed:', type, active);

        if (window.GraphData?.setEntityTypeFilter) {
            window.GraphData.setEntityTypeFilter(type, active);
        }
    }

    function handleRelationshipTypeFilter(type, active) {
        console.log('🎛️ Relationship filter changed:', type, active);

        if (window.GraphData?.setRelationshipTypeFilter) {
            window.GraphData.setRelationshipTypeFilter(type, active);
        }
    }

    function handleResize() {
        console.log('📏 Window resized');

        if (window.GraphRender?.handleResize) {
            window.GraphRender.handleResize();
        }
    }

    // ===== STATS UPDATE =====
    function updateStats(stats) {
        const nodeCountEl = document.getElementById('nodeCount');
        const edgeCountEl = document.getElementById('edgeCount');

        if (nodeCountEl) {
            nodeCountEl.textContent = `${stats.filtered.nodes} encji`;
        }

        if (edgeCountEl) {
            edgeCountEl.textContent = `${stats.filtered.links} relacji`;
        }
    }

    // ===== LOADING STATES =====
    function showLoading() {
        const loading = document.getElementById('loading');
        if (loading) {
            loading.style.display = 'flex';
        }
    }

    function hideLoading() {
        const loading = document.getElementById('loading');
        if (loading) {
            loading.style.display = 'none';
        }
    }

    function showError(message) {
        console.error('❌ Graph error:', message);

        // Could implement a proper error UI here
        alert(`Błąd: ${message}`);
    }

    // ===== UTILITIES =====
    function getEntityName(entityRef) {
        // Handle both entity objects and IDs
        if (typeof entityRef === 'string') {
            const entity = window.GraphData?.findEntityById(entityRef);
            return entity?.name || entityRef;
        }
        return entityRef?.name || entityRef?.id || 'Unknown';
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // ===== PUBLIC API =====
    return {
        // Initialization
        initialize,
        setupFilters,

        // Tooltips
        showEntityTooltip,
        showRelationshipTooltip,
        hideTooltip,

        // UI Updates
        updateStats,
        showLoading,
        hideLoading,
        showError,

        // Event handlers (exposed for external use)
        handleRefresh,
        handleSearch,
        handleEntityTypeFilter,
        handleRelationshipTypeFilter,

        // State
        get isInitialized() { return isInitialized; }
    };
})();