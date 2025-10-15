import cluster from './cluster'
import express from 'express';
import _ from 'lodash';
import http from 'http';

class WebServer {
  start(port = 3000) {
    const app = express()

    const clusterDetails = (req, res) => {
      const swarm = cluster.getProtocol();
      const host = cluster.getHost();
      
      // With Hyperswarm, we get members from the cluster module
      const members = cluster.getMembers();
      
      // Include current host in the members list
      const allMembers = [host].concat(members);
      
      res.status(200).json({members: allMembers});
    }

    app.use((req, res, next) => {
      res.header("Access-Control-Allow-Origin", "*");
      res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
      next();
    });

    app.get('/', clusterDetails)
    app.get('/cluster', clusterDetails);

    try {
      const server = http.createServer(app);
      server.on('error', err => {
        console.error(err);
      });
      server.listen(port);
      console.log(`Cluster health check web service is listening on port ${port}`)
    } catch (error) {
      console.log(error.message);
    }
  }
}

export default new WebServer();

