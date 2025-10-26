# FHE Credit Score Server

Privacy-preserving credit score calculation using Fully Homomorphic Encryption (FHE) with Zama's Concrete library.

## 🎯 Overview

This is a **server application** that computes credit scores on **encrypted data** without ever seeing the actual values. Built using:
- **Zama's Concrete FHE** - For homomorphic encryption
- **Flask** - Web server
- **Docker** - Containerization

## 🏗️ Architecture

```
┌─────────┐                      ┌─────────┐
│ Client  │                      │ Server  │
│         │                      │         │
│ 1. Encrypt data ────────────► │         │
│                                │ 2. Compute on │
│                                │    encrypted  │
│                                │    data       │
│ 4. Decrypt result ◄─────────── │ 3. Return     │
│                                │    encrypted  │
│                                │    result     │
└─────────┘                      └─────────┘
   ✓ Has private key               ✗ Never sees
   ✓ Sees plaintext                  actual values
```

## 🚀 Quick Start

### Option 1: Using Docker (Recommended)

1. **Build and run:**
```bash
docker-compose up --build
```

2. **Server will be available at:** `http://localhost:5000`

### Option 2: Local Python

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run server:**
```bash
python encrypted_credit_score_simple.py
```

## 📡 API Endpoints

### GET /health
Check server health and readiness.

**Response:**
```json
{
  "status": "healthy",
  "service": "FHE Credit Score Server",
  "ready": true
}
```

### GET /info
Get server information and available endpoints.

### POST /compute
Compute credit score on encrypted data.

**Request:**
```json
{
  "encrypted_data": "base64_encoded_encrypted_inputs"
}
```

**Response:**
```json
{
  "status": "success",
  "encrypted_result": "base64_encoded_encrypted_score"
}
```

## 💻 Using the Client

### Run with default values:
```bash
python client.py
```

### Run with custom values:
```bash
python client.py \
  --salary 60000 \
  --loan 15000 \
  --history 48 \
  --delays 1 \
  --server http://localhost:5000
```

### Client workflow:
1. Compiles FHE circuit locally (gets encryption keys)
2. Encrypts your financial data
3. Sends encrypted data to server
4. Server computes on encrypted data
5. Client decrypts the result

## 🔧 Docker Commands

```bash
# Build image
docker build -t fhe-credit-server .

# Run container
docker run -p 5000:5000 fhe-credit-server

# Using docker-compose
docker-compose up -d          # Start in background
docker-compose logs -f        # View logs
docker-compose down           # Stop
```

## 📊 Example

```bash
# Terminal 1: Start server
docker-compose up

# Terminal 2: Run client
python client.py --salary 80000 --loan 10000 --history 60 --delays 0
```

**Output:**
```
✓ Server status: healthy
[CLIENT] Compiling FHE circuit locally...
[CLIENT] ✓ Circuit compiled!
[CLIENT] Encrypting financial data...
  Salary: $80,000
  Loan: $10,000
  Credit History: 60 months
  Payment Delays: 0
[CLIENT] ✓ Data encrypted!
[CLIENT] Sending encrypted data to server...
[SERVER] Computing on encrypted data...
[CLIENT] ✓ Server computed successfully!
[CLIENT] Decrypting result...
[CLIENT] ✓ Your credit score: 826

FINAL RESULT
Credit Score: 826
Rating: Excellent

✓ Privacy preserved - server never saw your actual data!
```

## 🔐 Privacy Guarantee

- ✅ All sensitive data encrypted on client side
- ✅ Server computes on encrypted values only
- ✅ Server **never sees** actual salary, loan amounts, etc.
- ✅ Only client can decrypt the result
- ✅ Mathematically guaranteed privacy via FHE

## 📦 Files

- `encrypted_credit_score_simple.py` - FHE server
- `client.py` - Client for sending encrypted requests
- `requirements.txt` - Python dependencies
- `Dockerfile` - Docker image configuration
- `docker-compose.yml` - Docker Compose configuration
- `README.md` - This file

## ⚡ Performance

- **Server startup:** ~2-5 seconds (circuit compilation)
- **Per request:** ~1-2 seconds
- **Resource usage:** Moderate CPU, minimal memory

## 🛠️ Configuration

### Environment Variables

- `PORT` - Server port (default: 5000)

### Docker Build Options

For faster builds during development:
```bash
docker build --build-arg BUILDKIT_INLINE_CACHE=1 -t fhe-credit-server .
```

## 🧪 Testing

Test the server:
```bash
# Check health
curl http://localhost:5000/health

# Get info
curl http://localhost:5000/info

# Compute score (need client)
python client.py
```

## 🚨 Important Notes

1. **Demo Mode**: Currently uses `enable_unsafe_features=True` for speed. For production, use secure configuration.
2. **Keys**: Client generates keys locally. In production, implement proper key management.
3. **Network**: Client and server must use **identical** FHE circuits for compatibility.

## 📚 How It Works

### Credit Score Algorithm

The server computes credit scores based on:
1. **Debt-to-Income Ratio** - Lower is better
2. **Credit History Length** - Longer is better
3. **Payment History** - Fewer delays is better

**Score Range:** 300-850 (similar to FICO)

### FHE Magic

```python
# Client side
encrypted_data = circuit.encrypt(salary, loan, history, delays)

# Server side (never sees plaintext!)
encrypted_score = compute(encrypted_data)

# Client side
score = circuit.decrypt(encrypted_score)  # Only client can decrypt!
```

## 🤝 Real-World Applications

This privacy-preserving pattern can be applied to:
- 💳 Credit scoring & loan approval
- 🏥 Medical diagnosis
- 🏦 Financial risk assessment
- 📊 Private analytics
- 🔍 Background checks

## 📄 License

For educational and demonstration purposes.

## 🙏 Acknowledgments

Built with [Zama's Concrete](https://github.com/zama-ai/concrete) FHE library.

---

**Built with 🔐 for privacy-preserving computation**
