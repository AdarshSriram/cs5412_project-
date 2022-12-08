var ws = undefined;
var websocket_created = false;

process_ws_res = (data) => {
    var r = JSON.parse(data);
    if (r.ok === undefined){
        var category = 1;
        if (r.field && r.field.category){
            category = r.field.category
        }
        const obj = {
            lat: r.object.coordinates[1],
            lon: r.object.coordinates[0],
            id: r.nearby.id,
            categoryEnum: category,
            distance_in_m: r.nearby.meters
        }
        return obj
    }
    else {
        return false
    }
}

var notif_queue = []
var notif_id_set = new Set();
var curr_ws_url = undefined;

const NOTIF_MAX_SIZE = 10
const PING_NOTIF_SIZE = 10

onconnect = e => {
 
  const port  =  e.ports[0];

  port.onmessage  =  msg  => {
        if (msg.data.isUrl !== undefined){

            if (websocket_created && !(curr_ws_url === msg.data.data)) {
                ws.close();
                ws = undefined;
                websocket_created = false;
            }
            ws = new WebSocket(msg.data.data);
            websocket_created = true;
            curr_ws_url = msg.data.data;

            console.log("Listening ...")
            
            ws.onmessage  = ({ data }) => {
                const post = process_ws_res(data)
                if (!!post && !notif_id_set.has(post.id)){
                    // port.postMessage(realtime_notif);
                    notif_id_set.add(post.id);
                    notif_queue.push(post);
                }
                if (notif_queue.length == NOTIF_MAX_SIZE){
                    port.postMessage({
                        data: notif_queue,
                        type: "batch"
                    });
                    const last_post = notif_queue.shift();
                    notif_id_set.delete(last_post.id)
                }
            }
    
        }; 
    }

    setInterval(
        () => {
            if (websocket_created){
                var r = []
                if (notif_queue.length < PING_NOTIF_SIZE){
                    r= notif_queue
                }
                else{
                    r = notif_queue.slice(-PING_NOTIF_SIZE)
                }
                const ping = {
                    data: r,
                    type: "recent_notifs"
                }
                port.postMessage(ping);
            }
        }, 3000);

    port.start();
}