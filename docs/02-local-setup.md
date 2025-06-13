# Local Development Setup

This guide will help you set up your local development environment for the Vector Knowledge Engine system.

## Prerequisites

- Python 3.9 or higher
- Node.js 14+ (for Azure Functions Core Tools)
- Git
- Azure CLI
- Task (task runner)

## Installation Steps

### 1. Core Tools

```bash
# Install Azure Functions Core Tools (macOS)
brew tap azure/functions
brew install azure-functions-core-tools@4

# Install Task (macOS)
brew install go-task

# Install Azure CLI (macOS)
brew install azure-cli
```

For other operating systems, see the [official documentation](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local).

### 2. Clone Repository

```bash
git clone <repository-url>
cd vector-knowledge-engine
```

### 3. Python Environment

```bash
# Create and activate virtual environment
cd src/function
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configuration

1. Create local settings file:
```bash
cd src/function
```

2. Create `local.settings.json`:
```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "AZURE_STORAGE_CONNECTION_STRING": "",
    "AZURE_STORAGE_CONTAINER": "knowledge-base",
    "CONFLUENCE_URL": "",
    "CONFLUENCE_USERNAME": "",
    "CONFLUENCE_API_TOKEN": "",
    "CONFLUENCE_SPACE": "",
    "LOG_LEVEL": "INFO",
    "MAX_RESULTS": "5",
    "CONFIDENCE_THRESHOLD": "0.7"
  }
}
```

## Available Tasks

The project uses Taskfile for common operations. Here are the available tasks:

```bash
# View all available tasks
task --list

# Common tasks:
task setup:local     # Setup local environment
task func:start      # Start Azure Function locally
task extract        # Extract content from data sources
task build-index    # Build vector search index
task func:deploy    # Deploy to Azure
task ask            # Query the knowledge engine
```

## Local Development Workflow

### 1. Build Vector Index

```bash
# Extract content from data sources
task extract

# Build the vector search index
task build-index
```

### 2. Start Local Server

```bash
# Start the Azure Function
task func:start
```

### 3. Test Endpoints

1. Health Check:
```bash
curl http://localhost:7071/api/health
```

2. Search (JSON format):
```bash
curl -X POST http://localhost:7071/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 3, "format": "json"}'
```

3. Search (Slack format):
```bash
curl -X POST http://localhost:7071/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 3, "format": "slack"}'
```

4. Search (Teams format):
```bash
curl -X POST http://localhost:7071/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 3, "format": "teams"}'
```

5. Command-line query:
```bash
task ask "What is semantic search?"
```

## Data Source Configuration

### Confluence Integration
Add these settings to your `local.settings.json`:
```json
{
  "CONFLUENCE_URL": "https://your-confluence.atlassian.net",
  "CONFLUENCE_USERNAME": "your-email@company.com",
  "CONFLUENCE_API_TOKEN": "your-api-token",
  "CONFLUENCE_SPACE": "SPACE_KEY"
}
```

### Platform Extensions
For Slack bot integration:
```json
{
  "SLACK_BOT_TOKEN": "xoxb-your-bot-token",
  "SLACK_SIGNING_SECRET": "your-signing-secret"
}
```

For Teams bot integration:
```json
{
  "TEAMS_APP_ID": "your-app-id",
  "TEAMS_APP_PASSWORD": "your-app-password"
}
```

## Troubleshooting

### Common Issues

1. **"func" command not found**
   - Ensure Azure Functions Core Tools is installed
   - Add to PATH if necessary

2. **Missing dependencies**
   - Activate virtual environment
   - Run `pip install -r requirements.txt`

3. **Configuration errors**
   - Check `local.settings.json` values
   - Verify environment variables

4. **Port conflicts**
   - Default port is 7071
   - Change in `local.settings.json` if needed

5. **Index not found errors**
   - Ensure you've run `task extract` and `task build-index`
   - Check `data/index` directory for generated files

### Performance Optimization

For better local development performance:
1. Use a smaller dataset during development
2. Adjust chunk size in build scripts
3. Use local storage instead of Azure Storage

## Next Steps

After setting up your local environment:
1. Configure [Azure Resources](03-azure-setup.md) for production deployment
2. Review [System Architecture](system-architecture.md) for understanding the system
3. Set up platform extensions (Slack, Teams, etc.) as needed
