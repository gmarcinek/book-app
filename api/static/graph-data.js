// Graph Data Management - Loading, Processing, Filtering
window.GraphData = (function() {
    'use strict';
    
    // ===== STATE =====
    let rawNodes = [];
    let rawLinks = [];
    let filteredNodes = [];
    let filteredLinks = [];
    
    let activeEntityTypes = new Set();
    let activeRelationshipTypes = new Set();
    let searchQuery = '';
    
    // ===== DATA LOADING =====
    async function loadGraphData() {
        try {
            console.log('🔄 Loading graph data...');
            
            const response = await fetch('/graph?max_nodes=300&max_edges=500');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('📊 Graph data loaded:', data.stats);
            
            return processRawData(data);
            
        } catch (error) {
            console.error('❌ Failed to load graph data:', error);
            throw error;
        }
    }
    
    // ===== DATA PROCESSING =====
    function processRawData(data) {
        console.log('📊 Processing raw data...');
        console.log('📊 Raw nodes:', data.nodes?.length || 0);
        console.log('📊 Raw edges:', data.edges?.length || 0);
        
        // Process nodes - they are already entities
        rawNodes = data.nodes
            .filter(node => node.id && node.name && node.type)
            .map(node => ({
                id: node.id,
                name: node.name,
                type: node.type,
                confidence: node.confidence || 0.5,
                aliases: node.aliases || [],
                description: node.description || '',
                context: node.context || '',
                created_at: node.created_at,
                // Keep all original fields
                ...node
            }));
        
        // Process edges/relationships
        rawLinks = data.edges
            .filter(edge => {
                const sourceExists = rawNodes.some(n => n.id === edge.source);
                const targetExists = rawNodes.some(n => n.id === edge.target);
                return sourceExists && targetExists && edge.relation_type;
            })
            .map(edge => ({
                source: edge.source,
                target: edge.target,
                type: edge.relation_type,
                confidence: edge.confidence || 0.8,
                evidence: edge.evidence_text || edge.evidence || '',
                created_at: edge.created_at,
                discovery_method: edge.discovery_method || 'unknown'
            }));
        
        console.log(`📚 Processed: ${rawNodes.length} entities, ${rawLinks.length} relationships`);
        
        // Extract unique types
        const entityTypes = [...new Set(rawNodes.map(n => n.type))].sort();
        const relationshipTypes = [...new Set(rawLinks.map(l => l.type))].sort();
        
        console.log('🎯 Found entity types:', entityTypes);
        console.log('🔗 Found relationship types:', relationshipTypes);
        
        // Update config
        window.GraphConfig.setEntityTypes(entityTypes);
        window.GraphConfig.setRelationshipTypes(relationshipTypes);
        
        // Initialize filters with all types
        activeEntityTypes = new Set(entityTypes);
        activeRelationshipTypes = new Set(relationshipTypes);
        
        // Apply initial filtering
        applyFilters();
        
        return {
            entityTypes,
            relationshipTypes,
            nodesCount: rawNodes.length,
            linksCount: rawLinks.length
        };
    }
    
    // ===== FILTERING =====
    function applyFilters() {
        console.log('🔍 Applying filters...');
        
        // Filter nodes
        filteredNodes = rawNodes.filter(node => {
            const typeMatch = activeEntityTypes.has(node.type);
            const searchMatch = searchQuery === '' || 
                node.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                node.aliases.some(alias => alias.toLowerCase().includes(searchQuery.toLowerCase()));
            
            return typeMatch && searchMatch;
        });
        
        // Get filtered node IDs
        const nodeIds = new Set(filteredNodes.map(n => n.id));
        
        // Filter links
        filteredLinks = rawLinks.filter(link => {
            const typeMatch = activeRelationshipTypes.has(link.type);
            const nodeMatch = nodeIds.has(link.source) && nodeIds.has(link.target);
            
            return typeMatch && nodeMatch;
        });
        
        console.log(`🔍 Filtered result: ${filteredNodes.length} nodes, ${filteredLinks.length} links`);
        
        // Trigger update event
        if (window.GraphEvents) {
            window.GraphEvents.trigger('dataFiltered', {
                nodes: filteredNodes,
                links: filteredLinks
            });
        }
    }
    
    // ===== FILTER CONTROLS =====
    function setEntityTypeFilter(type, active) {
        if (active) {
            activeEntityTypes.add(type);
        } else {
            activeEntityTypes.delete(type);
        }
        applyFilters();
    }
    
    function setRelationshipTypeFilter(type, active) {
        if (active) {
            activeRelationshipTypes.add(type);
        } else {
            activeRelationshipTypes.delete(type);
        }
        applyFilters();
    }
    
    function setSearchQuery(query) {
        searchQuery = query.trim();
        applyFilters();
    }
    
    function resetFilters() {
        activeEntityTypes = new Set(window.GraphConfig.getEntityTypes());
        activeRelationshipTypes = new Set(window.GraphConfig.getRelationshipTypes());
        searchQuery = '';
        applyFilters();
    }
    
    // ===== DATA ACCESS =====
    function getFilteredData() {
        return {
            nodes: [...filteredNodes],
            links: [...filteredLinks]
        };
    }
    
    function getRawData() {
        return {
            nodes: [...rawNodes],
            links: [...rawLinks]
        };
    }
    
    function getStats() {
        return {
            raw: {
                nodes: rawNodes.length,
                links: rawLinks.length
            },
            filtered: {
                nodes: filteredNodes.length,
                links: filteredLinks.length
            },
            filters: {
                activeEntityTypes: Array.from(activeEntityTypes),
                activeRelationshipTypes: Array.from(activeRelationshipTypes),
                searchQuery
            }
        };
    }
    
    // ===== ENTITY LOOKUP =====
    function findEntityById(id) {
        return rawNodes.find(node => node.id === id);
    }
    
    function findEntitiesByType(type) {
        return rawNodes.filter(node => node.type === type);
    }
    
    function searchEntities(query) {
        const lowerQuery = query.toLowerCase();
        return rawNodes.filter(node =>
            node.name.toLowerCase().includes(lowerQuery) ||
            node.aliases.some(alias => alias.toLowerCase().includes(lowerQuery))
        );
    }
    
    // ===== PUBLIC API =====
    return {
        // Data loading
        loadGraphData,
        
        // Filtering
        setEntityTypeFilter,
        setRelationshipTypeFilter,
        setSearchQuery,
        resetFilters,
        applyFilters,
        
        // Data access
        getFilteredData,
        getRawData,
        getStats,
        
        // Entity lookup
        findEntityById,
        findEntitiesByType,
        searchEntities,
        
        // Direct access (for debugging)
        get filteredNodes() { return filteredNodes; },
        get filteredLinks() { return filteredLinks; }
    };
})();