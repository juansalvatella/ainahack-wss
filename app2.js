/* create an http/s server in your application however you like */
const {createServer} = require('http');
const server = createServer();
server.listen(3000);

/* require the library and call the returned function with your server */
const {createEndpoint} = require('@jambonz/node-client-ws');
const makeService = createEndpoint({server});

/* create a jambonz application listeng for requests with URL path '/hello-world' */
const svc = makeService({path: '/hello-world'});

/* listen for new calls to that service */
svc.on('session:new', (session) => {
  /* the 'session' object has all of the properties of the incoming call */
  console.log({session}, `new incoming call: ${session.call_sid}`);

  /* set up some event handlers for this session */
  session
    .on('close', onClose.bind(null, session))
    .on('error', onError.bind(null, session));

  /* all of the jambonz verbs are available as methods on the session object 
     https://www.jambonz.org/docs/webhooks/overview/
  */
  session
    .pause({length: 1.5})
    .say({text})
    .pause({length: 0.5})
    .hangup()
    .send(); // sends the queued verbs to jambonz
});

const onClose = (session, code, reason) => {
  console.log({session, code, reason}, `session ${session.call_sid} closed`);
};

const onError = (session, err) => {
  console.log({err}, `session ${session.call_sid} received error`);
};
