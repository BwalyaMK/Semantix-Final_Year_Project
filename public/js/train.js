/**
 * Training Page JavaScript
 */

let currentPage = 1;

document.addEventListener('DOMContentLoaded', () => {
  loadTrainingData();
  loadLearnedData();
  loadStats();

  // Add example form
  document.getElementById('addExampleForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const question = document.getElementById('questionInput').value.trim();
    const intent = document.getElementById('intentSelect').value;

    if (!question || !intent) {
      alert('Please enter both question and intent');
      return;
    }

    try {
      const response = await fetch('/api/train/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, intent })
      });

      const data = await response.json();

      if (data.success) {
        document.getElementById('questionInput').value = '';
        document.getElementById('intentSelect').value = '';
        loadTrainingData();
        loadStats();
      } else {
        alert(data.error || 'Failed to add example');
      }
    } catch (error) {
      console.error('Error:', error);
    }
  });

  // File upload
  const uploadArea = document.getElementById('uploadArea');
  const csvFile = document.getElementById('csvFile');
  const browseBtn = document.getElementById('browseBtn');

  browseBtn.addEventListener('click', (e) => {
    e.preventDefault();
    csvFile.click();
  });

  uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
  });

  uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
  });

  uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  });

  csvFile.addEventListener('change', () => {
    if (csvFile.files[0]) {
      uploadFile(csvFile.files[0]);
    }
  });

  // Retrain button
  document.getElementById('retrainBtn').addEventListener('click', async () => {
    if (!confirm('Retrain the classifier with all current training data?')) return;

    try {
      const response = await fetch('/api/train/retrain', { method: 'POST' });
      const data = await response.json();

      if (data.success) {
        alert(`Model retrained successfully!\nSamples: ${data.training_samples}\nCV Score: ${data.cv_score ? (data.cv_score * 100).toFixed(1) + '%' : 'N/A'}`);
        loadStats();
      } else {
        alert(data.error || 'Failed to retrain');
      }
    } catch (error) {
      console.error('Error:', error);
    }
  });

  // Export button
  document.getElementById('exportBtn').addEventListener('click', () => {
    window.location.href = '/api/train/export?format=csv';
  });

  // Promote learned
  document.getElementById('promoteLearned').addEventListener('click', async () => {
    if (!confirm('Promote verified learned examples to training data and retrain?')) return;

    try {
      const response = await fetch('/api/train/learned/promote', { method: 'POST' });
      const data = await response.json();

      if (data.success) {
        alert('Learned data promoted and model retrained');
        loadTrainingData();
        loadLearnedData();
        loadStats();
      }
    } catch (error) {
      console.error('Error:', error);
    }
  });

  // Test classifier
  document.getElementById('testBtn').addEventListener('click', async () => {
    const query = document.getElementById('testInput').value.trim();
    if (!query) return;

    try {
      const response = await fetch('/api/search/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });

      const data = await response.json();

      const testResult = document.getElementById('testResult');
      testResult.classList.remove('hidden');
      testResult.innerHTML = `
                <div class="intent">
                    <span class="intent-badge ${getIntentClass(data.intent)}">${formatIntent(data.intent)}</span>
                </div>
                <div class="confidence">Confidence: ${(data.confidence * 100).toFixed(1)}%</div>
                <div class="all-probs" style="margin-top: 0.5rem; font-size: 0.75rem; color: #666;">
                    ${Object.entries(data.all_probabilities).map(([k, v]) =>
        `${formatIntent(k)}: ${(v * 100).toFixed(1)}%`
      ).join(' | ')}
                </div>
            `;
    } catch (error) {
      console.error('Error:', error);
    }
  });
});

