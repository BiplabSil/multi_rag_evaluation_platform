# Multi-RAG Evaluation Platform Dashboard

A beautiful, user-friendly React dashboard for the Multi-RAG Evaluation Platform. This dashboard provides a visual interface for document ingestion, querying, metrics visualization, and vector store cleanup.

## Features

### 1. Ingestion Section
- Upload documents via file path or URL
- Specify document name and version metadata
- View ingestion status and chunk count
- Track document details (ID, filename, chunks)

### 2. Chat Section
- Ask natural language questions to your documents
- Optional ground truth input for better context_recall evaluation
- View retrieved document chunks
- Beautiful metric cards (PowerBI style) showing:
  - Faithfulness
  - Answer Relevancy
  - Context Precision
  - Context Recall

### 3. Metrics Dashboard
- Aggregate metrics overview cards
- Bar chart showing 4 metrics for last 10 queries
- Configurable threshold line
- Interactive tooltips
- Color-coded pass/fail indicators
- Recent queries table

### 4. Cleanup Section
- Search documents by metadata (name, version)
- Preview matching documents before deletion
- Delete old documents from vector store
- Safety warnings and confirmation dialogs

## Installation

```bash
cd dashboard
npm install
```

## Configuration

### Environment Variables

Create a `.env` file in the dashboard directory:

```env
VITE_API_URL=http://localhost:8000
```

### API Endpoints Expected

The dashboard expects the following API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ingest` | POST | Ingest a document |
| `/api/query` | POST | Run RAG query |
| `/api/metrics` | GET | Get evaluation metrics |
| `/api/search-by-metadata` | POST | Search documents by metadata |
| `/api/documents` | DELETE | Delete documents |
| `/api/health` | GET | Health check |

## Usage

### Development Mode

```bash
npm run dev
```

The dashboard will start on `http://localhost:5173` with API proxy to `http://localhost:8000`.

### Build for Production

```bash
npm run build
```

Output will be in the `dist/` folder.

### Preview Production Build

```bash
npm run preview
```

## Integration with Backend

The dashboard is designed as a **plug-and-play module**:

1. Ensure your FastAPI backend is running
2. Configure the API URL (default: `http://localhost:8000`)
3. The dashboard will automatically connect to the backend

### CORS Configuration (Backend)

Make sure your FastAPI app has CORS enabled:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Dashboard URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## File Structure

```
dashboard/
├── index.html              # HTML entry point
├── package.json            # Dependencies
├── vite.config.js          # Vite configuration
├── src/
│   ├── main.jsx            # React entry point
│   ├── App.jsx             # Main application component
│   ├── index.css           # Global styles
│   ├── services/
│   │   └── api.js          # API service module
│   └── components/
│       ├── IngestionForm.jsx    # Document upload form
│       ├── ChatSection.jsx      # Query and response
│       ├── MetricsDashboard.jsx # Metrics visualization
│       └── CleanupSection.jsx   # Document cleanup
└── public/                 # Static assets
```

## API Service Module

The `src/services/api.js` file provides a clean interface to the backend:

```javascript
import { ingestDocument, submitQuery, getMetrics, searchByMetadata, deleteDocuments } from './services/api';

// Ingest a document
const result = await ingestDocument({
  source: '/path/to/file.pdf',
  source_type: 'pdf',
  document_name: 'My Document',
  document_version: '1.0'
});

// Submit a query
const response = await submitQuery({
  question: 'What is the main topic?',
  ground_truth: 'The document is about...' // optional
});

// Get metrics
const metrics = await getMetrics(20);

// Search documents
const results = await searchByMetadata({
  document_name: 'HR Policy',
  document_version: '1.0'
});

// Delete documents
const deleted = await deleteDocuments({
  document_name: 'HR Policy',
  document_version: '1.0'
});
```

## Customization

### Colors

Edit CSS variables in `src/index.css`:

```css
:root {
  --bg-primary: #0f172a;
  --accent-blue: #3b82f6;
  --accent-green: #22c55e;
  /* ... other colors */
}
```

### Metrics Threshold

The default threshold is `0.6`. Adjust in the Metrics Dashboard UI or modify the initial state in `MetricsDashboard.jsx`:

```javascript
const [threshold, setThreshold] = useState(0.6);
```

## Tech Stack

- **React 18** - UI library
- **Recharts** - Charts and visualizations
- **Lucide React** - Icons
- **Vite** - Build tool

## License

Developed by Biplab Sil