// api/static/graph-render.js
// Graph Rendering Engine - D3.js Visualization with GraphDrawer integration

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
        const config = window.GraphConfig?.SIMULATION;
        
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
            .force('box', forceBox()
                .x0(80)           // Lewy margines 80px
                .y0(110)          // Górny margines 110px (miejsce na toolbar)
                .x1(width - 80)   // Prawy margines 80px
                .y1(height - 80)  // Dolny margines 80px
                .strength(0.1)    // Siła "ścian"
            )
            .alphaDecay(config.alphaDecay)
            .on('tick', updatePositions);
    }
    
    // Custom force function - delikatniejsze invisible walls
    function forceBox() {
        let x0 = 0, y0 = 0, x1 = 100, y1 = 100, strength = 0.1;
        
        function force() {
            const nodes = simulation.nodes();
            
            for (let i = 0, n = nodes.length; i < n; ++i) {
                const node = nodes[i];
                
                // Delikatne odbicie od ścian
                if (node.x < x0) {
                    node.vx += (x0 - node.x) * strength;
                }
                else if (node.x > x1) {
                    node.vx += (x1 - node.x) * strength;
                }
                
                if (node.y < y0) {
                    node.vy += (y0 - node.y) * strength;
                }
                else if (node.y > y1) {
                    node.vy += (y1 - node.y) * strength;
                }
            }
        }
        
        // API dla konfiguracji
        force.x0 = function(_) { return arguments.length ? (x0 = +_, force) : x0; };
        force.y0 = function(_) { return arguments.length ? (y0 = +_, force) : y0; };
        force.x1 = function(_) { return arguments.length ? (x1 = +_, force) : x1; };
        force.y1 = function(_) { return arguments.length ? (y1 = +_, force) : y1; };
        force.strength = function(_) { return arguments.length ? (strength = +_, force) : strength; };
        
        return force;
    }
    
    // ===== RENDERING =====
    function render(data) {
        console.log('🎨 Rendering graph...');
        console.log('🎨 Nodes to render:', data.nodes.length);
        console.log('🎨 Links to render:', data.links.length);
        
        if (data.nodes.length === 0) {
            // Clear everything and show empty state
            container.selectAll('*').remove();
            showEmptyState();
            simulation.nodes([]);
            simulation.force('link').links([]);
            return;
        }
        
        // Bardziej delikatne preservation - mniej agresywne
        const currentNodes = simulation.nodes();
        const nodeMap = new Map(currentNodes.map(n => [n.id, n]));
        
        // Create updated nodes array - mniej restrictive preservation
        const updatedNodes = data.nodes.map(filterNode => {
            const existingNode = nodeMap.get(filterNode.id);
            if (existingNode) {
                // Preserve tylko podstawowe simulation properties
                const preservedProps = ['x', 'y', 'vx', 'vy', 'index'];
                preservedProps.forEach(prop => {
                    if (existingNode[prop] !== undefined) {
                        filterNode[prop] = existingNode[prop];
                    }
                });
                // Nie zachowuj fx, fy - pozwól na naturalne pozycjonowanie
                return filterNode;
            } else {
                // New node - will get initial position from simulation
                return { ...filterNode };
            }
        });
        
        // Update links with proper node references
        const updatedLinks = data.links.map(link => {
            const sourceNode = updatedNodes.find(n => n.id === (link.source.id || link.source));
            const targetNode = updatedNodes.find(n => n.id === (link.target.id || link.target));
            
            return {
                ...link,
                source: sourceNode,
                target: targetNode
            };
        }).filter(link => link.source && link.target); // Remove broken links
        
        // Update simulation BEFORE rendering
        simulation.nodes(updatedNodes);
        simulation.force('link').links(updatedLinks);
        
        // Clear and re-render visual elements
        container.selectAll('*').remove();
        
        // Render links first (behind nodes)
        renderLinks(updatedLinks);
        
        // Render nodes
        renderNodes(updatedNodes);
        
        // Bardziej płynny restart
        if (currentNodes.length === 0) {
            // First render - full start
            simulation.alpha(1).restart();
        } else {
            // Filter update - większa energia dla płynności
            simulation.alpha(0.3).restart(); // Zwiększone z 0.1 do 0.3
        }
        
        console.log('✅ Graph rendered successfully');
    }
    
    function renderLinks(links) {
        const linkSelection = container.selectAll('.relationship-line')
            .data(links, d => `${d.source.id}-${d.target.id}-${d.type}`);
        
        const linkEnter = linkSelection.enter()
            .append('line')
            .attr('class', 'relationship-line')
            .attr('stroke-width', d => Math.max(1, d.confidence * 3))
            .style('stroke', d => {
                // Get source node color and dim it
                const sourceNode = d.source;
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
            .duration(300)
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
                event.stopPropagation(); // Prevent event bubbling
                console.log('🔍 Node clicked:', d);
                
                // Hide tooltip if visible
                if (window.GraphInteractions) {
                    window.GraphInteractions.hideTooltip();
                }
                
                // Show entity drawer using new GraphDrawer module
                if (window.GraphDrawer) {
                    window.GraphDrawer.showEntity(d);
                } else {
                    console.warn('⚠️ GraphDrawer module not available');
                }
            });
        
        // Animate entrance
        nodeEnter.selectAll('circle, text')
            .transition()
            .duration(300)
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
        // Używamy config alphaTarget dla spójności
        if (!event.active) simulation.alphaTarget(window.GraphConfig?.SIMULATION?.alphaTarget || 0.3).restart();
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
    function showEmptyState() {
        container.append('text')
            .attr('class', 'empty-state')
            .attr('x', width / 2)
            .attr('y', height / 2)
            .style('text-anchor', 'middle')
            .style('font-size', '18px')
            .style('fill', '#9ca3af')
            .text('Brak danych do wyświetlenia');
    }
    
    function handleResize() {
        const graphContainer = document.getElementById('graph-container');
        width = graphContainer.clientWidth;
        height = graphContainer.clientHeight;
        
        svg.attr('width', width).attr('height', height);
        
        // Update center force
        simulation.force('center', d3.forceCenter(width / 2, height / 2));
        
        // Update box boundaries
        simulation.force('box')
            .x0(80)
            .y0(110) 
            .x1(width - 80)
            .y1(height - 80);
        
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