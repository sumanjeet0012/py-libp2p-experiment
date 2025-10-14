import Hyperswarm from 'hyperswarm'
import _ from 'lodash'
import crypto from 'crypto'

class CanteenCluster {
  constructor() {
    this.members = new Set()
    this.swarm = null
    this.host = null
  }

  getHost() {
    return this.host
  }

  getProtocol() {
    return this.swarm
  }

  getMembers() {
    return Array.from(this.members)
  }

  start(port, nodes) {
    this.host = `127.0.0.1:${port}`
    
    // Create hyperswarm instance
    const swarm = new Hyperswarm()
    
    // Create a topic for the canteen cluster
    const topic = crypto.createHash('sha256')
      .update('canteen-cluster')
      .digest()
    
    console.log(`Starting Hyperswarm on port ${port}...`)
    console.log(`Joining ${nodes.length} specified bootstrap node(s).`)
    
    // Join the cluster topic
    const discovery = swarm.join(topic, {
      server: true,  // Accept connections
      client: true   // Make connections
    })
    
    // Wait for the topic to be fully announced
    discovery.flushed().then(() => {
      console.log(`Cluster topic announced`)
    })
    
    // Handle new peer connections
    swarm.on('connection', (socket, peerInfo) => {
      const peerId = peerInfo.publicKey.toString('hex').slice(0, 8)
      
      if (!this.members.has(peerId)) {
        this.members.add(peerId)
        console.log(`Cluster members: ${this.members.size > 0 ? '[' + Array.from(this.members).join(', ') + ']' : 'None.'}`)
      }
      
      socket.on('error', () => {
        this.members.delete(peerId)
        console.log(`Cluster members: ${this.members.size > 0 ? '[' + Array.from(this.members).join(', ') + ']' : 'None.'}`)
      })
      
      socket.on('close', () => {
        this.members.delete(peerId)
        console.log(`Cluster members: ${this.members.size > 0 ? '[' + Array.from(this.members).join(', ') + ']' : 'None.'}`)
      })
    })
    
    this.swarm = swarm
  }
}

export default new CanteenCluster()