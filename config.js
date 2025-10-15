import dotenv from 'dotenv'
import _ from 'lodash'

// Load environment variables from .env file
dotenv.config()

/**
 * Configuration Management
 * Priority: Command-line args > Environment variables > Defaults
 */
class Config {
  constructor() {
    // Parse command-line arguments
    this.args = _.reduce(process.argv.slice(2), (args, arg) => {
      const [k, v = true] = arg.split('=')
      args[k] = v
      return args
    }, {})
  }

  /**
   * Get configuration value with fallback priority:
   * 1. Command-line argument
   * 2. Environment variable
   * 3. Default value
   */
  get(argKey, envKey, defaultValue) {
    // Check command-line argument first
    if (this.args[argKey] !== undefined) {
      return this.args[argKey]
    }
    
    // Check environment variable
    if (process.env[envKey] !== undefined && process.env[envKey] !== '') {
      return process.env[envKey]
    }
    
    // Return default
    return defaultValue
  }

  /**
   * Get integer value
   */
  getInt(argKey, envKey, defaultValue) {
    const value = this.get(argKey, envKey, defaultValue)
    return parseInt(value, 10)
  }

  /**
   * Get boolean value
   */
  getBool(argKey, envKey, defaultValue) {
    const value = this.get(argKey, envKey, defaultValue)
    if (typeof value === 'boolean') return value
    if (typeof value === 'string') {
      return value.toLowerCase() === 'true' || value === '1'
    }
    return defaultValue
  }

  /**
   * Get array value (comma-separated string)
   */
  getArray(argKey, envKey, defaultValue = []) {
    const value = this.get(argKey, envKey, null)
    if (!value) return defaultValue
    if (Array.isArray(value)) return value
    return value.split(',').map(v => v.trim()).filter(v => v)
  }

  // Blockchain Configuration
  getBlockchainProvider() {
    return this.get('provider', 'BLOCKCHAIN_PROVIDER', 'http://localhost:7545')
  }

  getContractAddress() {
    return this.get('contract', 'CONTRACT_ADDRESS', '0x8fC4C65e7410a841fdE20f67679C76eFf1Ab8939')
  }

  getPrivateKey() {
    return this.get('privatekey', 'PRIVATE_KEY', null)
  }

  // Network Configuration
  getP2PPort() {
    return this.getInt('port', 'P2P_PORT', 5000)
  }

  getWebApiPort() {
    return this.getInt('webport', 'WEB_API_PORT', 3000)
  }

  getBootstrapNodes() {
    return this.getArray('nodes', 'BOOTSTRAP_NODES', [])
  }

  // Docker Configuration
  getDockerSocket() {
    return this.get('dockersocket', 'DOCKER_SOCKET', '/var/run/docker.sock')
  }

  // Scheduler Configuration
  getSchedulerPollInterval() {
    return this.getInt('pollinterval', 'SCHEDULER_POLL_INTERVAL', 1000)
  }

  // Logging Configuration
  getLogLevel() {
    return this.get('loglevel', 'LOG_LEVEL', 'info')
  }

  /**
   * Print current configuration
   */
  print() {
    console.log('=== Canteen Configuration ===')
    console.log(`Blockchain Provider: ${this.getBlockchainProvider()}`)
    console.log(`Contract Address: ${this.getContractAddress()}`)
    console.log(`Private Key: ${this.getPrivateKey() ? '***HIDDEN***' : 'Auto (Ganache)'}`)
    console.log(`P2P Port: ${this.getP2PPort()}`)
    console.log(`Web API Port: ${this.getWebApiPort()}`)
    console.log(`Bootstrap Nodes: ${this.getBootstrapNodes().join(', ') || 'None'}`)
    console.log(`Docker Socket: ${this.getDockerSocket()}`)
    console.log(`Poll Interval: ${this.getSchedulerPollInterval()}ms`)
    console.log(`Log Level: ${this.getLogLevel()}`)
    console.log('=============================\n')
  }
}

export default new Config()
