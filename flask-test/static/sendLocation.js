if (!!window.SharedWorker && navigator.geolocation) {
  var worker = new SharedWorker("{{url_for('static', filename='common.js')}}");
  
  worker.port.start(); 

  worker.port.onmessage = function(e){}; 

  navigator.geolocation.getCurrentPosition(sendLocation);

  function sendLocation(position) {
          const msg = {
              lat : position.coords.latitude,
              lon : position.coords.longitude,
              host : '{{host}}',
              user_id : '{{user_id}}'
          }
          worker.port.postMessage(msg);
          console.log('{{user_id}}');
      }

}