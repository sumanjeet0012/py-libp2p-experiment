# Canteen Dashboard

Visual interface for monitoring and managing your Canteen cluster.

## Features

- **Real-time cluster visualization** - See all nodes and their connections
- **Node status monitoring** - View which images are deployed on each node
- **Image management** - Add and remove Docker images from the cluster
- **Blockchain integration** - Direct interaction with Canteen smart contract

---

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure

```bash
# Copy example config
cp .env.example .env

# Edit configuration
nano .env
```

Update these values:
```bash
REACT_APP_API_URL=http://localhost:3000
REACT_APP_BLOCKCHAIN_PROVIDER=http://localhost:7545
REACT_APP_CONTRACT_ADDRESS=0xYourContractAddress
```

### 3. Start Dashboard

```bash
npm start
```

Dashboard opens at `http://localhost:3001`

---

## Configuration

All configuration is done via environment variables. See `CONFIGURATION_GUIDE.md` for details.

### Key Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `REACT_APP_API_URL` | Canteen node API endpoint | `http://localhost:3000` |
| `REACT_APP_BLOCKCHAIN_PROVIDER` | Blockchain provider URL | `http://localhost:7545` |
| `REACT_APP_CONTRACT_ADDRESS` | Contract address | `0x8fC4...` |
| `PORT` | Dashboard server port | `3001` |

### Override at Runtime

```bash
# Connect to different node
REACT_APP_API_URL=http://192.168.1.10:3000 npm start

# Use different port
PORT=3005 npm start

# Both
REACT_APP_API_URL=http://192.168.1.10:3000 PORT=3005 npm start
```

---

## Usage

### Viewing Cluster

The dashboard displays:
- **Nodes** - All registered Canteen nodes
- **Connections** - Network topology between nodes
- **Images** - Docker images assigned to each node
- **Status** - Node health (Up/Down)

### Adding Images

1. Enter image name (e.g., `nginx:latest`)
2. Enter number of replicas
3. Click "Add image"
4. Confirm transaction in MetaMask (if using)

### Removing Images

1. Enter image name
2. Click "Remove image"
3. Confirm transaction

---

## Development

### Project Structure

```
dashboard/
├── public/           # Static assets
├── src/
│   ├── App.js       # Main component
│   ├── App.css      # Styles
│   ├── Canteen.json # Contract ABI
│   └── index.js     # Entry point
├── .env             # Configuration
└── package.json     # Dependencies
```

### Available Scripts

```bash
# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

### Building for Production

```bash
# Create optimized build
npm run build

# Serve with any web server
npx serve -s build -p 80
```

---

## Deployment

### Static Hosting

```bash
# Build
npm run build

# Deploy to:
# - Netlify: Drop /build folder
# - Vercel: Connect repo
# - GitHub Pages: Copy to gh-pages branch
# - AWS S3: Sync to bucket
```

### Docker

```dockerfile
FROM node:16 as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Build and run:
```bash
docker build -t canteen-dashboard .
docker run -p 80:80 canteen-dashboard
```

---

## Troubleshooting

### Dashboard shows "N/A" for nodes

**Cause:** Can't connect to API or blockchain

**Fix:**
```bash
# 1. Verify node is running
curl http://localhost:3000/cluster

# 2. Check Ganache is running
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  http://localhost:7545

# 3. Update .env with correct values
```

### Can't add/remove images

**Cause:** Wrong contract address or no account

**Fix:**
1. Make sure MetaMask is connected (or Ganache accounts are available)
2. Verify contract address in `.env`
3. Check you have ETH in your account

### CORS errors

**Cause:** Browser blocking cross-origin requests

**Fix:** CORS is already enabled in the main app's web server. If still having issues:
```bash
# Use a CORS proxy for development
REACT_APP_API_URL=https://cors-anywhere.herokuapp.com/http://localhost:3000
```

### Changes to .env not reflected

**Cause:** React caches environment variables

**Fix:**
```bash
# Stop server (Ctrl+C)
# Delete cache
rm -rf node_modules/.cache
# Restart
npm start
```

---

## Integration with Main App

### Complete Setup

```bash
# Terminal 1: Start Ganache
ganache-cli -p 7545

# Terminal 2: Deploy contract
cd /path/to/canteen
npx truffle migrate --network development
# Note the contract address

# Terminal 3: Start main app
npm start

# Terminal 4: Start dashboard
cd dashboard
REACT_APP_CONTRACT_ADDRESS=0xYourAddress npm start
```

### Multiple Nodes

Monitor different nodes by pointing to their APIs:

```bash
# Dashboard 1 -> Node 1
REACT_APP_API_URL=http://localhost:3000 PORT=3001 npm start

# Dashboard 2 -> Node 2
REACT_APP_API_URL=http://localhost:3001 PORT=3002 npm start
```

---

## Technologies

- **React** - UI framework
- **D3.js** - Network visualization
- **Web3.js** - Blockchain interaction
- **styled-components** - CSS-in-JS styling

---

## License

MIT

---

## More Information

- **Configuration Guide**: See `CONFIGURATION_GUIDE.md`
- **Main App Docs**: See `../README.md`
- **API Reference**: See `../COMPLETE_USER_GUIDE.md`

---

Made with ❤️ for decentralized container orchestration
