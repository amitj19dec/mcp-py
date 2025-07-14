# Azure Container Instance Deployment Guide - MCP Gateway

## 🎯 **Architecture Overview**

```
Internet → Application Gateway → Private VNet
                    ↓
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
Backend Pool 1    Backend Pool 2    Private Subnet
(Frontend)        (Backend API)     
    │                 │              
    ▼                 ▼              
ACI Frontend      ACI Backend       
React App         FastAPI          
(Port 80)         (Port 8001)      
```

## 📋 **Prerequisites**

- Azure CLI installed and configured
- Docker installed locally
- Access to MCP Gateway source code
- Azure subscription with appropriate permissions

## 🔧 **Step 1: Environment Setup**

### **1.1 Set Environment Variables**

```bash
# Azure Configuration
export RESOURCE_GROUP="rg-mcp-gateway"
export LOCATION="eastus"
export VNET_NAME="vnet-mcp-gateway"
export SUBNET_NAME="subnet-containers"
export APP_GW_NAME="agw-mcp-gateway"
export APP_GW_SUBNET="subnet-appgw"

# Container Configuration
export ACR_NAME="acrmcpgateway$(date +%s)"  # Must be globally unique
export BACKEND_CONTAINER_NAME="aci-mcp-backend"
export FRONTEND_CONTAINER_NAME="aci-mcp-frontend"

# Application Configuration
export UI_TOKEN="your-secure-ui-token-$(openssl rand -hex 16)"
export API_KEY="your-secure-api-key-$(openssl rand -hex 16)"
export MCP_SERVERS="demo:http://your-mcp-server:8000:demo"
```

### **1.2 Login to Azure**

```bash
# Login to Azure
az login

# Set subscription (if you have multiple)
az account set --subscription "your-subscription-id"

# Verify login
az account show
```

## 🏗️ **Step 2: Create Azure Resources**

### **2.1 Create Resource Group**

```bash
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### **2.2 Create Virtual Network**

```bash
# Create VNet
az network vnet create \
  --resource-group $RESOURCE_GROUP \
  --name $VNET_NAME \
  --address-prefix 10.0.0.0/16 \
  --location $LOCATION

# Create subnet for containers (private)
az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $SUBNET_NAME \
  --address-prefix 10.0.1.0/24

# Create subnet for Application Gateway
az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $APP_GW_SUBNET \
  --address-prefix 10.0.2.0/24
```

### **2.3 Create Container Registry**

```bash
# Create Azure Container Registry
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# Get ACR login server
export ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer --output tsv)

# Login to ACR
az acr login --name $ACR_NAME
```

## 🐳 **Step 3: Build and Push Docker Images**

### **3.1 Prepare Application Configuration**

**Create backend environment file:**
```bash
# Create backend/.env.production
cat > backend/.env.production << EOF
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8001
DEBUG=false
LOG_LEVEL=INFO
GATEWAY_API_KEY=$API_KEY
UI_TOKEN=$UI_TOKEN
CORS_ORIGINS=*
MCP_SERVERS=$MCP_SERVERS
HTTP_CONNECT_TIMEOUT=30
HTTP_REQUEST_TIMEOUT=60
HTTP_STREAM_TIMEOUT=300
MAX_RETRIES=3
HEALTH_CHECK_INTERVAL=30
MAX_ACTIVITY_EVENTS=1000
EOF
```

**Create frontend environment file:**
```bash
# Create frontend/.env.production
cat > frontend/.env.production << EOF
REACT_APP_API_URL=
REACT_APP_UI_TOKEN=$UI_TOKEN
REACT_APP_ENABLE_DEBUG=false
REACT_APP_ENABLE_AUTO_REFRESH=true
REACT_APP_SERVER_REFRESH_INTERVAL=10000
REACT_APP_ACTIVITY_REFRESH_INTERVAL=5000
REACT_APP_STATUS_REFRESH_INTERVAL=30000
GENERATE_SOURCEMAP=false
EOF
```

### **3.2 Build and Push Backend Image**

```bash
# Navigate to project root
cd /path/to/mcp-gateway-poc

# Build backend image
docker build \
  --file Dockerfile \
  --tag $ACR_LOGIN_SERVER/mcp-gateway-backend:latest \
  --build-arg ENV_FILE=.env.production \
  .

# Push backend image
docker push $ACR_LOGIN_SERVER/mcp-gateway-backend:latest
```

### **3.3 Build and Push Frontend Image**

```bash
# Build frontend image with Application Gateway integration
docker build \
  --file frontend/Dockerfile \
  --tag $ACR_LOGIN_SERVER/mcp-gateway-frontend:latest \
  --build-arg REACT_APP_API_URL="/api" \
  --build-arg REACT_APP_UI_TOKEN=$UI_TOKEN \
  --build-arg REACT_APP_ENABLE_DEBUG=false \
  frontend/

