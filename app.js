const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const bodyParser = require('body-parser');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ noServer: true });

// Middleware for parsing JSON
app.use(bodyParser.json());

// Helper function to simulate synchronous task processing
const syncTaskExample = (data) => {
    // Replace this with the actual sync task logic
    return `Processed data: ${JSON.stringify(data)}`;
};

// Dani WebSocket endpoint
app.get('/dani_test', (req, res) => {
    res.send('Use WebSocket to connect to this endpoint.');
});

server.on('upgrade', (request, socket, head) => {
    const pathname = new URL(request.url, `http://${request.headers.host}`).pathname;

    if (pathname === '/dani_test' || pathname === '/jambonz-websocket') {
        wss.handleUpgrade(request, socket, head, (ws) => {
            if (pathname === '/dani_test') handleDaniWebSocket(ws);
            if (pathname === '/jambonz-salamandra') handlSalamandra(ws);
            if (pathname === '/jambonz-flow') handleFlow(ws);
        });
    } else {
        socket.destroy();
    }
});

// Dani WebSocket handler
const handleDaniWebSocket = (ws) => {
    console.log('Connected to /dani_test');
    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);
            ws.send(JSON.stringify(data));
        } catch (err) {
            console.error('Error parsing message:', err);
        }
    });

    ws.on('close', () => {
        console.log('WebSocket disconnected');
    });

    ws.on('error', (err) => {
        console.error('WebSocket error:', err);
    });
};

// Jambonz WebSocket handler
const handlSalamandra = (ws) => {
    console.log('Connected to /jambonz-salamandra');
    ws.on('message', async (message) => {
        try {
            const data = JSON.parse(message);
            console.log('Received data:', data);

            // Process different types of messages
            if (data.type === 'session:new') {
                const response = {
                    type: 'ack',
                    msgid: data.msgid,
                    data: [
                        {
                            verb: 'gather',
                            say: {
                                text: 'Anem a començar!',
                            },
                            input: ['speech'],
                        },
                    ],
                };
                ws.send(JSON.stringify(response));
            } else if (data.type === 'call:status') {
                console.log('Received call status:', data);
            } else if (data.type === 'verb:hook') {
                const reason = data.data?.reason;
                if (reason === 'speechDetected') {
                    const speech = data.data?.speech?.transcripts[0]?.alternatives[0]?.transcript || 'Sense transcripció';
                    const response = {
                        type: 'ack',
                        msgid: data.msgid,
                        data: [
                            {
                                verb: 'gather',
                                say: {
                                    text: 'Anem a començar!',
                                },
                                input: ['speech'],
                            },
                        ],
                    };
                    ws.send(JSON.stringify(response));
                }
            }

            // Simulate synchronous task processing
            const result = syncTaskExample(data);
            console.log('Sync task result:', result);
        } catch (err) {
            console.error('Error processing message:', err);
        }
    });

    ws.on('close', () => {
        console.log('WebSocket disconnected');
    });

    ws.on('error', (err) => {
        console.error('WebSocket error:', err);
    });
};

// Jambonz WebSocket handler
const handleFlow = (ws) => {
    console.log('Connected to /jambonz-flow');
    ws.on('message', async (message) => {
        try {
            const data = JSON.parse(message);
            console.log('Received data:', data);

            // Process different types of messages
            if (data.type === 'session:new') {
                const response = {
                    type: 'ack',
                    msgid: data.msgid,
                    data: [
                        {
                            input: ['speech'],
                            verb: 'gather',
                            say: {
                                text: 'Ja q asi hi som!',
                            },
                        },
                    ],
                };
                ws.send(JSON.stringify(response));
            } else if (data.type === 'call:status') {
                console.log('Received call status:', data);
            } else if (data.type === 'verb:hook') {
                const reason = data.data?.reason;
                if (reason === 'speechDetected') {
                    const speech =
                        data.data?.speech?.transcripts[0]?.alternatives[0]?.transcript || '';
                    const response = {
                        type: 'command',
                        command: 'redirect',
                        data: [
                            {
                                input: ['speech'],
                                verb: 'gather',
                                say: {
                                    text: speech,
                                },
                            },
                        ],
                    };
                    ws.send(JSON.stringify(response));
                }
            }

            // Simulate synchronous task processing
            const result = syncTaskExample(data);
            console.log('Sync task result:', result);
        } catch (err) {
            console.error('Error processing message:', err);
        }
    });

    ws.on('close', () => {
        console.log('WebSocket disconnected');
    });

    ws.on('error', (err) => {
        console.error('WebSocket error:', err);
    });
};

server.listen(80, () => {
    console.log('Server is running on http://localhost:80');
});
