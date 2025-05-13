#!/bin/bash

# Setup script for KrishnaAI mobile app deployment

echo "Setting up KrishnaAI for mobile deployment..."

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "npm is not installed. Please install Node.js and npm first."
    exit 1
fi

# Install Capacitor CLI
echo "Installing Capacitor CLI..."
npm install -g @capacitor/cli

# Create package.json if it doesn't exist
if [ ! -f "package.json" ]; then
    echo "Creating package.json..."
    cat > package.json << EOF
{
  "name": "krishna-ai",
  "version": "1.0.0",
  "description": "KrishnaAI - Your Spiritual Guide",
  "main": "app.py",
  "scripts": {
    "start": "python app.py",
    "build-mobile": "capacitor sync"
  },
  "author": "",
  "license": "MIT",
  "dependencies": {
    "@capacitor/android": "^5.0.0",
    "@capacitor/core": "^5.0.0",
    "@capacitor/ios": "^5.0.0"
  }
}
EOF
fi

# Install Capacitor dependencies
echo "Installing Capacitor dependencies..."
npm install @capacitor/core @capacitor/cli @capacitor/ios @capacitor/android

# Initialize Capacitor
echo "Initializing Capacitor..."
npx cap init KrishnaAI com.krishna.ai --web-dir=static

# Create Capacitor config
echo "Creating capacitor.config.json..."
cat > capacitor.config.json << EOF
{
  "appId": "com.krishna.ai",
  "appName": "KrishnaAI",
  "webDir": "static",
  "bundledWebRuntime": false,
  "server": {
    "hostname": "localhost",
    "androidScheme": "https"
  }
}
EOF

# Add iOS and Android platforms
echo "Adding iOS and Android platforms..."
npx cap add ios
npx cap add android

echo "Setting up static files for mobile..."
mkdir -p static/js
mkdir -p static/css
mkdir -p static/img

# Create placeholder icons
echo "Creating placeholder icons (replace with actual icons later)..."
mkdir -p static
touch static/icon-192x192.png
touch static/icon-512x512.png
touch static/apple-touch-icon.png
touch static/favicon.png

# Copy templates to static
echo "Creating wrapper index.html in static directory..."
cat > static/index.html << EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0;url=/">
    <title>Redirecting to KrishnaAI</title>
</head>
<body>
    <script>
        window.location.href = "/";
    </script>
    <p>If you are not redirected, <a href="/">click here</a>.</p>
</body>
</html>
EOF

echo "Creating README for mobile deployment..."
cat > MOBILE_DEPLOYMENT.md << EOF
# KrishnaAI Mobile Deployment

This document explains how to build and deploy the KrishnaAI app to iOS and Android app stores.

## Prerequisites

- Xcode 13+ (for iOS)
- Android Studio (for Android)
- Node.js and npm
- Capacitor CLI

## Building for iOS

1. Ensure you have Xcode installed
2. Run: \`npx cap sync ios\`
3. Run: \`npx cap open ios\`
4. In Xcode, configure your signing identity
5. Build and archive the app for App Store distribution

## Building for Android

1. Ensure you have Android Studio installed
2. Run: \`npx cap sync android\`
3. Run: \`npx cap open android\`
4. In Android Studio, build the app for release
5. Generate a signed APK/AAB for Google Play Store

## Development Notes

- Update app icons in the static directory
- Test on physical devices before submission
- Consider API connectivity issues on mobile networks
- Implement push notifications for better engagement

## API Configuration

The mobile app connects to your Flask backend. For production:

1. Set up a proper production server (not Flask's development server)
2. Configure a domain with SSL
3. Update the server URLs in capacitor.config.json
EOF

# Make the script executable
chmod +x setup_mobile.sh

echo "Setup complete!"
echo "Run 'npx cap sync' to update your mobile projects"
echo "Run 'npx cap open ios' to open the iOS project in Xcode"
echo "Run 'npx cap open android' to open the Android project in Android Studio"
echo "See MOBILE_DEPLOYMENT.md for more details on app store submission" 