# Push frontend image
docker push $ACR_LOGIN_SERVER/mcp-gateway-frontend:latest
```

## 🔐 **Step 4: Create Service Principal for ACI**

```bash
# Create service principal for ACI to access ACR
export SP_NAME="sp-aci-acr-$RANDOM"

# Create service principal
export SP_APP_ID=$(az ad sp create-for-rbac \
  --name $SP_NAME \
  --scopes /subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ContainerRegistry/registries/$ACR_NAME \
  --role acrpull \
  --query appId \
  --output tsv)

# Get service principal password
export SP_PASSWORD=$(az ad sp credential reset \
  --id $SP_APP_ID \
  --query password \
  --output tsv)
```

## 📦 **Step 5: Deploy Container Instances**

### **5.1 Deploy Backend Container**

```bash
# Get subnet ID
export SUBNET_ID=$(az network vnet subnet show \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $SUBNET_NAME \
  --query id \
  --output tsv)

# Deploy backend ACI
az container create \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_CONTAINER_NAME \
  --image $ACR_LOGIN_SERVER/mcp-gateway-backend:latest \
  --registry-login-server $ACR_LOGIN_SERVER \
  --registry-username $SP_APP_ID \
  --registry-password $SP_PASSWORD \
  --vnet $VNET_NAME \
  --subnet $SUBNET_NAME \
  --ports 8001 \
  --protocol TCP \
  --cpu 2 \
  --memory 4 \
  --restart-policy Always \
  --environment-variables \
    GATEWAY_HOST=0.0.0.0 \
    GATEWAY_PORT=8001 \
    DEBUG=false \
    LOG_LEVEL=INFO \
    GATEWAY_API_KEY=$API_KEY \
    UI_TOKEN=$UI_TOKEN \
    CORS_ORIGINS="*" \
    MCP_SERVERS="$MCP_SERVERS" \
  --secure-environment-variables \
    GATEWAY_API_KEY=$API_KEY \
    UI_TOKEN=$UI_TOKEN
```

### **5.2 Deploy Frontend Container**

```bash
# Deploy frontend ACI
az container create \
  --resource-group $RESOURCE_GROUP \
  --name $FRONTEND_CONTAINER_NAME \
  --image $ACR_LOGIN_SERVER/mcp-gateway-frontend:latest \
  --registry-login-server $ACR_LOGIN_SERVER \
  --registry-username $SP_APP_ID \
  --registry-password $SP_PASSWORD \
  --vnet $VNET_NAME \
  --subnet $SUBNET_NAME \
  --ports 80 \
  --protocol TCP \
  --cpu 1 \
  --memory 2 \
  --restart-policy Always
```

### **5.3 Get Container Private IPs**

```bash
# Get backend private IP
export BACKEND_PRIVATE_IP=$(az container show \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_CONTAINER_NAME \
  --query ipAddress.ip \
  --output tsv)

# Get frontend private IP
export FRONTEND_PRIVATE_IP=$(az container show \
  --resource-group $RESOURCE_GROUP \
  --name $FRONTEND_CONTAINER_NAME \
  --query ipAddress.ip \
  --output tsv)

echo "Backend Private IP: $BACKEND_PRIVATE_IP"
echo "Frontend Private IP: $FRONTEND_PRIVATE_IP"
```

## 🌐 **Step 6: Create Application Gateway**

### **6.1 Create Public IP for Application Gateway**

```bash
az network public-ip create \
  --resource-group $RESOURCE_GROUP \
  --name pip-$APP_GW_NAME \
  --allocation-method Static \
  --sku Standard \
  --location $LOCATION
```

### **6.2 Create Application Gateway**

```bash
# Create Application Gateway
az network application-gateway create \
  --name $APP_GW_NAME \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --subnet $APP_GW_SUBNET \
  --capacity 1 \
  --sku Standard_v2 \
  --http-settings-cookie-based-affinity Disabled \
  --frontend-port 80 \
  --http-settings-port 80 \
  --http-settings-protocol Http \
  --public-ip-address pip-$APP_GW_NAME \
  --servers $FRONTEND_PRIVATE_IP
```

### **6.3 Configure Backend Pools**

```bash
# Create backend pool for API
az network application-gateway address-pool create \
  --gateway-name $APP_GW_NAME \
  --resource-group $RESOURCE_GROUP \
  --name backend-api-pool \
  --servers $BACKEND_PRIVATE_IP

# Create backend pool for frontend (update existing)
az network application-gateway address-pool update \
  --gateway-name $APP_GW_NAME \
  --resource-group $RESOURCE_GROUP \
  --name appGatewayBackendPool \
  --servers $FRONTEND_PRIVATE_IP
