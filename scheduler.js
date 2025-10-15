import Web3 from 'web3'
import Canteen from './build/contracts/Canteen.json'
import Docker from 'dockerode'
import _ from 'lodash'
import Cluster from './cluster'
import config from './config'

class CanteenScheduler {
  async start(provider, contractAddress, privateKey) {
    const web3 = new Web3(provider)
    
    // Get account - either from Ganache or create new one
    let account
    if (privateKey) {
      account = web3.eth.accounts.wallet.add(web3.eth.accounts.privateKeyToAccount(privateKey))
    } else {
      // Get first account from Ganache (pre-funded with 100 ETH)
      const accounts = await web3.eth.getAccounts()
      if (accounts.length === 0) {
        throw new Error('No accounts available in Ganache')
      }
      account = { address: accounts[0] }
      console.log(`Using Ganache account: ${account.address}`)
    }

    const contract = new web3.eth.Contract(Canteen.abi, contractAddress, {from: account.address})

    // Use Docker socket from config
    const docker = new Docker({socketPath: config.getDockerSocket()})

    this.docker = docker
    this.contract = contract
    this.account = account
    this.web3 = web3

    try {
      await this.registerNode()
      // Use poll interval from config
      const pollInterval = config.getSchedulerPollInterval()
      setInterval(async () => await this.loop(), pollInterval)
    } catch (error) {
      console.error(error)
    }

    // await this.updateScheduler('rethinkdb:latest')
    // await this.updateScheduler('crccheck/hello-world')
  }

  async loop() {
    // Loops to check if scheduled image for this given node changed.

    const {contract, web3} = this

    const details = await contract.methods.getMemberDetails(Cluster.getHost()).call()
    const scheduledImage = details['0']

    // Check if scheduled image is available.
    if (!details) return
    // Check if scheduled image is unique.
    if (this.scheduledImage === scheduledImage) return

    if (this.scheduledImage && this.scheduledImage.length > 0 && scheduledImage.length === 0) {
      // Node no longer has to schedule. Clean up.

      await this.cleanup()
    } else {
      // Update image.
      await this.updateScheduler(scheduledImage)
    }
  }

  async registerNode() {
    const {contract, account, web3} = this

    const registerMember = contract.methods.addMember(Cluster.getHost())

    try {
      registerMember.send({
        from: account.address,
        gas: await registerMember.estimateGas()
      })

      console.log('Node has been registered on Canteen.')
    } catch (error) {
      if (error.message === 'Returned error: VM Exception while processing transaction: revert') {
        console.log('Node seems to have existed previously on Canteen. Reinstantiating...')
      } else {
        throw error
      }
    }
  }

  async updateScheduler(scheduledImage) {
    this.scheduledImage = scheduledImage
    if (this.scheduledImage.length === 0) return

    this.docker.pull(scheduledImage, (err, stream) => {
      if (err) {
        console.error('Error pulling image:', err.message)
        return
      }
      
      if (!stream) {
        console.error('No stream returned from docker.pull')
        return
      }

      console.log('')

      this.docker.modem.followProgress(stream, finished.bind(this), progress)

      function progress(event) {
        console.log(`${event.status}${event.id && ` ID: ${event.id}` || ''}`)
      }

      async function finished() {
        console.log('')

        const containers = await this.docker.listContainers()

        console.log(`Starting up a container with the image '${scheduledImage}'.`)

        const containerStatus = _.find(containers, {Image: scheduledImage})

        const scheduleImage = async () => {
          const containers = await this.docker.listContainers()
          const containerStatus = _.find(containers, {Image: scheduledImage})

          let container
          if (!containerStatus) {
            // Create a new container if not exist.

            const port = scheduledImage.includes("hello-world") ? 8000 : 8080;

            container = await this.docker.createContainer({
              Image: scheduledImage,
              ExposedPorts: {
                [`${port}/tcp`]: {},

              },
              HostConfig: {
                // ExposeAllPorts: true,
                PortBindings: {
                  [`${port}/tcp`]: [{HostPort: `${port}`}],
                }
              }
            })

            console.log('Successfully created a new container and binded it to the scheduler.')
          } else {
            // Get reference to the container.

            container = this.docker.getContainer(containerStatus['Id'])
            console.log('Found a stopped container; started it and binded it to the scheduler.')
          }

          // Wipe out the old container.
          const oldContainer = this.container
          if (oldContainer) {
            console.log('Stopping and removing prior image binded to the scheduler.')
            await oldContainer.stop()
            await oldContainer.remove()
          }

          // Run the new (or paused) container.
          await container.start()

          console.log(`Node and scheduler is ready. Container ID is: ${container.id}`)

          this.container = container
        }

        if (containerStatus && containerStatus.State === 'running') {
          let container = this.docker.getContainer(containerStatus['Id'])
          await container.stop()
          await container.remove()

          console.log(`Found an existing running container; removing it...`)

          setTimeout(async () => await scheduleImage(), 3000)
        } else {
          await scheduleImage()
        }
      }
    })
  }

  async cleanup() {
    console.log('Scheduler stopping; stopping and removing binded container.')

    if (this.container) {
      try {
        await this.container.stop()
        await this.container.remove()
        console.log('Container stopped and removed successfully.')
      } catch (error) {
        // Container might already be stopped or removed
        console.log('Container cleanup skipped (already stopped/removed).')
      }

      this.scheduledImage = ''
      this.container = null
    } else {
      console.log('No container to cleanup.')
    }
  }
}

export default new

CanteenScheduler()