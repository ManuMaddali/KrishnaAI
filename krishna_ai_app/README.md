# KrishnaAI Mobile and Web App

This is a Flutter implementation of KrishnaAI that works across web, iOS, and Android platforms.

## Setup

1. Make sure Flutter is installed on your system
2. Run `flutter pub get` to install dependencies
3. Make sure the KrishnaAI Flask backend is running on localhost:5000

## Running the App

### Web
```
flutter run -d chrome
```

### iOS
```
flutter run -d ios
```
You'll need Xcode installed for iOS development.

### Android
```
flutter run -d android
```
You'll need Android Studio installed for Android development.

## Building for Production

### Web
```
flutter build web
```

### iOS
```
flutter build ios
```
Then open the iOS project in Xcode to create an archive.

### Android
```
flutter build apk
```
Or for app bundle:
```
flutter build appbundle
```

## Configuration

To connect to a different backend server, update the `baseUrl` parameter in the ApiService initialization in `lib/main.dart`.