```

### **6.4 Configure HTTP Settings**

```bash
# Create HTTP settings for API backend
az network application-gateway http-settings create \
  --gateway-name $APP_GW_NAME \
  --resource-group $RESOURCE_GROUP \
  --name api-http-settings \
  --port 8001 \
  --protocol Http \
  --cookie-based-affinity Disabled \
  --timeout 60 \
  --probe-name api-health-probe

# Create health probe for API
az network application-gateway probe create \
  --gateway-name $APP_GW_NAME \
  --resource-group $RESOURCE_GROUP \
  --name api-health-probe \
  --protocol Http \
  --host-name-from-http-settings \
  --path /api/health \
  --interval 30 \
  --timeout 30 \
  --threshold 3

# Update default HTTP settings for frontend
az network application-gateway http-settings update \
  --gateway-name $APP_GW_NAME \
  --resource-group $RESOURCE_GROUP \
  --name appGatewayBackendHttpSettings \
  --port 80 \
  --protocol Http \
  --cookie-based-affinity Disabled \
  --timeout 60
```

### **6.5 Configure URL Path Map and Rules**

```bash
# Create URL path map
az network application-gateway url-path-map create \
  --gateway-name $APP_GW_NAME \
  --resource-group $RESOURCE_GROUP \
  --name path-map \
  --default-address-pool appGatewayBackendPool \
  --default-http-settings appGatewayBackendHttpSettings

# Add path rule for API
az network application-gateway url-path-map rule create \
  --gateway-name $APP_GW_NAME \
  --resource-group $RESOURCE_GROUP \
  --path-map-name path-map \
  --name api-rule \
  --paths "/api/*" "/mcp" \
  --address-pool backend-api-pool \
  --http-settings api-http-settings

# Update listener to use path-based routing
az network application-gateway http-listener update \
  --gateway-name $APP_GW_NAME \
  --resource-group $RESOURCE_GROUP \
  --name appGatewayHttpListener \
  --frontend-port appGatewayFrontendPort \
  --protocol Http

# Update routing rule to use path map
az network application-gateway rule update \
  --gateway-name $APP_GW_NAME \
  --resource-group $RESOURCE_GROUP \
  --name rule1 \
  --http-listener appGatewayHttpListener \
  --rule-type PathBasedRouting \
  --url-path-map path-map
