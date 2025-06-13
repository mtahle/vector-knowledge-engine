# Azure Setup Guide

This guide explains how to set up the required Azure resources for deploying the Vector Knowledge Engine.

## Prerequisites

- Azure subscription
- Azure CLI installed and configured
- Local environment set up ([see local setup guide](02-local-setup.md))

## Azure Resources Overview

The system requires the following Azure resources:
- Azure Function App (for hosting the search API)
- Azure Storage Account (for storing the vector index)
- Application Insights (for monitoring)

## Setup Steps

### 1. Login to Azure

```bash
# Login to Azure CLI
az login

# Set subscription
az account set --subscription <subscription-id>
```

### 2. Create Resource Group

```bash
# Set variables
export RESOURCE_GROUP="rg-vector-knowledge-engine"
export LOCATION="northeurope"
export STORAGE_ACCOUNT="stvectorknowledge"
export FUNCTION_APP="fa-vector-knowledge-engine"

# Create resource group
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION
```

### 3. Create Storage Account

```bash
# Create storage account
az storage account create \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Standard_LRS \
    --allow-blob-public-access false

# Create container
az storage container create \
    --name knowledge-base \
    --account-name $STORAGE_ACCOUNT \
    --public-access off

# Get connection string
export AZURE_STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --query connectionString \
    --output tsv)
```

### 4. Create Function App

```bash
# Create app insights
az monitor app-insights component create \
    --app ai-vector-knowledge-engine \
    --location $LOCATION \
    --resource-group $RESOURCE_GROUP \
    --application-type web

# Create function app
az functionapp create \
    --name $FUNCTION_APP \
    --storage-account $STORAGE_ACCOUNT \
    --consumption-plan-location $LOCATION \
    --resource-group $RESOURCE_GROUP \
    --functions-version 4 \
    --runtime python \
    --runtime-version 3.9 \
    --app-insights ai-vector-knowledge-engine
```

### 5. Configure Function App

```bash
# Configure application settings
az functionapp config appsettings set \
    --name $FUNCTION_APP \
    --resource-group $RESOURCE_GROUP \
    --settings \
    AZURE_STORAGE_CONNECTION_STRING=$AZURE_STORAGE_CONNECTION_STRING \
    AZURE_STORAGE_CONTAINER=knowledge-base \
    CONFLUENCE_URL=$CONFLUENCE_URL \
    CONFLUENCE_USERNAME=$CONFLUENCE_USERNAME \
    CONFLUENCE_API_TOKEN=$CONFLUENCE_API_TOKEN \
    CONFLUENCE_SPACE=$CONFLUENCE_SPACE \
    LOG_LEVEL=INFO \
    MAX_RESULTS=5 \
    CONFIDENCE_THRESHOLD=0.7
```

### 6. Configure Function Settings

1. Create or update `host.json`:
```json
{
    "version": "2.0",
    "logging": {
        "applicationInsights": {
            "samplingSettings": {
                "isEnabled": true,
                "excludedTypes": "Request"
            }
        }
    },
    "extensionBundle": {
        "id": "Microsoft.Azure.Functions.ExtensionBundle",
        "version": "[3.*, 4.0.0)"
    }
}
```

2. Configure CORS for web applications:
```bash
az functionapp cors add \
    --name $FUNCTION_APP \
    --resource-group $RESOURCE_GROUP \
    --allowed-origins "*"
```

## Platform-Specific Configuration

### For Slack Integration
```bash
# Add Slack-specific settings
az functionapp config appsettings set \
    --name $FUNCTION_APP \
    --resource-group $RESOURCE_GROUP \
    --settings \
    SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN \
    SLACK_SIGNING_SECRET=$SLACK_SIGNING_SECRET

# Configure CORS for Slack
az functionapp cors add \
    --name $FUNCTION_APP \
    --resource-group $RESOURCE_GROUP \
    --allowed-origins "https://*.slack.com"
```

### For Teams Integration
```bash
# Add Teams-specific settings
az functionapp config appsettings set \
    --name $FUNCTION_APP \
    --resource-group $RESOURCE_GROUP \
    --settings \
    TEAMS_APP_ID=$TEAMS_APP_ID \
    TEAMS_APP_PASSWORD=$TEAMS_APP_PASSWORD

# Configure CORS for Teams
az functionapp cors add \
    --name $FUNCTION_APP \
    --resource-group $RESOURCE_GROUP \
    --allowed-origins "https://*.teams.microsoft.com"
```

## Scaling Configuration

The Function App uses the Consumption plan by default:
- Automatically scales based on load
- Charges only for actual usage
- Maximum of 200 concurrent executions

To adjust scaling:
1. Go to Azure Portal > Function App > Scale out
2. Configure:
   - Maximum instance count
   - Scale rules
   - Pre-warmed instances (Premium plan only)

For high-performance requirements:
```bash
# Switch to Premium plan (if needed)
az functionapp plan create \
    --name premium-plan \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku EP1

# Update function app to use Premium plan
az functionapp update \
    --name $FUNCTION_APP \
    --resource-group $RESOURCE_GROUP \
    --plan premium-plan
```

## Upload Vector Index

After building the index locally, upload it to Azure Storage:

```bash
# Upload index files
az storage blob upload-batch \
    --account-name $STORAGE_ACCOUNT \
    --destination knowledge-base \
    --source data/index
```

## Deployment

Deploy the function app using the task:

```bash
task func:deploy
```

## Verify Deployment

1. Check function app status:
```bash
az functionapp show \
    --name $FUNCTION_APP \
    --resource-group $RESOURCE_GROUP \
    --query state
```

2. Test the health endpoint:
```bash
curl https://$FUNCTION_APP.azurewebsites.net/api/health
```

3. Test the search endpoint:
```bash
curl -X POST https://$FUNCTION_APP.azurewebsites.net/api/search \
    -H "Content-Type: application/json" \
    -d '{"query": "test query", "top_k": 3}'
```

## Monitoring

### Application Insights

1. View logs:
```bash
az monitor app-insights query \
    --app ai-vector-knowledge-engine \
    --resource-group $RESOURCE_GROUP \
    --analytics-query "requests | where timestamp > ago(1h)"
```

2. Check performance:
```bash
az monitor app-insights metrics list \
    --app ai-vector-knowledge-engine \
    --resource-group $RESOURCE_GROUP
```

### Storage Monitoring

Monitor blob storage usage:
```bash
az storage blob list \
    --container-name knowledge-base \
    --account-name $STORAGE_ACCOUNT \
    --query "[].{name:name, size:properties.contentLength}"
```

## Troubleshooting

### Common Issues

1. **Deployment Failures**
   - Check function app logs
   - Verify Python version compatibility
   - Check resource quotas

2. **Storage Access Issues**
   - Verify connection string
   - Check container permissions
   - Validate storage account firewall settings

3. **Configuration Problems**
   - Review application settings
   - Check environment variables
   - Verify service principal permissions

4. **Search Performance Issues**
   - Monitor index loading times
   - Check memory usage
   - Verify embedding model compatibility

## Next Steps

After setting up Azure resources:
1. Configure platform extensions (Slack, Teams, etc.)
2. Test the deployment with various queries
3. Monitor the application performance
4. Set up automated deployments
