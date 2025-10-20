# Spark Wikipedia Network Dataset Analysis on Kubernetes

This directory contains the deployment files and scripts for running Spark-based Wikipedia network dataset analysis on Kubernetes with throughput measurements.

## Overview

The Spark job performs network analysis on the Wikipedia voting dataset from Stanford SNAP:
- **Dataset**: Wikipedia adminship election voting data
- **Source**: https://snap.stanford.edu/data/wiki-Vote.txt.gz
- **Size**: ~7,115 nodes, ~103,689 edges
- **Format**: Tab-separated directed graph (from_node → to_node)

## Files

- `spark-wikipedia-deployment.yaml` - Kubernetes deployment configuration
- `deploy-and-monitor.sh` - Automated deployment and monitoring script
- `README.md` - This documentation

## Analysis Operations

The Spark application performs the following operations and measures throughput:

1. **Download Dataset** - Downloads Wikipedia voting network from SNAP
2. **Read & Parse** - Reads and parses the graph data into Spark DataFrame
3. **Count Edges** - Counts total number of edges in the network
4. **Count Nodes** - Counts unique nodes (voters and candidates)
5. **Out-Degree** - Calculates how many votes each user cast
6. **In-Degree** - Calculates how many votes each candidate received
7. **Top Influencers** - Finds top 10 most-voted candidates
8. **Statistics** - Computes average, max, min degrees

## Output Files

The job generates two output files saved to `/output/` volume (emptyDir):

### 1. throughput-data.csv
CSV file with performance metrics:
```csv
Metric,Value,Unit
download_time,X.XX,seconds
read_time,X.XX,seconds
total_edges,XXXXX,edges
count_time,X.XX,seconds
count_throughput,XXXXX.XX,edges/second
total_nodes,XXXX,nodes
unique_nodes_time,X.XX,seconds
outdegree_time,X.XX,seconds
outdegree_throughput,XXXX.XX,nodes/second
indegree_time,X.XX,seconds
indegree_throughput,XXXX.XX,nodes/second
top_influencers_time,X.XX,seconds
stats_time,X.XX,seconds
total_processing_time,XX.XX,seconds
overall_throughput,XXXXX.XX,edges/second
avg_out_degree,X.XX,edges
max_out_degree,XXX,edges
avg_in_degree,X.XX,edges
max_in_degree,XXX,edges
```

### 2. wikipedia-results.txt
Detailed analysis results including:
- Dataset statistics
- Performance metrics
- Top 10 influencers list

## Prerequisites

- Kubernetes cluster (version 1.20+)
- kubectl configured
- Sufficient resources: ~4GB memory, 2 CPU cores

## Quick Start

### Option 1: Automated Deployment (Recommended)

```bash
# Make the script executable
chmod +x deploy-and-monitor.sh

# Deploy and monitor (with automatic log export)
./deploy-and-monitor.sh
```

The script will:
1. Clean up any existing resources
2. Deploy the Spark job
3. Monitor execution and stream logs
4. Export results to `spark-logs_<timestamp>/` directory

### Option 2: Manual Deployment

```bash
# Deploy the resources
kubectl apply -f spark-wikipedia-deployment.yaml

# Monitor the job
kubectl get jobs -w

# Check pod logs
kubectl logs -f $(kubectl get pods -l app=spark-wikipedia -o jsonpath='{.items[0].metadata.name}')

# Wait for job completion
kubectl wait --for=condition=complete job/spark-wikipedia-job --timeout=1800s

# Export results
POD_NAME=$(kubectl get pods -l app=spark-wikipedia -o jsonpath='{.items[0].metadata.name}')
kubectl cp $POD_NAME:/output/throughput-data.csv ./throughput-data.csv
kubectl cp $POD_NAME:/output/wikipedia-results.txt ./wikipedia-results.txt
```

## Script Options

The `deploy-and-monitor.sh` script supports several options:

```bash
# Deploy to a specific namespace
./deploy-and-monitor.sh -n my-namespace

# Skip cleanup of existing resources
./deploy-and-monitor.sh --no-cleanup

# Skip automatic export (manual export needed)
./deploy-and-monitor.sh --no-export

# Show help
./deploy-and-monitor.sh --help
```

## Resource Configuration

Default resource allocation:
- **Memory Request**: 3GB
- **Memory Limit**: 4GB
- **CPU Request**: 1 core
- **CPU Limit**: 2 cores
- **Storage**: emptyDir volume (ephemeral)

To modify resources, edit the `spark-wikipedia-deployment.yaml` file:

```yaml
resources:
  requests:
    memory: "3Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

## Monitoring

### Check Job Status
```bash
kubectl get job spark-wikipedia-job
kubectl get pods -l app=spark-wikipedia
```

### View Logs
```bash
kubectl logs -f $(kubectl get pods -l app=spark-wikipedia -o jsonpath='{.items[0].metadata.name}')
```

### Check Results
```bash
# View throughput data
kubectl exec $(kubectl get pods -l app=spark-wikipedia -o jsonpath='{.items[0].metadata.name}') -- cat /output/throughput-data.csv

# View detailed results
kubectl exec $(kubectl get pods -l app=spark-wikipedia -o jsonpath='{.items[0].metadata.name}') -- cat /output/wikipedia-results.txt
```

## Troubleshooting

### Job Fails to Start
```bash
# Check job description
kubectl describe job spark-wikipedia-job

# Check pod events
kubectl describe pod $(kubectl get pods -l app=spark-wikipedia -o jsonpath='{.items[0].metadata.name}')
```

### Out of Memory
Increase memory limits in deployment YAML:
```yaml
resources:
  limits:
    memory: "6Gi"  # Increase from 4Gi
```

### Dataset Download Fails
Check network connectivity and firewall settings. The job needs to access:
- https://snap.stanford.edu/data/wiki-Vote.txt.gz

## Cleanup

### Delete Resources
```bash
kubectl delete job spark-wikipedia-job
kubectl delete configmap spark-wikipedia-config
```

### Using the Deployment File
```bash
kubectl delete -f spark-wikipedia-deployment.yaml
```

### Using the Script
```bash
# Next run will clean up automatically
./deploy-and-monitor.sh
```

## Performance Expectations

Typical performance on standard Kubernetes cluster:
- **Download Time**: 2-10 seconds (depends on network)
- **Read Time**: 1-3 seconds
- **Processing Time**: 10-30 seconds
- **Overall Throughput**: 3,000-10,000 edges/second

Performance varies based on:
- CPU/Memory allocation
- Cluster load
- Network speed
- Storage type

## Dataset Information

**Wikipedia Adminship Election Data**
- Nodes: 7,115 (Wikipedia users)
- Edges: 103,689 (voting relationships)
- Type: Directed graph
- Edge meaning: User A voted on User B in admin election
- Time span: Data collected over several years

Source: J. Leskovec, D. Huttenlocher, J. Kleinberg. "Signed Networks in Social Media." CHI 2010.

## Integration with Continuous Testing

This deployment can be integrated into continuous testing similar to Cassandra:

```bash
# Run periodic Spark jobs
while true; do
  ./deploy-and-monitor.sh
  sleep 3600  # Wait 1 hour
done
```

See the parent directory's `start-continuous-testing.sh` for examples.

## License

This implementation is part of the BioSys EC Elastic Container project.
