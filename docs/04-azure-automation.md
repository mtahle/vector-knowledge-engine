# Azure Automation Guide

This guide explains how to use the automated Azure setup tasks to quickly deploy the Vector Knowledge Engine to Azure.

## Overview

The Taskfile includes automated tasks to:
- Create all required Azure resources
- Configure platform integrations (Confluence, Slack, Teams)
- Upload vector indexes
- Deploy the function app

## Prerequisites

1. **Local Environment Setup**
   ```bash
   task setup:local
   ```

2. **Azure CLI Login**
   ```bash
   az login
   ```

3. **Set Subscription (if needed)**
   ```bash
   az account set --subscription <subscription-id>
   ```

## Quick Start - Automated Setup

### 1. Create Azure Resources

```bash
task setup:azure
```

This task will:
- ✅ Create a resource group
- ✅ Create a storage account with unique name
- ✅ Create a storage container for the vector index
- ✅ Create Application Insights for monitoring
- ✅ Create a Premium Function App Plan (EP1)
- ✅ Create an Azure Function App on Linux
- ✅ Configure basic settings and CORS
- ✅ Display all resource names and next steps

**Example Output:**
```
✅ Azure setup completed successfully!

📋 Resource Summary:
===================
Resource Group: rg-vector-knowledge-engine
Storage Account: stvectorknowledge1703847281
Function Plan: plan-vector-knowledge-engine (Premium EP1)
Function App: fa-vector-knowledge-engine-1703847281
Application Insights: ai-vector-knowledge-engine
Function App URL: https://fa-vector-knowledge-engine-1703847281.azurewebsites.net
```

### 2. Configure Platform Integrations (Optional)

#### Configure Confluence
```bash
# Set the resource names from step 1
export FUNCTION_APP=fa-vector-knowledge-engine-1703847281
export RESOURCE_GROUP=rg-vector-knowledge-engine

# Configure Confluence integration
task azure:config:confluence
```

#### Configure Slack Integration
```bash
task azure:config:slack
```

#### Configure Teams Integration
```bash
task azure:config:teams
```

### 3. Build and Upload Vector Index

```bash
# Extract content from your data sources
task extract

# Build the vector index
task build-index

# Upload to Azure (set STORAGE_ACCOUNT from step 1)
export STORAGE_ACCOUNT=stvectorknowledge1703847281
task azure:upload-index
```

### 4. Deploy Function App

```bash
# Deploy the function code
task func:deploy
```

### 5. Test Your Deployment

```bash
# Test health endpoint
curl https://fa-vector-knowledge-engine-1703847281.azurewebsites.net/api/health

# Test search endpoint
curl -X POST https://fa-vector-knowledge-engine-1703847281.azurewebsites.net/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 3}'
```

## Available Tasks

### Core Setup Tasks

| Task | Description |
|------|-------------|
| `setup:azure` | Create all Azure resources automatically |
| `azure:upload-index` | Upload vector index to Azure Storage |

### Configuration Tasks

| Task | Description |
|------|-------------|
| `azure:config:confluence` | Configure Confluence integration |
| `azure:config:slack` | Configure Slack bot integration |
| `azure:config:teams` | Configure Teams bot integration |

### Deployment Tasks

| Task | Description |
|------|-------------|
| `func:deploy` | Deploy function app to Azure |

## Environment Variables

The automation tasks use environment variables that can be customized:

```bash
# Optional: Customize resource names (before running setup:azure)
export RESOURCE_GROUP="my-custom-rg"
export LOCATION="northeurope"
export STORAGE_ACCOUNT="mycustomstorage"
export FUNCTION_APP="my-custom-function-app"
export FUNCTION_PLAN="my-custom-plan"

# Required: Set after setup for other tasks
export FUNCTION_APP="fa-vector-knowledge-engine-1703847281"
export RESOURCE_GROUP="rg-vector-knowledge-engine"
export STORAGE_ACCOUNT="stvectorknowledge1703847281"
```

## Resource Naming Strategy

By default, the automation creates resources with unique names:
- **Resource Group**: `rg-vector-knowledge-engine`
- **Storage Account**: `stvectorknowledge[timestamp]`
- **Function Plan**: `plan-vector-knowledge-engine`
- **Function App**: `fa-vector-knowledge-engine-[timestamp]`
- **App Insights**: `ai-vector-knowledge-engine`

The timestamp suffix ensures unique names for storage accounts and function apps (which must be globally unique).

## Premium Plan Benefits

The automation uses Azure Functions Premium Plan (EP1) which provides:

### Performance Benefits
- **Predictable Performance**: Always-warm instances eliminate cold starts
- **Dedicated Resources**: vCPU and memory allocation for consistent performance
- **Better Throughput**: Higher concurrent execution limits
- **Faster Scaling**: Pre-warmed instances ready for immediate use

### Enterprise Features
- **VNet Integration**: Private network connectivity
- **Custom Domains**: Professional URL endpoints
- **Advanced Security**: Enhanced isolation and authentication options
- **Longer Execution Time**: Up to 60 minutes per function execution

## Cost Information

The automated setup uses Azure services with the following pricing structure:

### Premium Plan (EP1)
- **Always-on pricing**: ~$146/month base cost
- **Execution pricing**: Additional charges for high-volume usage
- **Memory**: 3.5 GB RAM, 1 vCPU core
- **Storage**: 250 GB included

### Other Services
- **Storage Account**: Standard LRS (~$0.018/GB/month)
- **Application Insights**: Pay-as-you-go (~$2.30/GB)

**Estimated monthly cost for production usage**: $150-200 USD

> **Note**: For development/testing, you may want to consider the Consumption plan. Modify the Taskfile.yml to remove the Premium plan creation and use `--consumption-plan-location` instead.

## Troubleshooting

### Common Issues

1. **"Resource name already exists"**
   - Storage accounts and function apps must be globally unique
   - The automation adds timestamps to prevent this
   - If you get this error, run the setup again

2. **"Azure CLI not logged in"**
   ```bash
   az login
   ```

3. **"Environment variable not set"**
   - After running `setup:azure`, save the resource names
   - Export them as environment variables for subsequent tasks

4. **"Index files not found"**
   - Run `task extract` and `task build-index` before uploading

5. **"Insufficient quota for EP1"**
   - Check your Azure subscription limits
   - Consider using a different region or SKU

### Manual Resource Management

If you need to customize resources beyond the automation:

```bash
# List all resources in the group
az resource list --resource-group rg-vector-knowledge-engine --output table

# Scale the function plan
az functionapp plan update --name plan-vector-knowledge-engine --resource-group rg-vector-knowledge-engine --sku EP2

# Delete entire resource group (careful!)
az group delete --name rg-vector-knowledge-engine
```

## Security Considerations

1. **API Keys**: Store sensitive configuration (API tokens, passwords) securely
2. **CORS**: The automation enables `*` CORS for development; restrict in production
3. **Authentication**: Consider enabling Azure Function authentication for production
4. **Network**: Use VNet integration and private endpoints for enterprise deployments
5. **Premium Plan**: Provides enhanced security isolation compared to Consumption plan

## Next Steps

After successful deployment:
1. Set up monitoring and alerting in Azure Portal
2. Configure custom domains and SSL certificates
3. Set up CI/CD pipelines for automated deployments
4. Review and optimize cost allocation
5. Configure VNet integration for enhanced security
6. Set up auto-scaling rules based on usage patterns

## Support

For issues with the automation tasks:
1. Check the task output for specific error messages
2. Verify Azure CLI permissions and quotas
3. Review the [Manual Azure Setup](03-azure-setup.md) guide for detailed steps 