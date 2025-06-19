// api/static/graph-render.js
// Graph Rendering Engine - D3.js Visualization

window.GraphRender = (function() {
    'use strict';
    
    // ===== STATE =====
    let svg, container, simulation;
    let width, height;
    let transform = d3.zoomIdentity;
    
    // ===== INITIALIZATION =====
    function initialize() {
        console.log('🎨 Initializing graph renderer...');
        
        svg = d3.select('#graph-svg');
        
        // Get container dimensions
        const graphContainer = document.getElementById('graph-container');
        width = graphContainer.clientWidth;
        height = graphContainer.clientHeight;
        
        svg.attr('width', width).attr('height', height);
        
        // Setup zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', handleZoom);
        
        svg.call(zoom);
        
        // Create main container group
        container = svg.append('g').attr('class', 'graph-container');
        
        // Setup simulation
        setupSimulation();
        
        console.log('✅ Graph renderer initialized');
        return true;
    }
    
    function setupSimulation() {
        const config = window.GraphConfig?.SIMULATION || {
            linkDistance: 100,
            linkStrength: 0.3,
            chargeStrength: -400,
            centerStrength: 0.1,
            collisionRadius: 25,
            alphaDecay: 0.01
        };
        
        simulation = d3.forceSimulation()
            .force('link', d3.forceLink()
                .id(d => d.id)
                .distance(config.linkDistance)
                .strength(config.linkStrength)
            )
            .force('charge', d3.forceManyBody()
                .strength(config.chargeStrength)
            )
            .force('center', d3.forceCenter(width / 2, height / 2)
                .strength(config.centerStrength)
            )
            .force('collision', d3.forceCollide()
                .radius(config.collisionRadius)
            )
            .alphaDecay(config.alphaDecay)
            .on('tick', updatePositions);
    }
    
    // ===== RENDERING =====
    function render(data) {
        console.log('🎨 Rendering graph...');
        console.log('🎨 Nodes to render:', data.nodes.length);
        console.log('🎨 Links to render:', data.links.length);
        
        // Clear existing elements
        container.selectAll('*').remove();
        
        if (data.nodes.length === 0) {
            showEmptyState();
            return;
        }
        
        // Render links first (so they appear behind nodes)
        renderLinks(data.links);
        
        // Render nodes
        renderNodes(data.nodes);
        
        // Update simulation
        simulation.nodes(data.nodes);
        simulation.force('link').links(data.links);
        simulation.alpha(1).restart();
        
        console.log('✅ Graph rendered successfully');
    }
    
    function renderLinks(links) {
        const linkSelection = container.selectAll('.relationship-line')
            .data(links, d => `${d.source.id || d.source}-${d.target.id || d.target}-${d.type}`);
        
        const linkEnter = linkSelection.enter()
            .append('line')
            .attr('class', 'relationship-line')
            .attr('stroke-width', d => Math.max(1, d.confidence * 3))
            .style('stroke', d => {
                // Get source node color and dim it - FIXED: handle both ID strings and objects
                let sourceId = d.source.id || d.source;
                const sourceNode = findNodeInCurrentData(sourceId);
                if (sourceNode && window.GraphConfig) {
                    return window.GraphConfig.getDimmedEntityColor(sourceNode.type, 0.4);
                }
                return '#6b7280';
            })
            .style('opacity', 0);
        
        // Add interactions
        linkEnter
            .on('mouseover', (event, d) => {
                if (window.GraphInteractions) {
                    window.GraphInteractions.showRelationshipTooltip(event, d);
                }
            })
            .on('mouseout', () => {
                if (window.GraphInteractions) {
                    window.GraphInteractions.hideTooltip();
                }
            });
        
        // Animate entrance
        linkEnter
            .transition()
            .duration(500)
            .style('opacity', 0.7);
    }
    
    function renderNodes(nodes) {
        const nodeSelection = container.selectAll('.entity-group')
            .data(nodes, d => d.id);
        
        const nodeEnter = nodeSelection.enter()
            .append('g')
            .attr('class', 'entity-group');
        
        // Node circles
        nodeEnter.append('circle')
            .attr('class', 'entity-node')
            .attr('r', window.GraphConfig?.VISUAL?.nodeRadius || 12)
            .style('fill', d => window.GraphConfig?.getEntityColor(d.type) || '#9ca3af')
            .style('stroke', d => window.GraphConfig?.getEntityColor(d.type) || '#9ca3af')
            .style('opacity', 0);
        
        // Node labels
        nodeEnter.append('text')
            .attr('class', 'entity-label')
            .attr('dy', (window.GraphConfig?.VISUAL?.nodeRadius || 12) + 20)
            .style('font-size', `${window.GraphConfig?.VISUAL?.labelFontSize || 16}px`)
            .text(d => {
                const maxLength = 15;
                const truncate = window.GraphConfig?.truncateText || ((text, max) => 
                    text?.length > max ? text.slice(0, max) + '...' : text || '');
                return truncate(d.name, maxLength);
            })
            .style('opacity', 0);
        
        // Add interactions
        nodeEnter
            .call(d3.drag()
                .on('start', dragStarted)
                .on('drag', dragged)
                .on('end', dragEnded))
            .on('mouseover', (event, d) => {
                if (window.GraphInteractions) {
                    window.GraphInteractions.showEntityTooltip(event, d);
                }
            })
            .on('mouseout', () => {
                if (window.GraphInteractions) {
                    window.GraphInteractions.hideTooltip();
                }
            })
            .on('click', (event, d) => {
                console.log('🔍 Node clicked:', d);
                // Could implement entity details view here
            });
        
        // Animate entrance
        nodeEnter.selectAll('circle, text')
            .transition()
            .duration(500)
            .style('opacity', 1);
    }
    
    function updatePositions() {
        // Update link positions
        container.selectAll('.relationship-line')
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        // Update node positions
        container.selectAll('.entity-group')
            .attr('transform', d => `translate(${d.x}, ${d.y})`);
    }
    
    // ===== INTERACTIONS =====
    function handleZoom(event) {
        transform = event.transform;
        container.attr('transform', transform);
    }
    
    function dragStarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
        if (window.GraphInteractions) {
            window.GraphInteractions.hideTooltip();
        }
    }
    
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    function dragEnded(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
    
    // ===== UTILITIES =====
    function findNodeById(id) {
        if (window.GraphData) {
            return window.GraphData.findEntityById(id);
        }
        return null;
    }
    
    function findNodeInCurrentData(id) {
        // First try to find in current filtered data
        if (window.GraphData && window.GraphData.filteredNodes) {
            const node = window.GraphData.filteredNodes.find(n => n.id === id);
            if (node) return node;
        }
        
        // Fallback to global search
        return findNodeById(id);
    }
    
    function showEmptyState() {
        container.append('text')
            .attr('class', 'empty-state')
            .attr('x', width / 2)
            .attr('y', height / 2)
            .text('Brak danych do wyświetlenia');
    }
    
    function handleResize() {
        const graphContainer = document.getElementById('graph-container');
        width = graphContainer.clientWidth;
        height = graphContainer.clientHeight;
        
        svg.attr('width', width).attr('height', height);
        simulation.force('center', d3.forceCenter(width / 2, height / 2));
        simulation.alpha(0.3).restart();
    }
    
    // ===== PUBLIC API =====
    return {
        initialize,
        render,
        handleResize,
        
        // Direct access for debugging
        get simulation() { return simulation; },
        get container() { return container; },
        get svg() { return svg; }
    };
})();