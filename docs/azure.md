# Running the API on Microsoft Azure

This guide shows how the Docker container in this repo could run in the cloud on
**Azure Container Apps**, and maps each step to the **AZ-900: Azure Fundamentals**
topics it practises.

> **Costs:** Azure Container Apps has a monthly free allowance, but you need an Azure
> account with a payment method, and anything above the free allowance is billed.
> Check the current pricing before you start, and delete the resource group when
> you're done (step 5) so nothing keeps running.
>
> These steps have not been run against a live Azure account yet.

## 1. Install the Azure CLI and sign in

```bash
# https://learn.microsoft.com/cli/azure/install-azure-cli
az login
az extension add --name containerapp --upgrade
```

## 2. Create a resource group

A resource group is a folder that holds everything for one project, so it can be
managed (and deleted) together.

```bash
az group create --name spaza-rg --location southafricanorth
```

`southafricanorth` (Johannesburg) keeps the app close to South African users. If a
service isn't offered in that region, use another, such as `westeurope`.

## 3. Build and deploy the container

Run this from the repo folder. Azure builds the image from the `Dockerfile` and
starts it with a public HTTPS address:

```bash
az containerapp up \
  --name spaza-api \
  --resource-group spaza-rg \
  --location southafricanorth \
  --source . \
  --ingress external \
  --target-port 8000
```

The command prints the app's URL. Open it for the chatbot, or add `/docs` for the
API documentation.

## 4. (Optional) Turn on AI mode

Store the API key as a **secret**, never in the code or the image:

```bash
az containerapp secret set --name spaza-api --resource-group spaza-rg \
  --secrets anthropic-key=<your-key>
az containerapp update --name spaza-api --resource-group spaza-rg \
  --set-env-vars ANTHROPIC_API_KEY=secretref:anthropic-key
```

## 5. Clean up

```bash
az group delete --name spaza-rg --yes
```

## How this maps to AZ-900

| Step | AZ-900 topic |
|---|---|
| Container Apps runs the code without managing servers | Cloud service types: IaaS, **PaaS**, SaaS, and serverless |
| Choosing `southafricanorth` | **Regions**, availability zones and data residency |
| Resource group | **Resource groups**, subscriptions and management groups |
| Pay only for what runs, free allowance | **Consumption-based pricing** and cost management |
| Secrets instead of keys in code | **Security**, identity and access |
| `az` commands | Azure **management tools**: portal, CLI and PowerShell |
| Scaling with demand | **Scalability**, elasticity and high availability |

## AZ-900 study plan (4 weeks, about 1 hour a weekday)

The free official course is the **Microsoft Learn AZ-900 learning path**:
https://learn.microsoft.com/credentials/certifications/azure-fundamentals/

| Week | Study | Practise |
|---|---|---|
| 1 | Cloud concepts: benefits of the cloud, IaaS/PaaS/SaaS, public/private/hybrid cloud, consumption-based pricing | Explain each in one sentence using this project as the example |
| 2 | Azure architecture: regions, availability zones, resource groups, subscriptions; compute (VMs, containers, App Service, Functions); networking basics; storage | Draw how a request reaches this API on Azure |
| 3 | Identity and security: Microsoft Entra ID, multi-factor authentication, role-based access control (RBAC), Zero Trust, Defender for Cloud | Write down who should be allowed to deploy this app and why |
| 4 | Management and governance: cost management, tags, Azure Policy, resource locks, Azure Monitor; then practice tests | Take the free practice assessment on the exam page until you score 80%+ |

The exam itself is paid, and the price depends on your country (check the exam page).
Microsoft sometimes gives free exam vouchers to people who attend its free online
training events, so look out for those before paying.
