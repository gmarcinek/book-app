// api/static/graph-main.js
// Main Graph Application - Orchestrates all modules

window.GraphMain = (function() {
    'use strict';
    
    // ===== STATE =====
    let isInitialized = false;
    let eventListeners = new Map();
    
    // ===== INITIALIZATION =====
    function initialize() {
        console.log('🚀 Initializing Knowledge Graph Application...');
        
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initialize);
            return;
        }
        
        try {
            // Initialize modules in correct order
            initializeModules();
            
            // Setup event system
            setupEventSystem();
            
            // Load initial data
            loadData();
            
            isInitialized = true;
            console.log('✅ Knowledge Graph Application initialized successfully');
            
        } catch (error) {
            console.error('❌ Failed to initialize application:', error);
            if (window.GraphInteractions?.showError) {
                window.GraphInteractions.showError('Nie udało się zainicjalizować aplikacji');
            }
        }
    }
    
    function initializeModules() {
        console.log('🔧 Initializing modules...');
        
        // Check if required modules are available
        const requiredModules = ['GraphConfig', 'GraphData', 'GraphRender', 'GraphInteractions'];
        const missingModules = requiredModules.filter(module => !window[module]);
        
        if (missingModules.length > 0) {
            throw new Error(`Missing required modules: ${missingModules.join(', ')}`);
        }
        
        // Initialize modules
        if (window.GraphRender?.initialize) {
            window.GraphRender.initialize();
        }
        
        if (window.GraphInteractions?.initialize) {
            window.GraphInteractions.initialize();
        }
        
        console.log('✅ All modules initialized');
    }
    
    function setupEventSystem() {
        console.log('📡 Setting up event system...');
        
        // Listen for data filter changes
        addEventListener('dataFiltered', handleDataFiltered);
        
        // Listen for data load events
        addEventListener('dataLoaded', handleDataLoaded);
        addEventListener('dataLoadError', handleDataLoadError);
        
        console.log('✅ Event system ready');
    }
    
    // ===== DATA MANAGEMENT =====
    async function loadData() {
        console.log('📊 Loading graph data...');
        
        try {
            if (window.GraphInteractions?.showLoading) {
                window.GraphInteractions.showLoading();
            }
            
            if (!window.GraphData?.loadGraphData) {
                throw new Error('GraphData module not available');
            }
            
            const result = await window.GraphData.loadGraphData();
            
            console.log('📊 Data loaded successfully:', result);
            
            // Setup filters with discovered types
            if (window.GraphInteractions?.setupFilters) {
                window.GraphInteractions.setupFilters(
                    result.entityTypes, 
                    result.relationshipTypes
                );
            }
            
            // Trigger data loaded event
            triggerEvent('dataLoaded', result);
            
        } catch (error) {
            console.error('❌ Failed to load data:', error);
            triggerEvent('dataLoadError', error);
            
        } finally {
            if (window.GraphInteractions?.hideLoading) {
                window.GraphInteractions.hideLoading();
            }
        }
    }
    
    // ===== EVENT HANDLERS =====
    function handleDataFiltered(data) {
        console.log('🔍 Data filtered, updating visualization...');
        
        // Update graph visualization
        if (window.GraphRender?.render) {
            window.GraphRender.render(data);
        }
        
        // Update stats
        if (window.GraphInteractions?.updateStats && window.GraphData?.getStats) {
            const stats = window.GraphData.getStats();
            window.GraphInteractions.updateStats(stats);
        }
    }
    
    function handleDataLoaded(result) {
        console.log('📊 Data loaded, initial render...');
        
        // Get filtered data for initial render
        if (window.GraphData?.getFilteredData) {
            const data = window.GraphData.getFilteredData();
            handleDataFiltered(data);
        }
        
        console.log('🎉 Application ready!');
    }
    
    function handleDataLoadError(error) {
        console.error('❌ Data load error:', error);
        
        if (window.GraphInteractions?.showError) {
            window.GraphInteractions.showError(
                error.message || 'Nie udało się załadować danych grafu'
            );
        }
    }
    
    // ===== EVENT SYSTEM =====
    function addEventListener(eventName, handler) {
        if (!eventListeners.has(eventName)) {
            eventListeners.set(eventName, []);
        }
        eventListeners.get(eventName).push(handler);
    }
    
    function removeEventListener(eventName, handler) {
        if (eventListeners.has(eventName)) {
            const handlers = eventListeners.get(eventName);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }
    
    function triggerEvent(eventName, data) {
        if (eventListeners.has(eventName)) {
            const handlers = eventListeners.get(eventName);
            handlers.forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`❌ Error in event handler for ${eventName}:`, error);
                }
            });
        }
    }
    
    // ===== UTILITY FUNCTIONS =====
    function refreshGraph() {
        console.log('🔄 Refreshing graph...');
        loadData();
    }
    
    function resetFilters() {
        console.log('🔄 Resetting filters...');
        
        if (window.GraphData?.resetFilters) {
            window.GraphData.resetFilters();
        }
        
        // Reset UI checkboxes
        document.querySelectorAll('#entity-filters input, #relationship-filters input')
            .forEach(checkbox => {
                checkbox.checked = true;
            });
        
        // Clear search
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = '';
        }
    }
    
    function exportData() {
        console.log('💾 Exporting graph data...');
        
        if (!window.GraphData?.getRawData) {
            console.warn('⚠️ Export not available - GraphData module missing');
            return;
        }
        
        const data = window.GraphData.getRawData();
        const stats = window.GraphData.getStats();
        
        const exportData = {
            metadata: {
                exported_at: new Date().toISOString(),
                node_count: data.nodes.length,
                link_count: data.links.length,
                ...stats
            },
            nodes: data.nodes,
            links: data.links
        };
        
        // Create download
        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
            type: 'application/json'
        });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `knowledge-graph-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        console.log('✅ Data exported');
    }
    
    function getApplicationState() {
        return {
            initialized: isInitialized,
            modules: {
                GraphConfig: !!window.GraphConfig,
                GraphData: !!window.GraphData,
                GraphRender: !!window.GraphRender,
                GraphInteractions: !!window.GraphInteractions
            },
            stats: window.GraphData?.getStats?.() || null
        };
    }
    
    // ===== DEBUG HELPERS =====
    function debug() {
        console.log('🐛 Debug Information:');
        console.log('State:', getApplicationState());
        console.log('Event Listeners:', Object.fromEntries(eventListeners));
        
        if (window.GraphData) {
            console.log('Data Stats:', window.GraphData.getStats());
        }
        
        if (window.GraphRender) {
            console.log('Renderer:', {
                simulation: window.GraphRender.simulation,
                container: window.GraphRender.container
            });
        }
    }
    
    // ===== PUBLIC API =====
    const publicAPI = {
        // Core functions
        initialize,
        loadData,
        refreshGraph,
        resetFilters,
        exportData,
        
        // Event system
        addEventListener,
        removeEventListener,
        triggerEvent,
        
        // State
        getApplicationState,
        get isInitialized() { return isInitialized; },
        
        // Debug
        debug
    };
    
    // Auto-initialize when script loads
    initialize();
    
    return publicAPI;
})();

// Export for debugging
window.GraphEvents = {
    trigger: window.GraphMain?.triggerEvent || (() => {}),
    listen: window.GraphMain?.addEventListener || (() => {})
};