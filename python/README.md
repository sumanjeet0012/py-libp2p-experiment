# Canteen Python Implementation

Python implementation of Canteen using py-libp2p with rendezvous peer discovery.

## Installation

```bash
pip install -r requirements.txt
```

## Prerequisites

1. **Ganache running**
   ```bash
   ganache-cli -p 7545
   ```

2. **Docker running**
   ```bash
   docker ps
   ```

3. **Contract deployed**
   ```bash
   truffle migrate --network development
   # Update CONTRACT_ADDRESS in .env
   ```

## Usage

### Server Mode (First Node - Rendezvous Server)

```bash
cd python
python main.py
```

Save the server address from output (e.g., `/ip4/127.0.0.1/tcp/5000/p2p/QmXxx...`)

### Client Mode (Additional Nodes)

```bash
cd python
BOOTSTRAP_NODES=/ip4/127.0.0.1/tcp/5000/p2p/QmXxx... \
P2P_PORT=5001 \
WEB_API_PORT=3001 \
python main.py
```

## Testing

### Check Health

```bash
curl http://localhost:3000/health
curl http://localhost:3000/cluster
```

### Assign Docker Image

```bash
truffle console --network development

const canteen = await Canteen.deployed()
await canteen.addImage("nginx:latest", 2)
```

The scheduler will automatically pull and run the container.

### Verify Container

```bash
docker ps
```

## Configuration

Edit `.env` file:

```properties
BLOCKCHAIN_PROVIDER=http://localhost:7545
CONTRACT_ADDRESS=0x...
P2P_PORT=5000
WEB_API_PORT=3000
BOOTSTRAP_NODES=
RENDEZVOUS_NAMESPACE=canteen-cluster
DOCKER_SOCKET=/var/run/docker.sock
SCHEDULER_POLL_INTERVAL=1000
```

## Architecture

```
main.py
├── config.py          # Environment variables
├── cluster.py         # py-libp2p + rendezvous discovery
├── scheduler.py       # Web3 + Docker management
└── web_server.py      # Flask health API
```

### Flow

1. **Load config** from `.env`
2. **Start P2P node** with rendezvous discovery
3. **Start web server** for health checks
4. **Initialize scheduler** (connect to blockchain and Docker)
5. **Register node** with smart contract
6. **Poll contract** every second for image assignments
7. **Manage containers** automatically

## Key Features

- **Rendezvous discovery** for P2P networking
- **Smart contract polling** for orchestration
- **Automatic Docker management** (pull, run, stop)
- **Health API** for monitoring
- **Graceful shutdown** (Ctrl+C)
- **Pure Trio async** (no asyncio)

## Troubleshooting

### Can't connect to blockchain
```bash
# Check Ganache
curl -X POST http://localhost:7545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### Docker permission denied
```bash
# Linux: Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Port already in use
```bash
# Use different ports
P2P_PORT=5010 WEB_API_PORT=3010 python main.py
```

