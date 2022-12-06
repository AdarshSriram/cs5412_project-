onconnect = function (event) {
  const port = event.ports[0]

  port.onmessage = function (e) {
    const data = e.data
    const lat = data.lat
    const lon = data.lon
    const user_id = data.user_id
    const host = data.host

    setInterval(
        () => {
        fetch(`http://${host}/set+users+${user_id}+point+${lat}+${lon}`, {mode: 'no-cors'})
        .catch(err => port.postMessage(err))
      }, 60000
    );
  }

  port.start(); 
}