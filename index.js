import cluster from './cluster'
import scheduler from './scheduler'
import Web3 from 'web3'
import web from './web-server'
import config from './config'

// Print configuration
config.print()

// Start cluster with configuration
cluster.start(config.getP2PPort(), config.getBootstrapNodes())

// Start scheduler with configuration
scheduler.start(
  new Web3.providers.HttpProvider(config.getBlockchainProvider()),
  config.getContractAddress(),
  config.getPrivateKey()
)

// Start web server with configuration
web.start(config.getWebApiPort());

process.stdin.resume();

process.on('exit', scheduler.cleanup.bind(scheduler));
process.on('SIGINT', scheduler.cleanup.bind(scheduler));