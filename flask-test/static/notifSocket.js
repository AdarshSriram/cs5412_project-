// const ws = new WebSocket("ws://localhost:3001");
var ws;
var websocket_created = false;
var we

// Create a broadcast channel to notify about state changes
const broadcastChannel = new BroadcastChannel("WebSocketChannel");

// Mapping to keep track of ports. You can think of ports as
// mediums through we can communicate to and from tabs.
// This is a map from a uuid assigned to each context(tab)
// to its Port. This is needed because Port API does not have
// any identifier we can use to identify messages coming from it.
const  idToPortMap  = {};

// Event handler called when a tab tries to connect to this worker.
onconnect = e => {
  // Get the MessagePort from the event. This will be the
  // communication channel between SharedWorker and the Tab
  const  port  =  e.ports[0];
  port.onmessage  =  msg  => {
        idToPortMap[msg.data.from] =  port;
        if (!websocket_created && msg.data.url !== undefined){
            websocket_created = true;
            ws = new WebSocket(msg.data.url);
            // Let all connected contexts(tabs) know about state cahnges
            ws.onopen = () => broadcastChannel.postMessage({ type: "WSState", state: ws.readyState });
            ws.onclose = () => broadcastChannel.postMessage({ type: "WSState", state: ws.readyState });

            // When we receive data from the server.
            ws.onmessage  = ({ data }) => {
            // Construct object to be passed to handlers
            const parsedData = { data:  JSON.parse(data), type:  "message" }
            if (!parsedData.data.from) {
                // Broadcast to all contexts(tabs). This is because 
                // no particular id was set on the from field here. 
                // We're using this field to identify which tab sent
                // the message
                broadcastChannel.postMessage(parsedData);
            } else {
                // Get the port to post to using the uuid, ie send to
                // expected tab only.
                idToPortMap[parsedData.data.from].postMessage(parsedData);
            }
            };
        }
        else if(msg.data.closeConn){
            ws.close();
        }
  };

  // We need this to notify the newly connected context to know
  // the current state of WS connection.
  if (websocket_created) {
    port.postMessage({ state: ws.readyState, type: "WSState"});
  }
};