# Supported Tools and Commands

K8s MCP Server provides access to several Kubernetes CLI tools and additional utilities for command piping.

## Kubernetes CLI Tools

### kubectl

The standard command-line tool for interacting with Kubernetes clusters.

**Examples:**
```bash
kubectl get pods
kubectl get deployments
kubectl describe pod my-pod
kubectl get services
kubectl logs my-pod
kubectl apply -f deployment.yaml
```

### helm

The package manager for Kubernetes, used to install and manage applications.

**Examples:**
```bash
helm list
helm install my-release my-chart
helm upgrade my-release my-chart
helm uninstall my-release
helm repo add bitnami https://charts.bitnami.com/bitnami
helm search repo nginx
```

### istioctl

The command-line tool for the Istio service mesh, used to manage and configure Istio.

**Examples:**
```bash
istioctl analyze
istioctl proxy-status
istioctl dashboard
istioctl x describe pod my-pod
istioctl profile list
istioctl version
```

### argocd

The command-line tool for ArgoCD, a GitOps continuous delivery tool for Kubernetes.

**Examples:**
```bash
argocd app list
argocd app get my-app
argocd app sync my-app
argocd cluster list
argocd repo list
argocd project list
```

## Cloud Provider CLI Tools

### AWS CLI

The AWS Command Line Interface for managing AWS services, including EKS.

**Examples:**
```bash
aws eks list-clusters
aws eks describe-cluster --name my-cluster
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

### Google Cloud SDK (gcloud)

The Google Cloud command-line tool for managing GCP services, including GKE.

**Examples:**
```bash
gcloud container clusters list
gcloud container clusters describe my-cluster
gcloud container clusters get-credentials my-cluster --region us-central1
```

### Azure CLI (az)

The Azure command-line tool for managing Azure services, including AKS.

**Examples:**
```bash
az aks list
az aks show --name my-cluster --resource-group my-group
az aks get-credentials --name my-cluster --resource-group my-group
```

## Utility Tools for Command Piping

The Docker image includes a rich set of tools that can be used for command piping and output processing:

### Text Processing
- **jq**: JSON processor (`kubectl get pods -o json | jq '.items[].metadata.name'`)
- **grep**: Pattern matching (`kubectl get pods | grep Running`)
- **sed**: Stream editor (`kubectl get pods | sed 's/Running/UP/g'`)
- **awk**: Text processing (`kubectl get pods | awk '{print $1}'`)
- **findutils**: Collection of find utilities
- **gawk**: GNU awk implementation

### Network Utilities
- **curl**: HTTP client (`curl -s http://pod-ip:port | jq .`)
- **wget**: Alternative HTTP client
- **net-tools**: Network utilities (includes `netstat`, `ifconfig`)
- **dnsutils**: DNS utilities (includes `dig`, `nslookup`)

### File Management
- **tar**: Archive utility
- **gzip**: Compression utility
- **zip/unzip**: Zip file utilities

### Other Utilities
- **less**: Pager for viewing output
- **vim**: Text editor
- **openssh-client**: SSH client utilities
- **gnupg**: Encryption utilities

## Command Piping Examples

The server supports Unix command piping to filter and transform output:

```bash
# Extract pod names as a list
kubectl get pods -o json | jq -r '.items[].metadata.name'

# Find deployments in a non-Running state
kubectl get deployments | grep -v Running

# Format pod listing with custom columns
kubectl get pods | awk '{printf "%-30s %-10s\n", $1, $3}'

# Get container images running in the cluster
kubectl get pods -o jsonpath='{.items[*].spec.containers[*].image}' | tr -s '[[:space:]]' '\n' | sort | uniq

# Count pods by status
kubectl get pods | grep -v NAME | awk '{print $3}' | sort | uniq -c

# Fetch and process an API
kubectl run curl --image=curlimages/curl -i --rm -- curl -s https://api.example.com | jq .
```

## API Functions

Each CLI tool has documentation and execution functions:

### Documentation Functions
- `describe_kubectl(command=None)`: Get documentation for kubectl commands
- `describe_helm(command=None)`: Get documentation for Helm commands
- `describe_istioctl(command=None)`: Get documentation for Istio commands
- `describe_argocd(command=None)`: Get documentation for ArgoCD commands

### Execution Functions
- `execute_kubectl(command, timeout=None)`: Execute kubectl commands
- `execute_helm(command, timeout=None)`: Execute Helm commands
- `execute_istioctl(command, timeout=None)`: Execute Istio commands
- `execute_argocd(command, timeout=None)`: Execute ArgoCD commands