# Dual-Mode Deployment - Quick Reference

## 🎯 Choose Your Deployment Mode

AWX MCP Server supports two deployment modes:

| Mode | Best For | Setup Time | Infrastructure |
|------|----------|------------|----------------|
| **Single User** | Individual developers, personal projects | 5 minutes | None |
| **Team/Enterprise** | Teams, organizations, compliance | 30+ minutes | Kubernetes/Cloud |

---

## 🖥️ Single User Mode (Local)

### Quick Start

```bash
# 1. Install
pip install awx-mcp-server

# 2. Configure VS Code
# Add to .vscode/settings.json:
{
  "github.copilot.chat.mcpServers": {
    "awx": {
      "command": "python",
      "args": ["-m", "awx_mcp_server"],
      "env": {
        "AWX_BASE_URL": "https://awx.example.com",
        "AWX_TOKEN": "${secret:awx-token}"
      }
    }
  }
}

# 3. Store your AWX token
# Ctrl+Shift+P → "GitHub: Store Secret"
# Name: awx-token
# Value: your-awx-api-token

# 4. Reload VS Code
# Ctrl+Shift+P → "Developer: Reload Window"

# 5. Start using!
# @workspace list AWX job templates
```

### Multiple Environments

```json
{
  "github.copilot.chat.mcpServers": {
    "awx-dev": { ... },
    "awx-staging": { ... },
    "awx-prod": { ... }
  }
}
```

Switch environments in Copilot Chat dropdown.

📚 **Full Guide:** [server/QUICK_START.md](server/QUICK_START.md)

---

## 🌐 Team/Enterprise Mode (Remote)

### Quick Start

```bash
# 1. Deploy server (choose one)

# Docker Compose:
cd server
docker-compose up -d

# Kubernetes:
kubectl apply -f deployment/kubernetes.yaml -n awx-mcp

# OpenShift:
oc apply -f deployment/kubernetes.yaml

# 2. Configure VS Code (clients)
{
  "github.copilot.chat.mcpServers": {
    "awx-remote": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-sse",
        "https://awx-mcp.company.com"
      ],
      "env": {
        "AWX_BASE_URL": "https://awx.example.com",
        "AWX_TOKEN": "${secret:awx-token}",
        "USER_ID": "john.doe@company.com"
      }
    }
  }
}

# 3. Use normally - same queries as single user mode!
```

### Credential Options

#### Option A: Client-Provided (Current - v1.1.5)
✅ **Implemented**

Clients pass AWX credentials to server each session.
- Credentials NOT stored on server
- Easy to switch environments
- Requires TLS for security

#### Option B: Vault Integration (Future - v2.0.0)
🚧 **Planned**

Server retrieves credentials from vault.
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager
- Kubernetes Secrets
- More...

**See:** [server/VAULT_INTEGRATION.md](server/VAULT_INTEGRATION.md)

📚 **Full Guide:** [server/REMOTE_DEPLOYMENT.md](server/REMOTE_DEPLOYMENT.md)

---

## 📊 Comparison

| Feature | Single User | Team/Enterprise |
|---------|-------------|-----------------|
| **Setup** | `pip install` | Deploy to K8s/Cloud |
| **Users** | 1 | Multiple |
| **Credentials** | Local (VS Code secrets) | Client-provided or Vault |
| **Switching Envs** | Multiple MCP configs | Same, per user |
| **Latency** | Very low | Low |
| **HA/Scaling** | No | Yes |
| **Audit Logs** | Limited | Centralized |
| **Cost** | Free | Infrastructure cost |
| **Best For** | Dev/Testing | Production/Teams |

---

## 🔄 Environment Switching

### Single User Mode

Configure multiple MCP servers in VS Code:

```json
{
  "github.copilot.chat.mcpServers": {
    "awx-dev": { "env": { "AWX_BASE_URL": "https://awx-dev.com", ... } },
    "awx-prod": { "env": { "AWX_BASE_URL": "https://awx-prod.com", ... } }
  }
}
```

Switch via Copilot Chat MCP dropdown.

### Team Mode

Each user configures their own environments:

```json
{
  "awx-remote-dev": {
    "args": ["...", "https://awx-mcp.company.com"],
    "env": { 
      "AWX_BASE_URL": "https://awx-dev.com",
      "AWX_TOKEN": "${secret:awx-dev-token}"
    }
  },
  "awx-remote-prod": {
    "args": ["...", "https://awx-mcp.company.com"],
    "env": { 
      "AWX_BASE_URL": "https://awx-prod.com",
      "AWX_TOKEN": "${secret:awx-prod-token}"
    }
  }
}
```

---

## 📁 Configuration Files

### Single User
- `.vscode/settings.json` - VS Code MCP config
- VS Code secrets - AWX tokens

### Team/Enterprise
- `deployment/docker-compose.yml` - Docker deployment
- `deployment/kubernetes.yaml` - K8s deployment
- `config/vault-config.yaml.template` - Vault config (future)

### Examples
- `docs/vscode-settings-examples.json` - All VS Code examples
- `server/QUICK_START.md` - Single user guide
- `server/REMOTE_DEPLOYMENT.md` - Enterprise guide

---

## 🔐 Security

### Single User
✅ Use VS Code secrets for tokens  
✅ Enable HTTPS for AWX  
✅ Rotate tokens regularly

### Team/Enterprise
✅ **Everything above, PLUS:**  
✅ TLS/SSL for remote server  
✅ Authentication at ingress  
✅ Network policies (K8s)  
✅ Audit logging  
✅ Vault integration (future)

---

## 🚀 Migration Path

### From Single User → Team/Enterprise

1. Deploy remote server
2. Update VS Code config to use remote endpoint
3. No changes to queries or workflow!

**Same queries work in both modes:**
```
list AWX job templates
launch job template 1
show recent failed jobs
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md) | Full architecture overview |
| [server/QUICK_START.md](server/QUICK_START.md) | Single user setup guide |
| [server/REMOTE_DEPLOYMENT.md](server/REMOTE_DEPLOYMENT.md) | Enterprise deployment guide |
| [server/VAULT_INTEGRATION.md](server/VAULT_INTEGRATION.md) | Vault integration (future) |
| [docs/vscode-settings-examples.json](docs/vscode-settings-examples.json) | All VS Code configurations |
| [AWX_MCP_QUERY_REFERENCE.md](AWX_MCP_QUERY_REFERENCE.md) | All available queries |

---

## 🛠️ Getting Help

- **Issues:** https://github.com/ldalcantara/awx-mcp-server/issues
- **Discussions:** https://github.com/ldalcantara/awx-mcp-server/discussions
- **Email:** ldalcantara@gmail.com

---

## ✅ Next Steps

### For Single User
1. 📖 Read [server/QUICK_START.md](server/QUICK_START.md)
2. 🔧 Install and configure
3. 🚀 Start automating!

### For Team/Enterprise
1. 📖 Read [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md)
2. 📖 Read [server/REMOTE_DEPLOYMENT.md](server/REMOTE_DEPLOYMENT.md)
3. ☸️ Deploy to K8s/Cloud
4. 🔧 Configure clients
5. 🚀 Onboard your team!

### For Vault Integration (Future)
1. 📖 Read [server/VAULT_INTEGRATION.md](server/VAULT_INTEGRATION.md)
2. ⭐ Star the repo and watch for v2.0.0
3. 💡 Open issues with your requirements
