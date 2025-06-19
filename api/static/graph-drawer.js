// api/static/graph-drawer.js
// Entity Drawer - Viewing and Editing with proper HTML structure creation

window.GraphDrawer = (function() {
    'use strict';
    
    // ===== STATE =====
    let currentEntity = null;
    let isEditMode = false;
    let allEntities = []; // For relationship editing
    let availableRelationTypes = [];
    let unsavedChanges = false;
    
    // ===== INITIALIZATION =====
    function initialize() {
        console.log('📄 Initializing Graph Drawer...');
        
        // Create proper HTML structure first
        createDrawerHTML();
        setupEventListeners();
        
        console.log('✅ Graph Drawer initialized');
        return true;
    }
    
    // Create the complete HTML structure with higher z-index
    function createDrawerHTML() {
        // Create drawer structure if it doesn't exist
        let drawer = document.getElementById('entity-drawer');
        if (drawer && !drawer.querySelector('.drawer-close')) {
            drawer.innerHTML = `
                <button id="drawer-close" class="drawer-close">✕</button>
                <div class="drawer-content"></div>
            `;
            
            // Set proper CSS for 33% width with high z-index
            drawer.style.width = '33vw';
            drawer.style.right = '-33vw';
            drawer.style.zIndex = '1052'; // Ensure it's above everything
            drawer.style.position = 'fixed';
        }
        
        // Ensure overlay exists with proper z-index
        let overlay = document.getElementById('drawer-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'drawer-overlay';
            overlay.className = 'drawer-overlay';
            overlay.style.zIndex = '1051'; // Below drawer but above everything else
            overlay.style.position = 'fixed';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.right = '0';
            overlay.style.bottom = '0';
            overlay.style.background = 'rgba(0, 0, 0, 0.5)';
            overlay.style.opacity = '0';
            overlay.style.visibility = 'hidden';
            overlay.style.transition = 'all 0.3s ease';
            document.body.appendChild(overlay);
        }
        
        console.log('✅ Drawer HTML structure created with high z-index');
    }
    
    function setupEventListeners() {
        // Close button
        const closeBtn = document.getElementById('drawer-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', closeDrawer);
            console.log('✅ Close button listener added');
        }
        
        // Overlay click
        const overlay = document.getElementById('drawer-overlay');
        if (overlay) {
            overlay.addEventListener('click', closeDrawer);
            console.log('✅ Overlay click listener added');
        }
        
        // Escape key
        document.addEventListener('keydown', handleEscapeKey);
        console.log('✅ Escape key listener added');
    }
    
    // ===== MAIN DRAWER FUNCTIONS =====
    async function showEntity(entity) {
        console.log('📄 Showing entity in drawer:', entity.name);
        
        currentEntity = entity;
        isEditMode = false;
        unsavedChanges = false;
        
        // Show drawer and overlay
        const drawer = document.getElementById('entity-drawer');
        const overlay = document.getElementById('drawer-overlay');
        
        if (drawer && overlay) {
            console.log('📄 Making drawer visible...');
            console.log('📄 Drawer current styles:', {
                right: drawer.style.right,
                zIndex: drawer.style.zIndex,
                position: drawer.style.position
            });
            
            // Force proper positioning
            drawer.style.right = '-33vw';
            drawer.style.zIndex = '1052';
            drawer.style.position = 'fixed';
            
            overlay.style.zIndex = '1051';
            overlay.style.position = 'fixed';
            
            // Show overlay first
            overlay.style.opacity = '1';
            overlay.style.visibility = 'visible';
            overlay.classList.add('visible');
            
            // Then show drawer
            setTimeout(() => {
                drawer.style.right = '0';
                drawer.classList.add('open');
                console.log('📄 Drawer should now be visible at right: 0');
            }, 50); // Small delay for smooth animation
            
            console.log('✅ Drawer and overlay shown');
        } else {
            console.error('❌ Drawer or overlay element not found!', { drawer: !!drawer, overlay: !!overlay });
            return;
        }
        
        // Load full entity data
        await loadFullEntityData(entity.id);
        
        // Render in view mode
        renderDrawerContent();
        
        console.log('✅ Entity drawer opened successfully');
    }
    
    async function loadFullEntityData(entityId) {
        try {
            console.log('📡 Loading full entity data:', entityId);
            
            // Load entity details
            const entityResponse = await fetch(`/entities/${entityId}`);
            if (entityResponse.ok) {
                const entityData = await entityResponse.json();
                
                // Merge with current entity data
                currentEntity = {
                    ...currentEntity,
                    ...entityData.entity,
                    relationships: entityData.relationships || [],
                    related_entities: entityData.related_entities || []
                };
                console.log('✅ Entity data loaded');
            } else {
                console.warn('⚠️ Failed to load entity details, using basic data');
            }
            
            // Load all entities for relationship editing
            const entitiesResponse = await fetch('/entities?limit=200');
            if (entitiesResponse.ok) {
                allEntities = await entitiesResponse.json();
                console.log('✅ All entities loaded for relationship editing');
            }
            
            // Load available relationship types from graph
            const graphResponse = await fetch('/graph?max_nodes=1&max_edges=1');
            if (graphResponse.ok) {
                const graphData = await graphResponse.json();
                availableRelationTypes = [...new Set(
                    graphData.edges?.map(e => e.relation_type).filter(Boolean) || []
                )];
                console.log('✅ Available relationship types loaded');
            }
            
        } catch (error) {
            console.error('❌ Failed to load entity data:', error);
            
            // Use fallback data
            if (!allEntities.length) {
                allEntities = [currentEntity];
            }
            if (!availableRelationTypes.length) {
                availableRelationTypes = ['related_to', 'contains', 'part_of'];
            }
        }
    }
    
    function renderDrawerContent() {
        if (!currentEntity) {
            console.error('❌ No current entity to render');
            return;
        }
        
        const drawerContent = document.querySelector('.drawer-content');
        if (!drawerContent) {
            console.error('❌ Drawer content container not found');
            return;
        }
        
        console.log('🎨 Rendering drawer content for:', currentEntity.name);
        
        drawerContent.innerHTML = generateDrawerHTML();
        
        // Setup event listeners for dynamic content
        setupDynamicEventListeners();
        
        console.log('✅ Drawer content rendered');
    }
    
    function generateDrawerHTML() {
        const entity = currentEntity;
        
        return `
            <!-- Header with Edit Toggle -->
            <div class="drawer-entity-header">
                <div class="entity-title-section">
                    <h2 class="entity-name">${entity.name || 'Unknown Entity'}</h2>
                    <div class="entity-type-badge" style="background-color: ${getEntityTypeColor(entity.type)}20; color: ${getEntityTypeColor(entity.type)}">
                        ${entity.type || 'UNKNOWN'}
                    </div>
                </div>
                <div class="drawer-actions">
                    <button id="edit-toggle-btn" class="btn primary ${isEditMode ? 'active' : ''}" onclick="window.GraphDrawer.toggleEditMode()">
                        ${isEditMode ? '👁️ View' : '✏️ Edit'}
                    </button>
                    <button id="entity-link-btn" class="btn" onclick="window.GraphDrawer.copyEntityLink()" title="Copy entity link">
                        🔗 Link
                    </button>
                    ${isEditMode ? `
                        <button id="save-btn" class="btn primary" onclick="window.GraphDrawer.saveChanges()" ${!unsavedChanges ? 'disabled' : ''}>
                            💾 Save
                        </button>
                        <button id="cancel-btn" class="btn secondary" onclick="window.GraphDrawer.cancelEdit()">
                            ❌ Cancel
                        </button>
                    ` : ''}
                </div>
            </div>
            
            <!-- Description Section -->
            <div class="drawer-section">
                <h3 class="section-title">📝 Description</h3>
                ${renderDescriptionSection()}
            </div>
            
            <!-- Aliases Section -->
            <div class="drawer-section">
                <h3 class="section-title">🏷️ Aliases</h3>
                ${renderAliasesSection()}
            </div>
            
            <!-- Entity Relationships Section -->
            <div class="drawer-section">
                <h3 class="section-title">🔗 Entity Relationships</h3>
                ${renderEntityRelationshipsSection()}
            </div>
            
            <!-- Chunk Relationships Section (Read-only) -->
            <div class="drawer-section">
                <h3 class="section-title">📄 Chunk Relationships (Read-only)</h3>
                ${renderChunkRelationshipsSection()}
            </div>
        `;
    }
    
    function renderDescriptionSection() {
        const description = currentEntity.description || '';
        
        if (isEditMode) {
            return `
                <textarea 
                    id="description-editor" 
                    class="description-textarea"
                    placeholder="Enter entity description..."
                    onchange="window.GraphDrawer.markUnsaved()"
                >${description}</textarea>
            `;
        } else {
            return `
                <div class="description-display">
                    ${description || '<em>No description available</em>'}
                </div>
            `;
        }
    }
    
    function renderAliasesSection() {
        const aliases = currentEntity.aliases || [];
        
        if (isEditMode) {
            return `
                <div class="aliases-editor">
                    <div class="aliases-list" id="aliases-list">
                        ${aliases.map((alias, index) => `
                            <div class="alias-item editable" data-index="${index}">
                                <input 
                                    type="text" 
                                    value="${alias}" 
                                    class="alias-input"
                                    onchange="window.GraphDrawer.updateAlias(${index}, this.value)"
                                />
                                <button class="alias-delete-btn" onclick="window.GraphDrawer.removeAlias(${index})">🗑️</button>
                            </div>
                        `).join('')}
                    </div>
                    <button class="btn secondary" onclick="window.GraphDrawer.addNewAlias()">
                        ➕ Add Alias
                    </button>
                </div>
            `;
        } else {
            if (aliases.length === 0) {
                return '<div class="aliases-display"><em>No aliases</em></div>';
            }
            
            return `
                <div class="aliases-display">
                    ${aliases.map(alias => `<span class="alias-tag">${alias}</span>`).join('')}
                </div>
            `;
        }
    }
    
    function renderEntityRelationshipsSection() {
        const entityRelationships = (currentEntity.relationships || [])
            .filter(rel => rel.target !== currentEntity.id || rel.source !== currentEntity.id);
        
        if (isEditMode) {
            return `
                <div class="relationships-editor">
                    <div class="relationships-list" id="relationships-list">
                        ${entityRelationships.map((rel, index) => `
                            <div class="relationship-item editable" data-index="${index}">
                                <div class="relationship-controls">
                                    <select 
                                        class="relation-type-select"
                                        onchange="window.GraphDrawer.updateRelationshipType(${index}, this.value)"
                                    >
                                        ${availableRelationTypes.map(type => `
                                            <option value="${type}" ${rel.relation_type === type ? 'selected' : ''}>
                                                ${type}
                                            </option>
                                        `).join('')}
                                    </select>
                                    
                                    <select 
                                        class="relation-target-select"
                                        onchange="window.GraphDrawer.updateRelationshipTarget(${index}, this.value)"
                                    >
                                        ${allEntities.map(entity => `
                                            <option value="${entity.id}" ${getRelationshipTarget(rel) === entity.id ? 'selected' : ''}>
                                                ${entity.name} (${entity.type})
                                            </option>
                                        `).join('')}
                                    </select>
                                    
                                    <button class="relationship-delete-btn" onclick="window.GraphDrawer.removeRelationship(${index})">
                                        🗑️
                                    </button>
                                </div>
                                <div class="relationship-confidence">
                                    Confidence: ${((rel.confidence || 0) * 100).toFixed(1)}%
                                </div>
                            </div>
                        `).join('')}
                    </div>
                    <button class="btn secondary" onclick="window.GraphDrawer.addNewRelationship()">
                        ➕ Add Relationship
                    </button>
                </div>
            `;
        } else {
            if (entityRelationships.length === 0) {
                return '<div class="relationships-display"><em>No entity relationships</em></div>';
            }
            
            return `
                <div class="relationships-display">
                    ${entityRelationships.map(rel => `
                        <div class="relationship-item">
                            <div class="relationship-type">${rel.relation_type || 'unknown'}</div>
                            <div class="relationship-target" onclick="window.GraphDrawer.openRelatedEntity('${getRelationshipTarget(rel)}')" title="Click to view this entity">
                                ${getRelationshipTargetName(rel)}
                            </div>
                            <div class="relationship-confidence">Confidence: ${((rel.confidence || 0) * 100).toFixed(1)}%</div>
                        </div>
                    `).join('')}
                </div>
            `;
        }
    }
    
    function renderChunkRelationshipsSection() {
        const chunkRelationships = (currentEntity.relationships || [])
            .filter(rel => rel.relation_type === 'contains');
        
        if (chunkRelationships.length === 0) {
            return '<div class="chunk-relationships-display"><em>No chunk relationships</em></div>';
        }
        
        return `
            <div class="chunk-relationships-display">
                ${chunkRelationships.map(rel => `
                    <div class="chunk-relationship-item">
                        <div class="chunk-info" onclick="window.GraphDrawer.openChunkInNewWindow('${rel.source}')" title="Click to view chunk details">
                            📄 Chunk ${rel.source}
                        </div>
                        <div class="chunk-confidence">Confidence: ${((rel.confidence || 0) * 100).toFixed(1)}%</div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    // ===== EDIT MODE FUNCTIONS =====
    function toggleEditMode() {
        if (isEditMode && unsavedChanges) {
            if (!confirm('You have unsaved changes. Discard them?')) {
                return;
            }
        }
        
        isEditMode = !isEditMode;
        unsavedChanges = false;
        renderDrawerContent();
    }
    
    function markUnsaved() {
        unsavedChanges = true;
        
        // Update save button state
        const saveBtn = document.getElementById('save-btn');
        if (saveBtn) {
            saveBtn.disabled = false;
        }
    }
    
    // ===== ALIASES EDITING =====
    function updateAlias(index, newValue) {
        if (!currentEntity.aliases) currentEntity.aliases = [];
        currentEntity.aliases[index] = newValue.trim();
        markUnsaved();
    }
    
    function removeAlias(index) {
        if (!currentEntity.aliases) return;
        currentEntity.aliases.splice(index, 1);
        markUnsaved();
        renderDrawerContent();
    }
    
    function addNewAlias() {
        if (!currentEntity.aliases) currentEntity.aliases = [];
        currentEntity.aliases.push('');
        markUnsaved();
        renderDrawerContent();
        
        // Focus on the new alias input
        setTimeout(() => {
            const newInput = document.querySelector('.alias-item:last-child .alias-input');
            if (newInput) newInput.focus();
        }, 100);
    }
    
    // ===== RELATIONSHIPS EDITING =====
    function updateRelationshipType(index, newType) {
        if (!currentEntity.relationships) return;
        currentEntity.relationships[index].relation_type = newType;
        markUnsaved();
    }
    
    function updateRelationshipTarget(index, newTargetId) {
        if (!currentEntity.relationships) return;
        const rel = currentEntity.relationships[index];
        
        // Update target while preserving relationship structure
        if (rel.source === currentEntity.id) {
            rel.target = newTargetId;
        } else {
            rel.source = newTargetId;
        }
        
        markUnsaved();
    }
    
    function removeRelationship(index) {
        if (!currentEntity.relationships) return;
        currentEntity.relationships.splice(index, 1);
        markUnsaved();
        renderDrawerContent();
    }
    
    function addNewRelationship() {
        if (!currentEntity.relationships) currentEntity.relationships = [];
        
        // Add a new relationship
        const newRelationship = {
            source: currentEntity.id,
            target: allEntities[0]?.id || '',
            relation_type: availableRelationTypes[0] || 'related_to',
            confidence: 0.8
        };
        
        currentEntity.relationships.push(newRelationship);
        markUnsaved();
        renderDrawerContent();
    }
    
    // ===== SAVE/CANCEL =====
    async function saveChanges() {
        if (!currentEntity || !unsavedChanges) return;
        
        try {
            console.log('💾 Saving entity changes...');
            
            // Get current form values
            const descriptionEl = document.getElementById('description-editor');
            if (descriptionEl) {
                currentEntity.description = descriptionEl.value.trim();
            }
            
            // Prepare data for API - only send changed fields
            const updateData = {
                name: currentEntity.name,
                description: currentEntity.description,
                aliases: currentEntity.aliases || [],
                type: currentEntity.type,
                confidence: currentEntity.confidence
            };
            
            console.log('📡 Sending PUT request to API...', updateData);
            
            // Save entity using the new PUT endpoint
            const response = await fetch(`/entities/${currentEntity.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updateData)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`HTTP ${response.status}: ${errorData.detail || response.statusText}`);
            }
            
            const result = await response.json();
            console.log('✅ Entity saved successfully:', result);
            
            unsavedChanges = false;
            
            // Update graph if available
            if (window.GraphMain?.refreshGraph) {
                window.GraphMain.refreshGraph();
            }
            
            // Switch back to view mode
            isEditMode = false;
            renderDrawerContent();
            
        } catch (error) {
            console.error('❌ Failed to save entity:', error);
            alert(`Failed to save changes: ${error.message}`);
        }
    }
    
    function cancelEdit() {
        if (unsavedChanges) {
            if (!confirm('You have unsaved changes. Discard them?')) {
                return;
            }
        }
        
        // Reload original data
        loadFullEntityData(currentEntity.id).then(() => {
            isEditMode = false;
            unsavedChanges = false;
            renderDrawerContent();
        });
    }
    
    // ===== UTILITY FUNCTIONS =====
    function getEntityTypeColor(entityType) {
        return window.GraphConfig?.getEntityColor(entityType) || '#9ca3af';
    }
    
    function getRelationshipTarget(relationship) {
        return relationship.target === currentEntity.id ? relationship.source : relationship.target;
    }
    
    function getRelationshipTargetName(relationship) {
        const targetId = getRelationshipTarget(relationship);
        const targetEntity = allEntities.find(e => e.id === targetId);
        return targetEntity ? `${targetEntity.name} (${targetEntity.type})` : targetId;
    }
    
    function setupDynamicEventListeners() {
        // Additional event listeners for dynamic content can be added here
    }
    
    // ===== NAVIGATION FUNCTIONS =====
    async function openRelatedEntity(entityId) {
        if (!entityId) return;
        
        console.log('🔄 Opening related entity:', entityId);
        
        try {
            // Find entity in current data first
            let entity = allEntities.find(e => e.id === entityId);
            
            if (!entity) {
                // If not found, fetch from API
                const response = await fetch(`/entities/${entityId}`);
                if (response.ok) {
                    const data = await response.json();
                    entity = data.entity;
                } else {
                    throw new Error('Entity not found');
                }
            }
            
            if (entity) {
                // Show this entity in the drawer
                await showEntity(entity);
            }
            
        } catch (error) {
            console.error('❌ Failed to open related entity:', error);
            alert(`Failed to load entity: ${error.message}`);
        }
    }
    
    function openChunkInNewWindow(chunkId) {
        if (!chunkId) return;
        
        console.log('🪟 Opening chunk in new window:', chunkId);
        
        try {
            // Create URL for chunk details (you might need to implement this endpoint)
            const chunkUrl = `/entities/${chunkId}`;
            
            // Open in new window/tab
            window.open(chunkUrl, '_blank', 'width=800,height=600,scrollbars=yes,resizable=yes');
            
        } catch (error) {
            console.error('❌ Failed to open chunk:', error);
            alert(`Failed to open chunk: ${error.message}`);
        }
    }
    function copyEntityLink() {
        if (!currentEntity) return;
        
        // Create shareable link to entity
        const baseUrl = window.location.origin + window.location.pathname;
        const entityUrl = `${baseUrl}?entity=${encodeURIComponent(currentEntity.id)}`;
        
        // Copy to clipboard
        navigator.clipboard.writeText(entityUrl).then(() => {
            console.log('📋 Entity link copied to clipboard:', entityUrl);
            
            // Show visual feedback
            const linkBtn = document.getElementById('entity-link-btn');
            if (linkBtn) {
                const originalText = linkBtn.innerHTML;
                linkBtn.innerHTML = '✅ Copied!';
                linkBtn.style.background = 'rgba(34, 197, 94, 0.8)';
                
                setTimeout(() => {
                    linkBtn.innerHTML = originalText;
                    linkBtn.style.background = '';
                }, 2000);
            }
            
            // Optional: Show tooltip or toast notification
            showTemporaryTooltip('Entity link copied to clipboard!');
            
        }).catch(err => {
            console.error('❌ Failed to copy link:', err);
            
            // Fallback: show the link in a prompt
            prompt('Copy this entity link:', entityUrl);
        });
    }
    
    function showTemporaryTooltip(message) {
        // Create temporary tooltip
        const tooltip = document.createElement('div');
        tooltip.className = 'temp-tooltip';
        tooltip.textContent = message;
        tooltip.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(34, 197, 94, 0.9);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            z-index: 2000;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        
        document.body.appendChild(tooltip);
        
        // Animate in
        setTimeout(() => tooltip.style.opacity = '1', 10);
        
        // Remove after 3 seconds
        setTimeout(() => {
            tooltip.style.opacity = '0';
            setTimeout(() => document.body.removeChild(tooltip), 300);
        }, 3000);
    }
    
    // ===== DRAWER CONTROL =====
    function closeDrawer() {
        if (isEditMode && unsavedChanges) {
            if (!confirm('You have unsaved changes. Close anyway?')) {
                return;
            }
        }
        
        console.log('📄 Closing drawer...');
        
        const drawer = document.getElementById('entity-drawer');
        const overlay = document.getElementById('drawer-overlay');
        
        if (drawer) {
            // Use inline styles to hide drawer
            drawer.style.right = '-33vw';
            drawer.classList.remove('open');
            console.log('📄 Drawer moved to right: -33vw');
        }
        
        if (overlay) {
            // Use inline styles to hide overlay
            overlay.style.opacity = '0';
            overlay.style.visibility = 'hidden';
            overlay.classList.remove('visible');
            console.log('📄 Overlay hidden');
        }
        
        // Reset state
        currentEntity = null;
        isEditMode = false;
        unsavedChanges = false;
        
        console.log('✅ Drawer closed');
    }
    
    function handleEscapeKey(event) {
        if (event.key === 'Escape') {
            closeDrawer();
        }
    }
    
    // ===== PUBLIC API =====
    return {
        initialize,
        showEntity,
        closeDrawer,
        
        // Edit functions (exposed for onclick handlers)
        toggleEditMode,
        markUnsaved,
        saveChanges,
        cancelEdit,
        
        // Link function
        copyEntityLink,
        
        // Navigation functions
        openRelatedEntity,
        openChunkInNewWindow,
        
        // Alias functions
        updateAlias,
        removeAlias,
        addNewAlias,
        
        // Relationship functions
        updateRelationshipType,
        updateRelationshipTarget,
        removeRelationship,
        addNewRelationship,
        
        // State getters
        get currentEntity() { return currentEntity; },
        get isEditMode() { return isEditMode; },
        get hasUnsavedChanges() { return unsavedChanges; }
    };
})();