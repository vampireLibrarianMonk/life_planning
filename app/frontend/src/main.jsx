import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { installDeviceMode } from './services/device'

// Tag <html> with data-device="mobile|desktop" before first paint of the app.
installDeviceMode()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
