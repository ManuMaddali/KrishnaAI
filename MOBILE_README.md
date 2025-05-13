# KrishnaAI Mobile Deployment Guide

This guide provides instructions for deploying the KrishnaAI application as both a Progressive Web App (PWA) and native mobile apps for iOS and Android stores.

## Table of Contents
- [PWA Deployment](#pwa-deployment)
- [Native App Deployment with Capacitor](#native-app-deployment-with-capacitor)
- [iOS App Store Deployment](#ios-app-store-deployment)
- [Android Play Store Deployment](#android-play-store-deployment)
- [Mobile-Specific Features](#mobile-specific-features)
- [Troubleshooting](#troubleshooting)

## PWA Deployment

The KrishnaAI app is already configured as a Progressive Web App with the following files:
- `/static/manifest.json` - App metadata and icons
- `/static/service-worker.js` - Caching and offline functionality
- Mobile-optimized UI in the HTML templates

### Testing PWA Locally

1. Run the app with:
```bash
python app.py
```

2. Access the app from a mobile device on the same network by using your computer's IP address: 
```
http://YOUR_COMPUTER_IP:5000
```

3. On Chrome/Safari mobile, you should see an "Add to Home Screen" option when visiting the site.

### Deploying the PWA to Production

1. Set up a proper production server (Gunicorn, uWSGI, etc.):
```bash
pip install gunicorn
gunicorn -w 4 app:app
```

2. Configure a domain with HTTPS (required for PWAs)
3. Update the `start_url` in the manifest.json file with your production URL

## Native App Deployment with Capacitor

We've provided the `setup_mobile.sh` script to prepare your project for native app deployment using Capacitor.

### Prerequisites

- Node.js and npm
- Xcode 14+ (for iOS)
- Android Studio (for Android)

### Setup

1. Run the setup script:
```bash
./setup_mobile.sh
```

2. This will:
   - Install Capacitor dependencies
   - Create necessary configuration files
   - Set up iOS and Android projects

3. Start your Flask app:
```bash
python app.py
```

4. Update the Capacitor config (if needed):
   - Edit `capacitor.config.json` to point to your production server for release builds

### Building the Apps

1. Sync your web content with the native projects:
```bash
npx cap sync
```

2. Open native projects:
```bash
# For iOS
npx cap open ios

# For Android
npx cap open android
```

## iOS App Store Deployment

1. In Xcode, configure your app:
   - Set up signing identity with an Apple Developer account
   - Configure app capabilities (Push, etc.)
   - Set appropriate app metadata (icons, etc.)

2. Create an app record in App Store Connect

3. Build the app for distribution:
   - Select `Product > Archive`
   - Upload to App Store using the Organizer

4. Complete App Store submission:
   - Age rating
   - App description
   - Screenshots
   - Privacy policy
   - Review information

## Android Play Store Deployment

1. In Android Studio, configure your app:
   - Update app/build.gradle with proper version codes
   - Configure app signing

2. Build a release APK or AAB:
   - `Build > Generate Signed Bundle/APK`
   - Follow the signing wizard

3. Create a developer account on Google Play Console

4. Complete app submission:
   - Upload the signed APK/AAB
   - Add store listing details
   - Screenshots and promotional graphics
   - Content rating survey
   - Pricing and distribution

## Mobile-Specific Features

### Handling Offline Mode

The service worker is configured to cache essential assets and provide offline functionality:
- Core UI elements
- Basic chat interface
- Previously loaded scriptures

Network-dependent features like new chat messages will require internet connectivity.

### Suggested Enhancements

1. **Push Notifications**:
   - Implement notifications for new features or spiritual reminders
   - Add the required Capacitor plugins:
   ```bash
   npm install @capacitor/push-notifications
   npx cap sync
   ```

2. **Biometric Authentication**:
   - Secure private conversations with fingerprint/face ID
   - Add the authentication plugin:
   ```bash
   npm install @capacitor/biometric-auth
   npx cap sync
   ```

3. **Deep Linking**:
   - Allow sharing specific scripture passages
   - Configure in capacitor.config.json

## Troubleshooting

### Common Issues

1. **App doesn't load on device**:
   - Ensure your Flask server is running on `0.0.0.0` (not `127.0.0.1`)
   - Check if your device can access your development machine's IP

2. **Service worker not registering**:
   - Verify that service-worker.js is being served from the root path
   - Check browser console for errors

3. **Native plugin issues**:
   - Run `npx cap doctor` to diagnose problems
   - Ensure capacitor is properly synced: `npx cap sync`

4. **iOS build failures**:
   - Update CocoaPods: `sudo gem install cocoapods`
   - Try: `cd ios/App && pod install`

5. **Android build failures**:
   - Update Android Studio and Gradle
   - Check Java version compatibility

### Getting Help

For specific issues, consult:
- [Capacitor Documentation](https://capacitorjs.com/docs)
- [Flask Documentation](https://flask.palletsprojects.com/)
- GitHub issues for similar projects

## License

This project is licensed under the MIT License - see the LICENSE file for details. 