```

## 🔧 **Step 7: Configure Frontend for Application Gateway**

### **7.1 Update Frontend Configuration**

The frontend needs to know that the API is available at the same domain under `/api` path.

**Create updated frontend nginx config:**

```bash
# Create custom nginx.conf for frontend
cat > frontend/nginx-appgw.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    server {
        listen 80;
        server_name localhost;
        root /usr/share/nginx/html;
        index index.html;
        
        # Serve React app
        location / {
            try_files $uri $uri/ /index.html;
        }
        
        # Proxy API requests to backend through Application Gateway
        location /api/ {
            proxy_pass http://backend-internal:8001/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Proxy MCP requests to backend through Application Gateway  
        location /mcp {
            proxy_pass http://backend-internal:8001/mcp;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF
```

### **7.2 Rebuild Frontend with Correct API URL**

```bash
# Rebuild frontend image with relative API URL
docker build \
  --file frontend/Dockerfile \
  --tag $ACR_LOGIN_SERVER/mcp-gateway-frontend:v2 \
  --build-arg REACT_APP_API_URL="" \
  --build-arg REACT_APP_UI_TOKEN=$UI_TOKEN \
  --build-arg REACT_APP_ENABLE_DEBUG=false \
  frontend/

# Push updated image
docker push $ACR_LOGIN_SERVER/mcp-gateway-frontend:v2

# Update frontend container
az container delete \
  --resource-group $RESOURCE_GROUP \
  --name $FRONTEND_CONTAINER_NAME \
  --yes

# Redeploy with new image
az container create \
  --resource-group $RESOURCE_GROUP \
  --name $FRONTEND_CONTAINER_NAME \
  --image $ACR_LOGIN_SERVER/mcp-gateway-frontend:v2 \
  --registry-login-server $ACR_LOGIN_SERVER \
  --registry-username $SP_APP_ID \
  --registry-password $SP_PASSWORD \
  --vnet $VNET_NAME \
  --subnet $SUBNET_NAME \
  --ports 80 \
  --protocol TCP \
  --cpu 1 \
  --memory 2 \
  --restart-policy Always
```

## 📊 **Step 8: Verification and Testing**

### **8.1 Get Application Gateway Public IP**

```bash
# Get Application Gateway public IP
export APP_GW_PUBLIC_IP=$(az network public-ip show \
  --resource-group $RESOURCE_GROUP \
  --name pip-$APP_GW_NAME \
  --query ipAddress \
  --output tsv)

echo "Application Gateway Public IP: $APP_GW_PUBLIC_IP"
echo "Frontend URL: http://$APP_GW_PUBLIC_IP"
echo "Backend API URL: http://$APP_GW_PUBLIC_IP/api/health"
echo "MCP Endpoint: http://$APP_GW_PUBLIC_IP/mcp"
```

### **8.2 Test Connectivity**

```bash
# Test backend health
curl -v http://$APP_GW_PUBLIC_IP/api/health

# Test MCP endpoint
curl -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
     http://$APP_GW_PUBLIC_IP/mcp

# Test frontend
curl -v http://$APP_GW_PUBLIC_IP/
```

### **8.3 Monitor Container Status**

```bash
# Check backend container status
az container show \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_CONTAINER_NAME \
  --query instanceView.state

# Check frontend container status  
az container show \
  --resource-group $RESOURCE_GROUP \
  --name $FRONTEND_CONTAINER_NAME \
  --query instanceView.state

# View backend logs
az container logs \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_CONTAINER_NAME

# View frontend logs
az container logs \
  --resource-group $RESOURCE_GROUP \
  --name $FRONTEND_CONTAINER_NAME
```

## 🔒 **Step 9: Security Hardening (Optional)**

### **9.1 Enable HTTPS with SSL Certificate**

```bash
# Create self-signed certificate (for testing)
openssl req -x509 -newkey rsa:4096 -keyout appgw-key.pem -out appgw-cert.pem -days 365 -nodes \
  -subj "/CN=$APP_GW_PUBLIC_IP"

# Convert to PFX format
openssl pkcs12 -export -out appgw-cert.pfx -inkey appgw-key.pem -in appgw-cert.pem -passout pass:

# Upload certificate to Application Gateway
az network application-gateway ssl-cert create \
  --gateway-name $APP_GW_NAME \
  --resource-group $RESOURCE_GROUP \
  --name appgw-ssl-cert \
  --cert-file appgw-cert.pfx \
  --cert-password ""

# Add HTTPS listener
az network application-gateway frontend-port create \
  --gateway-name $APP_GW_NAME \
  --resource-group $RESOURCE_GROUP \
  --name appGatewayFrontendPortHttps \
  --port 443

az network application-gateway http-listener create \
  --gateway-name $APP_GW_NAME \
  --resource-group $RESOURCE_GROUP \
  --name appGatewayHttpsListener \
  --frontend-ip appGatewayFrontendIP \
  --frontend-port appGatewayFrontendPortHttps \
  --protocol Https \
  --ssl-cert appgw-ssl-cert
```

### **9.2 Configure Network Security Groups**

```bash
# Create NSG for container subnet
az network nsg create \
  --resource-group $RESOURCE_GROUP \
  --name nsg-containers

# Allow Application Gateway to access containers
az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name nsg-containers \
  --name AllowAppGateway \
  --priority 100 \
  --source-address-prefixes 10.0.2.0/24 \
  --destination-port-ranges 80 8001 \
  --access Allow \
  --protocol Tcp

# Associate NSG with container subnet
az network vnet subnet update \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $SUBNET_NAME \
  --network-security-group nsg-containers
```

## 🔄 **Step 10: Maintenance and Updates**

### **10.1 Update Images**

```bash
# Build new version
docker build --tag $ACR_LOGIN_SERVER/mcp-gateway-backend:v2 .
docker push $ACR_LOGIN_SERVER/mcp-gateway-backend:v2

# Update container
az container delete --resource-group $RESOURCE_GROUP --name $BACKEND_CONTAINER_NAME --yes
# Redeploy with new image tag
```

### **10.2 Scale Resources**

```bash
# Update container resources
az container update \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_CONTAINER_NAME \
  --cpu 4 \
  --memory 8
```

### **10.3 Backup Configuration**

```bash
# Export resource group template
az group export \
  --name $RESOURCE_GROUP \
  --output-format json > deployment-backup.json
```

## 🚨 **Troubleshooting Guide**

### **Common Issues:**

1. **Containers not starting:**
   ```bash
   az container logs --resource-group $RESOURCE_GROUP --name $BACKEND_CONTAINER_NAME
   ```

2. **Application Gateway can't reach containers:**
   ```bash
   # Check backend health
   az network application-gateway show-backend-health \
     --resource-group $RESOURCE_GROUP \
     --name $APP_GW_NAME
   ```

3. **Frontend can't reach backend:**
   - Verify CORS_ORIGINS includes Application Gateway domain
   - Check path routing configuration
   - Verify network security group rules

4. **ACR authentication issues:**
   ```bash
   # Regenerate ACR credentials
   az acr credential renew --name $ACR_NAME --password-name password
   ```

### **Clean Up Resources**

```bash
# Delete entire resource group (CAUTION: This deletes everything)
az group delete --name $RESOURCE_GROUP --yes --no-wait
```

This setup provides a production-ready deployment of the MCP Gateway with proper security, networking, and scalability considerations.