/**
 * Graph Page JavaScript
 * Full-page Cytoscape.js graph explorer
 */

let cy = null;
let currentGraphData = null;

document.addEventListener('DOMContentLoaded', () => {
  const graphQuery = document.getElementById('graphQuery');
  const buildGraphBtn = document.getElementById('buildGraphBtn');
  const cyContainer = document.getElementById('cyContainer');
  const loadingOverlay = document.getElementById('loadingOverlay');
  const edgeThreshold = document.getElementById('edgeThreshold');
  const thresholdDisplay = document.getElementById('thresholdDisplay');
  const layoutSelect = document.getElementById('layoutSelect');
  const paperDetails = document.getElementById('paperDetails');
  const relatedList = document.getElementById('relatedList');
  
  // Check for URL parameters (from search or chat page)
  const urlParams = new URLSearchParams(window.location.search);
  const queryParam = urlParams.get('q');
  const graphDataParam = urlParams.get('graphData');
  
  // Auto-load from URL parameter
  if (queryParam) {
    graphQuery.value = decodeURIComponent(queryParam);
    buildGraph();
  }
  
  // Load graph data passed from chat page
  if (graphDataParam) {
    try {
      const graphData = JSON.parse(decodeURIComponent(graphDataParam));
      currentGraphData = graphData;
      initGraph(graphData);
      updateStats(graphData.stats);
      if (graphData.related_rankings) {
        displayRelatedList(graphData.related_rankings);
      }
    } catch (error) {
      console.error('Error loading graph data:', error);
    }
  }

  // Toolbar buttons
  document.getElementById('zoomIn').addEventListener('click', () => cy && cy.zoom(cy.zoom() * 1.2));
  document.getElementById('zoomOut').addEventListener('click', () => cy && cy.zoom(cy.zoom() / 1.2));
  document.getElementById('fitGraph').addEventListener('click', () => cy && cy.fit());
  document.getElementById('resetGraph').addEventListener('click', () => {
    if (cy) {
      runLayout(layoutSelect.value);
    }
  });

  // Threshold slider
  edgeThreshold.addEventListener('input', () => {
    const value = edgeThreshold.value / 100;
    thresholdDisplay.textContent = value.toFixed(2);
    filterEdgesByThreshold(value);
  });

  // Layout selector
  layoutSelect.addEventListener('change', () => {
    if (cy) {
      runLayout(layoutSelect.value);
    }
  });

  // Build graph
  async function buildGraph() {
    const query = graphQuery.value.trim();
    if (!query) return;

    loadingOverlay.classList.remove('hidden');
    
    // Update URL without reloading page
    const newUrl = new URL(window.location);
    newUrl.searchParams.set('q', query);
    window.history.pushState({}, '', newUrl);

    try {
      const response = await fetch('/api/graph/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          max_related: 10,
          threshold: edgeThreshold.value / 100
        })
      });

      const data = await response.json();

      if (data.error) {
        showError(data.error);
        return;
      }

      currentGraphData = data.graph;
      initGraph(data.graph);
      updateStats(data.graph.stats);
      displayRelatedList(data.graph.related_rankings);

    } catch (error) {
      console.error('Error building graph:', error);
      showError('Failed to build graph. Please try again.');
    } finally {
      loadingOverlay.classList.add('hidden');
    }
  }

  // Initialize Cytoscape
  function initGraph(graphData) {
    // Clear placeholder
    cyContainer.innerHTML = '';

    if (!graphData.nodes || graphData.nodes.length === 0) {
      cyContainer.innerHTML = `
                <div class="graph-placeholder">
                    <i class="fas fa-project-diagram"></i>
                    <p>No results found for your query</p>
                </div>
            `;
      return;
    }

    cy = cytoscape({
      container: cyContainer,
      elements: [...graphData.nodes, ...graphData.edges],
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-wrap': 'wrap',
            'text-max-width': '120px',
            'font-size': '11px',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 5,
            'background-color': '#94a3b8',
            'width': 'mapData(similarity, 0, 1, 25, 50)',
            'height': 'mapData(similarity, 0, 1, 25, 50)',
            'border-width': 2,
            'border-color': '#64748b'
          }
        },
        {
          selector: 'node.primary',
          style: {
            'background-color': '#6366f1',
            'border-color': '#4f46e5',
            'width': 50,
            'height': 50,
            'font-weight': 'bold',
            'font-size': '12px'
          }
        },
        {
          selector: 'node.related',
          style: {
            'background-color': '#94a3b8'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 'mapData(weight, 0.5, 1, 1, 6)',
            'line-color': '#cbd5e1',
            'opacity': 'mapData(weight, 0.5, 1, 0.4, 1)',
            'curve-style': 'bezier'
          }
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 4,
            'border-color': '#f59e0b',
            'background-color': '#fbbf24'
          }
        },
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#f59e0b',
            'width': 4
          }
        }
      ],
      layout: {
        name: 'cose',
        animate: true,
        animationDuration: 500,
        nodeRepulsion: 10000,
        idealEdgeLength: 120,
        edgeElasticity: 100
      },
      minZoom: 0.2,
      maxZoom: 3
    });

    // Event handlers
    cy.on('tap', 'node', function (evt) {
      const node = evt.target;
      showPaperDetails(node.data());
    });

    cy.on('tap', function (evt) {
      if (evt.target === cy) {
        clearPaperDetails();
      }
    });

    // Double-click to expand
    cy.on('dbltap', 'node', function (evt) {
      const node = evt.target;
      expandNode(node.data().id);
    });
  }

  // Run layout
  function runLayout(layoutName) {
    if (!cy) return;

    const layouts = {
      cose: {
        name: 'cose',
        animate: true,
        nodeRepulsion: 10000,
        idealEdgeLength: 120
      },
      circle: {
        name: 'circle',
        animate: true
      },
      grid: {
        name: 'grid',
        animate: true
      },
      concentric: {
        name: 'concentric',
        animate: true,
        concentric: function (node) {
          return node.data('is_primary') ? 10 : 1;
        }
      }
    };

    cy.layout(layouts[layoutName] || layouts.cose).run();
  }

  // Filter edges by threshold
  function filterEdgesByThreshold(threshold) {
    if (!cy) return;

    cy.edges().forEach(edge => {
      const weight = edge.data('weight');
      if (weight < threshold) {
        edge.style('display', 'none');
      } else {
        edge.style('display', 'element');
      }
    });

    // Update edge count
    const visibleEdges = cy.edges().filter(e => e.style('display') !== 'none');
    document.getElementById('edgeCount').textContent = visibleEdges.length;
  }

  // Update stats
  function updateStats(stats) {
    document.getElementById('nodeCount').textContent = stats.total_nodes || 0;
    document.getElementById('edgeCount').textContent = stats.total_edges || 0;
    document.getElementById('primaryCount').textContent = stats.primary_count || 0;
    document.getElementById('relatedCount').textContent = stats.related_count || 0;
  }

  // Show paper details
  function showPaperDetails(data) {
    paperDetails.innerHTML = `
            <div class="paper-title">${data.title}</div>
            <div class="paper-authors">${formatAuthors(data.authors)}</div>
            ${data.year ? `<div class="paper-year">${data.year}</div>` : ''}
            <div class="paper-abstract">${truncate(data.abstract, 200) || 'No abstract'}</div>
            ${data.url ? `<a href="${data.url}" target="_blank" class="paper-link btn btn-sm btn-primary">
                <i class="fas fa-external-link-alt"></i> View Paper
            </a>` : ''}
        `;
  }

  // Clear paper details
  function clearPaperDetails() {
    paperDetails.innerHTML = '<p class="empty-state">Click a node to see details</p>';
  }

  // Display related list
  function displayRelatedList(rankings) {
    if (!rankings || rankings.length === 0) {
      relatedList.innerHTML = '<p class="empty-state">No related papers</p>';
      return;
    }

    relatedList.innerHTML = rankings.slice(0, 10).map((item, index) => `
            <div class="related-item ${item.is_primary ? 'primary' : ''}" 
                 onclick="highlightNode('${item.openalex_id}')">
                <span class="title">${truncate(item.title, 50)}</span>
                <div class="meta">
                    <span>#${index + 1}</span>
                    <span>${(item.similarity * 100).toFixed(0)}%</span>
                </div>
            </div>
        `).join('');
  }

  // Highlight node
  window.highlightNode = function (nodeId) {
    if (!cy) return;

    cy.nodes().unselect();
    const node = cy.getElementById(nodeId);
    if (node) {
      node.select();
      cy.animate({
        center: { eles: node },
        zoom: 1.5,
        duration: 300
      });
      showPaperDetails(node.data());
    }
  };

  // Expand node (fetch more related)
  async function expandNode(nodeId) {
    try {
      const existingIds = cy.nodes().map(n => n.id());

      const response = await fetch('/api/graph/expand', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          openalex_id: nodeId,
          query: graphQuery.value,
          existing_ids: existingIds,
          limit: 5
        })
      });

      const data = await response.json();

      if (data.new_nodes && data.new_nodes.length > 0) {
        // Add new elements
        cy.add([...data.new_nodes, ...data.new_edges]);

        // Re-run layout
        runLayout(layoutSelect.value);

        // Update stats
        document.getElementById('nodeCount').textContent = cy.nodes().length;
        document.getElementById('edgeCount').textContent = cy.edges().length;
      }

    } catch (error) {
      console.error('Error expanding node:', error);
    }
  }

  // Show error
  function showError(message) {
    cyContainer.innerHTML = `
            <div class="graph-placeholder">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${message}</p>
            </div>
        `;
  }

  // Event listeners
  buildGraphBtn.addEventListener('click', buildGraph);
  graphQuery.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') buildGraph();
  });
});
