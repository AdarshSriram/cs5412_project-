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
          // console.log(`http://${host}/set+users+${user_id}+point+${lat}+${lon}`)
        fetch(`http://${host}/set+users+${user_id}+point+${lat}+${lon}`, {mode: 'no-cors'})
        .catch(err => {
          console.log(err)
        })
      }, 30000
    );
  }

  port.start(); 
}