function triggerEmergency() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function (position) {
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;

            // Send location to the server
            fetch('/emergency', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    latitude: latitude,
                    longitude: longitude
                })
            })
            .then(response => response.json())
            .then(data => {
                alert('Emergency activated! Your location has been sent.');
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to send emergency data.');
            });
        });
    } else {
        alert('Geolocation is not supported by your browser.');
    }
}