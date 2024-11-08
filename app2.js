const {createServer} = require('http');
const {createEndpoint} = require('@jambonz/node-client-ws');
const server = createServer();
const { WebSocketServer } = require('ws');

// create two external websocket servers on this http server
const wssSalamandra = new WebSocketServer({ noServer: true });
const wssExtension = new WebSocketServer({ noServer: true });

// paths /foo and /bar should come to us, node-client-ws will handle the rest
const makeService = createEndpoint({
  server,
  externalWss: [
    {
      path: '/salamandra',
      wss: wssSalamandra
    },
    {
      path: '/extension',
      wss: wssExtension
    }
  ]
});

const logger = require('pino')({level: process.env.LOGLEVEL || 'info'});
const port = process.env.WS_PORT || 80;

server.listen(port, () => {
  logger.info(`jambonz websocket server listening at http://localhost:${port}`);
});

// Handle connections and messages for /foo WebSocket server
wssSalamandra.on('connection', (ws) => {
  logger.info('connection to /salamandra');
  ws.on('message', (message) => {
    logger.info(`received message on /salamandra: ${message}`);
    ws.send('foo'); // Reply with 'foo' text frame
  });
});

// Handle connections and messages for /bar WebSocket server
wssExtension.on('connection', (ws) => {
  logger.info('connection to /extension');
  ws.on('message', (message) => {
    logger.info(`received message on /extension: ${message}`);
    ws.send(message); // Reply with 'bar' text frame
  });
});
