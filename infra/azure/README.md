# Azure Deployment Notes

Suggested services:

- Azure Container Apps or Azure App Service for the API
- Azure Database for PostgreSQL
- Azure OpenAI
- Azure Key Vault
- Azure Monitor and Log Analytics
- Azure Entra ID

Security recommendations:

- use managed identities for service-to-service access
- keep the database private to the application network boundary
- store secrets in Key Vault, not app settings files
- emit application and security telemetry to Azure Monitor