// Load training data
async function loadTrainingData(page = 1) {
  currentPage = page;

  try {
    const response = await fetch(`/api/train/data?page=${page}&per_page=20`);
    const data = await response.json();

    const tbody = document.getElementById('trainingData');

    if (!data.examples || data.examples.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No training data yet</td></tr>';
      return;
    }

    tbody.innerHTML = data.examples.map(ex => `
            <tr>
                <td>${truncate(ex.question, 80)}</td>
                <td><span class="intent-badge ${getIntentClass(ex.intent)}">${formatIntent(ex.intent)}</span></td>
                <td>${ex.source}</td>
                <td>
                    <button class="action-btn delete" onclick="deleteExample(${ex.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');

    // Update pagination
    updatePagination(data.total, data.pages, page);

  } catch (error) {
    console.error('Error:', error);
  }
}

// Load learned data
async function loadLearnedData() {
  try {
    const response = await fetch('/api/train/learned');
    const data = await response.json();

    const tbody = document.getElementById('learnedData');

    if (!data.examples || data.examples.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No self-learned data yet</td></tr>';
      return;
    }

    tbody.innerHTML = data.examples.map(ex => `
            <tr>
                <td>${truncate(ex.query, 60)}</td>
                <td><span class="intent-badge ${getIntentClass(ex.inferred_intent)}">${formatIntent(ex.inferred_intent)}</span></td>
                <td>${(ex.confidence * 100).toFixed(1)}%</td>
                <td>${ex.verified ?
        '<span class="verified-badge"><i class="fas fa-check"></i> Yes</span>' :
        '<span class="pending-badge">Pending</span>'
      }</td>
                <td>
                    <button class="action-btn verify" onclick="verifyLearned(${ex.id})">
                        <i class="fas fa-check"></i>
                    </button>
                </td>
            </tr>
        `).join('');

  } catch (error) {
    console.error('Error:', error);
  }
}

// Load stats
async function loadStats() {
  try {
    const response = await fetch('/api/train/stats');
    const data = await response.json();

    // Training stats
    document.getElementById('totalExamples').textContent = data.training.total;
    document.getElementById('modelTrained').textContent = data.training.classifier.trained ? 'Yes' : 'No';

    // Intent breakdown
    const breakdown = document.getElementById('intentBreakdown');
    const intentEntries = Object.entries(data.training.by_intent);

    if (intentEntries.length === 0 || intentEntries.every(([_, count]) => count === 0)) {
        breakdown.innerHTML = '<div class="intent-breakdown-empty">No training data yet</div>';
    } else {
        const maxCount = Math.max(...Object.values(data.training.by_intent));

        breakdown.innerHTML = intentEntries
            .filter(([_, count]) => count > 0)  // Only show intents with data
            .sort((a, b) => b[1] - a[1])  // Sort by count descending
            .map(([intent, count]) => `
                <div class="intent-bar ${intent}">
                    <span class="intent-label" title="${formatIntent(intent)}">${formatIntent(intent)}</span>
                    <div class="bar">
                        <div class="bar-fill" style="width: ${maxCount > 0 ? (count / maxCount * 100) : 0}%"></div>
                    </div>
                    <span class="count">${count}</span>
                </div>
            `).join('');
    }

    // Learning stats
    document.getElementById('learnedCount').textContent = data.learning.total_learned;
    document.getElementById('verifiedCount').textContent = data.learning.verified;
    document.getElementById('pendingCount').textContent = data.learning.pending;

  } catch (error) {
    console.error('Error:', error);
  }
}

// Upload file
async function uploadFile(file) {
  const status = document.getElementById('uploadStatus');
  status.classList.remove('hidden');
  status.className = 'upload-status';
  status.textContent = 'Processing...';

  try {
    let examples = [];

    if (file.name.endsWith('.json')) {
      const text = await file.text();
      examples = JSON.parse(text);
    } else if (file.name.endsWith('.csv')) {
      const text = await file.text();
      const lines = text.trim().split('\n');
      const headers = lines[0].split(',').map(h => h.trim().toLowerCase());

      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        examples.push({
          question: values[headers.indexOf('question')]?.trim(),
          intent: values[headers.indexOf('intent')]?.trim()
        });
      }
    }

    const response = await fetch('/api/train/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ examples })
    });

    const data = await response.json();

    status.classList.add('success');
    status.textContent = `Added: ${data.added}, Updated: ${data.updated}${data.errors.length > 0 ? `, Errors: ${data.errors.length}` : ''}`;

    loadTrainingData();
    loadStats();

  } catch (error) {
    status.classList.add('error');
    status.textContent = 'Error processing file: ' + error.message;
  }
}

// Delete example
window.deleteExample = async function (id) {
  if (!confirm('Delete this training example?')) return;

  try {
    const response = await fetch(`/api/train/data/${id}`, { method: 'DELETE' });
    const data = await response.json();

    if (data.success) {
      loadTrainingData(currentPage);
      loadStats();
    }
  } catch (error) {
    console.error('Error:', error);
  }
};

// Verify learned
window.verifyLearned = async function (id) {
  const intent = prompt('Enter correct intent (or leave empty to confirm current):');

  try {
    const response = await fetch(`/api/train/learned/${id}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ correct_intent: intent || undefined })
    });

    const data = await response.json();

    if (data.success) {
      loadLearnedData();
      loadStats();
    } else {
      alert(data.error || 'Failed to verify');
    }
  } catch (error) {
    console.error('Error:', error);
  }
};

// Update pagination
function updatePagination(total, pages, current) {
  const pagination = document.getElementById('pagination');

  if (pages <= 1) {
    pagination.innerHTML = '';
    return;
  }

  let html = '';

  if (current > 1) {
    html += `<button onclick="loadTrainingData(${current - 1})">Prev</button>`;
  }

  for (let i = 1; i <= pages; i++) {
    if (i === current) {
      html += `<button class="active">${i}</button>`;
    } else if (i === 1 || i === pages || Math.abs(i - current) <= 2) {
      html += `<button onclick="loadTrainingData(${i})">${i}</button>`;
    } else if (Math.abs(i - current) === 3) {
      html += `<button disabled>...</button>`;
    }
  }

  if (current < pages) {
    html += `<button onclick="loadTrainingData(${current + 1})">Next</button>`;
  }

  pagination.innerHTML = html;
}
