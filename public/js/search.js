/**
 * Search Page JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('searchInput');
  const searchBtn = document.getElementById('searchBtn');
  const rerankToggle = document.getElementById('rerankToggle');
  const intentDisplay = document.getElementById('intentDisplay');
  const confidenceDisplay = document.getElementById('confidenceDisplay');
  const resultsInfo = document.getElementById('resultsInfo');
  const resultsList = document.getElementById('resultsList');

  // Handle search
  async function performSearch() {
    const query = searchInput.value.trim();
    if (!query) return;

    // Show loading
    resultsList.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>Searching...</p>
            </div>
        `;

    try {
      const response = await fetch('/api/search/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          rerank: rerankToggle.checked
        })
      });

      const data = await response.json();

      // Update intent display
      intentDisplay.textContent = formatIntent(data.intent);
      intentDisplay.className = `intent-badge ${getIntentClass(data.intent)}`;
      confidenceDisplay.textContent = `Confidence: ${(data.confidence * 100).toFixed(1)}%`;

      // Update results
      resultsInfo.textContent = `Found ${data.results.length} results for "${query}"`;

      if (data.results.length === 0) {
        resultsList.innerHTML = `
                    <div class="placeholder">
                        <i class="fas fa-search"></i>
                        <p>No results found for your query</p>
                    </div>
                `;
        return;
      }

      // Store query for graph navigation
      const currentQuery = query;
      
      resultsList.innerHTML = data.results.map(result => `
                <div class="result-card">
                    <a href="${result.url || '#'}" target="_blank" class="title">
                        ${result.title}
                    </a>
                    <div class="meta">
                        <span><i class="fas fa-users"></i> ${formatAuthors(result.authors)}</span>
                        ${result.publication_year ? `<span><i class="fas fa-calendar"></i> ${result.publication_year}</span>` : ''}
                        ${result.cited_by_count ? `<span><i class="fas fa-quote-right"></i> ${result.cited_by_count} citations</span>` : ''}
                    </div>
                    <p class="abstract">${truncate(result.abstract, 300) || 'No abstract available'}</p>
                    ${result.concepts && result.concepts.length > 0 ? `
                        <div class="concepts">
                            ${result.concepts.slice(0, 5).map(c => `
                                <span class="concept-tag">${c.name}</span>
                            `).join('')}
                        </div>
                    ` : ''}
                    ${result.similarity_score !== undefined ? `
                        <div class="similarity">
                            <span>Similarity:</span>
                            <div class="similarity-bar">
                                <div class="similarity-fill" style="width: ${result.similarity_score * 100}%"></div>
                            </div>
                            <span>${(result.similarity_score * 100).toFixed(1)}%</span>
                        </div>
                    ` : ''}
                </div>
            `).join('');
      
      // Add "View Graph" button after results
      const viewGraphBtn = document.createElement('div');
      viewGraphBtn.className = 'view-graph-section';
      viewGraphBtn.innerHTML = `
        <button class="btn btn-primary" onclick="window.location.href='/graph.html?q=${encodeURIComponent(currentQuery)}'">
          <i class="fas fa-project-diagram"></i> View Knowledge Graph for "${currentQuery}"
        </button>
      `;
      resultsList.appendChild(viewGraphBtn);

    } catch (error) {
      console.error('Search error:', error);
      resultsList.innerHTML = `
                <div class="placeholder">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>An error occurred while searching. Please try again.</p>
                </div>
            `;
    }
  }

  // Event listeners
  searchBtn.addEventListener('click', performSearch);
  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
  });

  // Handle intent filter radio buttons
  document.querySelectorAll('input[name="intent"]').forEach(radio => {
    radio.addEventListener('change', () => {
      // Could filter results by intent here
    });
  });
});
