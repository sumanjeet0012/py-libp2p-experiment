import _ from 'lodash'
import cluster from './cluster'
import scheduler from './scheduler'
import Web3 from 'web3'
import web from './web-server';

const args = _.reduce(process.argv.slice(2), (args, arg) => {
  const [k, v = true] = arg.split('=')
  args[k] = v
  return args
}, {})

const port = args.port || 5000
const webPort = args.webport || 3000
const nodes = args.nodes && args.nodes.split(',') || []

cluster.start(port, nodes)

scheduler.start(new Web3.providers.HttpProvider('http://localhost:7545'),
  '0x8fC4C65e7410a841fdE20f67679C76eFf1Ab8939', // Deployed Canteen contract address
  null) // Use null to let Web3 get an account from Ganache

web.start(webPort);

process.stdin.resume();

process.on('exit', scheduler.cleanup.bind(scheduler));
process.on('SIGINT', scheduler.cleanup.bind(scheduler));