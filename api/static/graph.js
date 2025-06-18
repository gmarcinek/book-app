(function(){
  const svg = d3.select('#graph');
  const tooltip = d3.select('#tooltip');
  const width = window.innerWidth;
  const height = window.innerHeight - document.getElementById('controls').offsetHeight;
  
  const sim = d3.forceSimulation()
    .force('link', d3.forceLink().id(d => d.id).distance(d => d.relation_type === 'contains' ? 50 : 80))
    .force('charge', d3.forceManyBody().strength(-200))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => d.uiType === 'entity' ? 8 : 5))
    .force('x', d3.forceX(width / 2).strength(0.05))
    .force('y', d3.forceY(height / 2).strength(0.06));

  let showChunks = false;
  let pending;
  let availableTypes = [];
  let selectedTypes = [];

  /* ---------- Dropdown functionality ---------- */
  function initDropdown() {
    const dropdownBtn = document.getElementById('typeDropdownBtn');
    const dropdownMenu = document.getElementById('typeDropdownMenu');
    const dropdownText = document.getElementById('typeDropdownText');

    // Toggle dropdown
    dropdownBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = dropdownMenu.classList.contains('open');
      
      if (isOpen) {
        closeDropdown();
      } else {
        openDropdown();
      }
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.dropdown')) {
        closeDropdown();
      }
    });

    function openDropdown() {
      dropdownMenu.classList.add('open');
      dropdownBtn.classList.add('open');
    }

    function closeDropdown() {
      dropdownMenu.classList.remove('open');
      dropdownBtn.classList.remove('open');
    }

    // Handle checkbox changes
    dropdownMenu.addEventListener('change', (e) => {
      const checkbox = e.target;
      const value = checkbox.value;
      
      if (value === '') {
        // "Wszystkie typy" checkbox
        if (checkbox.checked) {
          selectedTypes = [];
          // Uncheck all other checkboxes
          dropdownMenu.querySelectorAll('input[type="checkbox"]:not([value=""])').forEach(cb => {
            cb.checked = false;
          });
        }
      } else {
        // Specific type checkbox
        if (checkbox.checked) {
          if (!selectedTypes.includes(value)) {
            selectedTypes.push(value);
          }
          // Uncheck "Wszystkie typy"
          dropdownMenu.querySelector('input[value=""]').checked = false;
        } else {
          selectedTypes = selectedTypes.filter(t => t !== value);
          // If no types selected, check "Wszystkie typy"
          if (selectedTypes.length === 0) {
            dropdownMenu.querySelector('input[value=""]').checked = true;
          }
        }
      }
      
      updateDropdownText();
      schedule(300);
    });

    function updateDropdownText() {
      if (selectedTypes.length === 0) {
        dropdownText.textContent = 'Wszystkie typy';
      } else if (selectedTypes.length === 1) {
        dropdownText.textContent = selectedTypes[0];
      } else {
        dropdownText.textContent = `${selectedTypes.length} typów`;
      }
    }
  }

  /* ---------- Helpers ---------- */
  function normaliseNode(n) {
    const raw = (n.type || 'UNKNOWN').toUpperCase();
    const ui = raw === 'CHUNK' ? 'chunk' : 'entity';
    const d = n.data || {};
    d.name = d.name || n.name || n.id;
    d.aliases = d.aliases || n.aliases || [];
    d.confidence = d.confidence ?? n.confidence ?? 0;
    d.rawType = raw;
    d.text = d.text || n.description || '';
    return { ...n, uiType: ui, data: d };
  }

  function getRelationshipColor(relType) {
    const colors = {
      'contains': '#10b981',
      'similar_to': '#f59e0b',
      'co_occurs': '#8b5cf6',
      'located_in': '#ef4444',
      'authored_by': '#06b6d4',
      'mentioned_with': '#84cc16'
    };
    return colors[relType] || '#374151';
  }

  function getRelationshipWidth(confidence) {
    return Math.max(2, Math.min(5, confidence * 4));
  }

  function showTip(evt, d) {
    let html;
    if (d.uiType === 'entity') {
      html = `<strong>${d.data.name}</strong><br>Typ: ${d.data.rawType}<br>Conf: ${d.data.confidence.toFixed(2)}<br>Alias: ${d.data.aliases.slice(0, 3).join(', ') || '—'}`;
    } else if (d.uiType === 'chunk') {
      html = `<strong>Chunk</strong><br>${d.data.text.slice(0, 120)}…`;
    } else if (d.relation_type) {
      html = `<strong>${d.relation_type}</strong><br>Confidence: ${(d.confidence || 1).toFixed(2)}<br>Od: ${d.source.data?.name || d.source.id}<br>Do: ${d.target.data?.name || d.target.id}`;
    }
    tooltip.style('display', 'block').html(html);
    const rect = tooltip.node().getBoundingClientRect();
    tooltip.style('left', (evt.pageX - rect.width / 2) + 'px').style('top', (evt.pageY - rect.height - 10) + 'px');
  }

  const hideTip = () => tooltip.style('display', 'none');

  function dragStarted(e, d) {
    if (!e.active) sim.alphaTarget(.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(e, d) {
    d.fx = e.x;
    d.fy = e.y;
  }

  function dragEnded(e, d) {
    if (!e.active) sim.alphaTarget(0);
    d.fx = d.fy = null;
  }

  function getActiveRelationFilters() {
    const filters = [];
    ['contains', 'similar_to', 'co_occurs', 'located_in', 'authored_by', 'mentioned_with'].forEach(type => {
      if (document.getElementById(`filter-${type}`).checked) filters.push(type);
    });
    return filters;
  }

  function render(nodes, edges) {
    svg.selectAll('*').remove();
    
    // Filter edges by active relation types
    const activeRelations = getActiveRelationFilters();
    const filteredEdges = edges.filter(e => activeRelations.includes(e.relation_type) || !e.relation_type);
    
    const link = svg.append('g').selectAll('line').data(filteredEdges).enter().append('line')
      .attr('class', d => `link link-${d.relation_type || 'default'}`)
      .attr('stroke', d => getRelationshipColor(d.relation_type))
      .attr('stroke-width', d => getRelationshipWidth(d.confidence || 1))
      .on('mouseover', showTip).on('mouseout', hideTip);
    
    const linkLabel = svg.append('g').selectAll('text').data(filteredEdges.filter(d => d.relation_type !== 'contains'))
      .enter().append('text').attr('class', 'link-label')
      .text(d => d.relation_type?.replace('_', ' ') || '')
      .on('mouseover', showTip).on('mouseout', hideTip);
    
    const node = svg.append('g').selectAll('circle').data(nodes).enter().append('circle')
      .attr('class', d => d.uiType === 'entity' ? 'node-entity' : 'node-chunk')
      .attr('r', d => d.uiType === 'entity' ? 6 : 3)
      .call(d3.drag().on('start', dragStarted).on('drag', dragged).on('end', dragEnded))
      .on('mouseover', showTip).on('mouseout', hideTip)
      .on('click', (e, d) => d.uiType === 'entity' && window.open(`/entities/${d.id}`, '_blank'));
    
    const label = svg.append('g').selectAll('text').data(nodes.filter(d => d.uiType === 'entity'))
      .enter().append('text').attr('font-size', '14px').attr('text-anchor', 'middle').attr('fill', '#374151')
      .attr('font-weight', '500')
      .text(d => d.data.name.length > 18 ? d.data.name.slice(0, 15) + '…' : d.data.name);
    
    sim.nodes(nodes).on('tick', () => {
      link.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y);
      linkLabel.attr('x', d => (d.source.x + d.target.x) / 2).attr('y', d => (d.source.y + d.target.y) / 2);
      node.attr('cx', d => d.x = Math.max(15, Math.min(width - 15, d.x))).attr('cy', d => d.y = Math.max(15, Math.min(height - 15, d.y)));
      label.attr('x', d => d.x).attr('y', d => d.y + 18);
    });
    
    sim.force('link').links(filteredEdges);
    sim.alpha(1).restart();
  }

  function updateTypeDropdown(entityTypes) {
    const dropdownMenu = document.getElementById('typeDropdownMenu');
    
    // Keep "Wszystkie typy" option and add new types with counts
    const allTypesOption = '<label class="dropdown-item"><input type="checkbox" value="" checked> <span class="type-name">Wszystkie typy</span></label>';
    
    const typeOptions = entityTypes.map(({type, count}) => 
      `<label class="dropdown-item">
        <input type="checkbox" value="${type}" ${selectedTypes.includes(type) ? 'checked' : ''}> 
        <span class="type-name">${type}</span>
        <span class="type-count">${count}</span>
      </label>`
    ).join('');
    
    dropdownMenu.innerHTML = allTypesOption + typeOptions;
  }

  async function loadEntityTypes() {
    try {
      const res = await fetch('/entity-types');
      const json = await res.json();
      
      if (json.entity_types && json.entity_types.length > 0) {
        updateTypeDropdown(json.entity_types);
        return json.entity_types.map(et => et.type);
      }
      return [];
    } catch (err) {
      console.warn('Failed to load entity types:', err);
      return [];
    }
  }

  /* ---------- Load ---------- */
  async function loadGraph() {
    document.getElementById('reloadBtn').disabled = true;
    try {
      const typeParam = selectedTypes.length ? selectedTypes.join(',') : '';
      const max = document.getElementById('maxNodes').value || 200;
      showChunks = document.getElementById('chunksToggle').checked;
      
      const url = `/graph?max_nodes=${max}${typeParam ? `&entity_types=${typeParam}` : ''}`;
      const res = await fetch(url);
      const json = await res.json();
      
      // Load entity types on first load or when types might have changed
      if (availableTypes.length === 0) {
        const newTypes = await loadEntityTypes();
        availableTypes = newTypes;
      }
      
      let nodes = json.nodes.map(normaliseNode);
      if (!showChunks) nodes = nodes.filter(n => n.uiType === 'entity');
      
      const q = document.getElementById('searchInput').value.trim().toLowerCase();
      if (q) {
        const keep = new Set();
        nodes.forEach(n => {
          if (n.data.name.toLowerCase().includes(q)) {
            keep.add(n.id);
          }
        });
        json.edges.forEach(e => {
          if (keep.has(e.source) || keep.has(e.target)) {
            keep.add(e.source);
            keep.add(e.target);
          }
        });
        nodes = nodes.filter(n => keep.has(n.id));
      }
      
      const ids = new Set(nodes.map(n => n.id));
      const edges = json.edges.filter(e => ids.has(e.source) && ids.has(e.target));
      
      render(nodes, edges);
      document.getElementById('stats').textContent = `n=${nodes.length} | e=${edges.length}`;
    } catch (err) {
      console.error(err);
      alert('Błąd ładowania grafu');
    }
    document.getElementById('reloadBtn').disabled = false;
  }

  /* ---------- Debounce wrapper ---------- */
  function schedule(ms = 500) {
    clearTimeout(pending);
    pending = setTimeout(loadGraph, ms);
  }

  /* ---------- Bindings ---------- */
  document.getElementById('reloadBtn').onclick = loadGraph;
  document.getElementById('chunksToggle').onchange = loadGraph;
  
  // Relation filter checkboxes
  ['contains', 'similar_to', 'co_occurs', 'located_in', 'authored_by', 'mentioned_with'].forEach(type => {
    document.getElementById(`filter-${type}`).onchange = () => schedule(100);
  });
  
  ['maxNodes', 'searchInput'].forEach(id => {
    const el = document.getElementById(id);
    el.addEventListener('input', () => schedule(id === 'searchInput' ? 300 : 600));
  });

  /* ---------- First paint ---------- */
  initDropdown();
  loadGraph();
})();