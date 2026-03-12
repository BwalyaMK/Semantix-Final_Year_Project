/**
 * Chat Page JavaScript
 * Handles Q&A with Cytoscape.js graph visualization
 */

let cy = null; // Cytoscape instance
let currentLearnedId = null;
let currentGraphData = null; // Store current graph data
let currentQuestion = null; // Store current question

document.addEventListener('DOMContentLoaded', () => {
  const questionInput = document.getElementById('questionInput');
  const askBtn = document.getElementById('askBtn');
  const includeGraph = document.getElementById('includeGraph');
  const answerSection = document.getElementById('answerSection');
  const answersContainer = document.getElementById('answersContainer');
  const loadingIndicator = document.getElementById('loadingIndicator');
  const graphContainer = document.getElementById('graphContainer');
  const relatedList = document.getElementById('relatedList');
  const thresholdSlider = document.getElementById('thresholdSlider');
  const thresholdValue = document.getElementById('thresholdValue');
  const feedbackModal = document.getElementById('feedbackModal');
  const expandGraphBtn = document.getElementById('expandGraphBtn');

  // Check for query parameter
  const urlParams = new URLSearchParams(window.location.search);
  const initialQuery = urlParams.get('q');
  if (initialQuery) {
    questionInput.value = initialQuery;
    askQuestion();
  }
  
  // Expand graph button handler
  expandGraphBtn.addEventListener('click', () => {
    if (currentGraphData && currentQuestion) {
      // Navigate to graph page with query parameter
      window.location.href = `/graph.html?q=${encodeURIComponent(currentQuestion)}`;
    }
  });

  // Handle threshold slider
  thresholdSlider.addEventListener('input', () => {
    const value = thresholdSlider.value / 100;
    thresholdValue.textContent = value.toFixed(2);
    if (cy) {
      filterGraphEdges(value);
    }
  });

  // Ask question
  async function askQuestion() {
    const question = questionInput.value.trim();
    if (!question) return;
    
    // Store current question
    currentQuestion = question;

    // Show loading
    loadingIndicator.classList.remove('hidden');
    answerSection.classList.add('hidden');
    expandGraphBtn.style.display = 'none';

    try {
      const response = await fetch('/api/chat/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: question,
          include_graph: includeGraph.checked,
          max_related: 15
        })
      });

      const data = await response.json();

      // Update intent display
      document.getElementById('detectedIntent').textContent = formatIntent(data.intent);
      document.getElementById('detectedIntent').className = `intent-badge ${getIntentClass(data.intent)}`;
      document.getElementById('confidenceInfo').textContent =
        `(${(data.confidence * 100).toFixed(1)}% confidence)`;

      // Show summary
      displaySummary(data.summary);

      // Show answers
      displayAnswers(data.answers);

      // Show graph if available
      if (data.graph && includeGraph.checked) {
        currentGraphData = data.graph; // Store graph data
        initGraph(data.graph);
        displayRelatedList(data.graph.related_rankings);
        // Show expand button
        expandGraphBtn.style.display = 'inline-block';
      }

      // Handle self-learning feedback
      if (data.learned && !data.is_confident) {
        currentLearnedId = data.learned.learned_id;
        showFeedbackModal(data.intent);
      }

      answerSection.classList.remove('hidden');

    } catch (error) {
      console.error('Error:', error);
      answersContainer.innerHTML = `
                <div class="placeholder">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>An error occurred. Please try again.</p>
                </div>
            `;
      answerSection.classList.remove('hidden');
    } finally {
      loadingIndicator.classList.add('hidden');
    }
  }

  // Display summary
  function displaySummary(summary) {
    const summaryText = document.getElementById('summaryText');
    const keyPoints = document.getElementById('keyPoints');

    if (!summary || !summary.text) {
      summaryText.textContent = 'No summary available.';
      keyPoints.innerHTML = '';
      return;
    }

    summaryText.textContent = summary.text;

    if (summary.key_points && summary.key_points.length > 0) {
      keyPoints.innerHTML = `
        <div class="key-points-header" style="font-size: 0.85rem; color: #64748b; margin-bottom: 0.5rem;">
          <i class="fas fa-key"></i> Key Findings:
        </div>
        ${summary.key_points.map((point, index) => `
          <div class="key-point">
            <span class="key-point-number">${index + 1}</span>
            <div class="key-point-content">
              <div class="key-point-text">${point.point}</div>
              <div class="key-point-source">Source: ${point.source}</div>
            </div>
          </div>
        `).join('')}
      `;
    } else {
      keyPoints.innerHTML = '';
    }
  }

  // Display answers
  function displayAnswers(answers) {
    if (!answers || answers.length === 0) {
      answersContainer.innerHTML = `
                <div class="placeholder">
                    <p>No matching papers found for your question.</p>
                </div>
            `;
      return;
    }

    answersContainer.innerHTML = answers.map((answer, index) => `
            <div class="answer-card">
                <span class="rank">${index + 1}</span>
                <a href="${answer.url || '#'}" target="_blank" class="title">
                    ${answer.title}
                </a>
                <div class="authors">${formatAuthors(answer.authors)}</div>
                <p class="abstract">${answer.abstract || 'No abstract available'}</p>
                <div class="footer">
                    <div class="similarity-score">
                        <i class="fas fa-chart-line"></i>
                        <span>Similarity: ${(answer.similarity_score * 100).toFixed(1)}%</span>
                    </div>
                    <a href="${answer.url || '#'}" target="_blank" class="btn btn-sm btn-outline">
                        <i class="fas fa-external-link-alt"></i> View Paper
                    </a>
                </div>
            </div>
        `).join('');
  }

  // Initialize Cytoscape graph
  function initGraph(graphData) {
    graphContainer.innerHTML = '';

    if (!graphData.nodes || graphData.nodes.length === 0) {
      graphContainer.innerHTML = `
                <div class="graph-placeholder">
                    <i class="fas fa-project-diagram"></i>
                    <p>No graph data available</p>
                </div>
            `;
      return;
    }

    cy = cytoscape({
      container: graphContainer,
      elements: [...graphData.nodes, ...graphData.edges],
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-wrap': 'wrap',
            'text-max-width': '100px',
            'font-size': '10px',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'background-color': '#94a3b8',
            'width': 30,
            'height': 30
          }
        },
        {
          selector: 'node.primary',
          style: {
            'background-color': '#6366f1',
            'width': 40,
            'height': 40,
            'font-weight': 'bold'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 'mapData(weight, 0, 1, 1, 5)',
            'line-color': '#cbd5e1',
            'opacity': 'mapData(weight, 0, 1, 0.3, 1)',
            'curve-style': 'bezier'
          }
        },
        {
          selector: ':selected',
          style: {
            'border-width': 3,
            'border-color': '#4f46e5'
          }
        }
      ],
      layout: {
        name: 'cose',
        animate: true,
        randomize: false,
        nodeRepulsion: 8000,
        idealEdgeLength: 100
      }
    });

    // Node click handler
    cy.on('tap', 'node', function (evt) {
      const node = evt.target;
      const data = node.data();
      showNodeDetails(data);
    });
  }

  // Filter graph edges by threshold
  function filterGraphEdges(threshold) {
    if (!cy) return;

    cy.edges().forEach(edge => {
      const weight = edge.data('weight');
      if (weight < threshold) {
        edge.style('display', 'none');
      } else {
        edge.style('display', 'element');
      }
    });
  }

  // Show node details (could add a details panel)
  function showNodeDetails(data) {
    console.log('Selected:', data);
    // Could show details in a panel
  }

  // Display related list
  function displayRelatedList(rankings) {
    if (!rankings || rankings.length === 0) {
      relatedList.innerHTML = '<p class="empty-state">No related papers found</p>';
      return;
    }

    relatedList.innerHTML = rankings.slice(0, 10).map((item, index) => `
            <div class="related-item ${item.is_primary ? 'primary' : ''}">
                <span class="title">${truncate(item.title, 60)}</span>
                <div class="sim-score">
                    <span>${index + 1}.</span>
                    <span>Similarity: ${(item.similarity * 100).toFixed(1)}%</span>
                </div>
            </div>
        `).join('');
  }

  // Show feedback modal
  function showFeedbackModal(inferredIntent) {
    feedbackModal.classList.remove('hidden');
    // Pre-select the inferred intent
    const radio = document.querySelector(`input[name="feedbackIntent"][value="${inferredIntent}"]`);
    if (radio) radio.checked = true;
  }

  // Event listeners
  askBtn.addEventListener('click', askQuestion);
  questionInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      askQuestion();
    }
  });

  // Feedback modal handlers
  document.getElementById('skipFeedback').addEventListener('click', () => {
    feedbackModal.classList.add('hidden');
    currentLearnedId = null;
  });

  document.getElementById('submitFeedback').addEventListener('click', async () => {
    const selectedIntent = document.querySelector('input[name="feedbackIntent"]:checked');
    if (!selectedIntent || !currentLearnedId) {
      feedbackModal.classList.add('hidden');
      return;
    }

    try {
      await fetch('/api/chat/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          learned_id: currentLearnedId,
          correct_intent: selectedIntent.value
        })
      });
    } catch (error) {
      console.error('Feedback error:', error);
    }

    feedbackModal.classList.add('hidden');
    currentLearnedId = null;
  });
});
