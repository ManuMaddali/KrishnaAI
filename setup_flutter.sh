#!/bin/bash

# KrishnaAI Flutter Setup Script
# This script sets up a Flutter project for KrishnaAI that works on web, iOS, and Android

echo "====== KrishnaAI Flutter Setup ======"
echo "Setting up Flutter for multi-platform deployment"

# Check if Flutter is installed
if ! command -v flutter &> /dev/null; then
    echo "Flutter not found. Installing Flutter..."
    
    # Create a directory for Flutter SDK
    mkdir -p ~/development
    cd ~/development
    
    # Download and extract Flutter SDK (adjust for your OS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        curl -O https://storage.googleapis.com/flutter_infra_release/releases/stable/macos/flutter_macos_3.19.3-stable.zip
        unzip flutter_macos_3.19.3-stable.zip
        export PATH="$PATH:$HOME/development/flutter/bin"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl -O https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.19.3-stable.tar.xz
        tar xf flutter_linux_3.19.3-stable.tar.xz
        export PATH="$PATH:$HOME/development/flutter/bin"
    else
        echo "Unsupported OS. Please install Flutter manually from https://flutter.dev/docs/get-started/install"
        exit 1
    fi
    
    # Add Flutter to PATH permanently
    echo 'export PATH="$PATH:$HOME/development/flutter/bin"' >> ~/.zshrc
    echo 'export PATH="$PATH:$HOME/development/flutter/bin"' >> ~/.bashrc
    
    # Go back to original directory
    cd -
    
    echo "Flutter installed successfully."
else
    echo "Flutter already installed. Continuing..."
fi

# Accept Android licenses
flutter doctor --android-licenses || true

# Create mobile app directory
APP_DIR="krishna_ai_app"
mkdir -p $APP_DIR

# Creating Flutter project
echo "Creating Flutter project..."
flutter create --platforms=android,ios,web --org=com.krishna $APP_DIR

# Create necessary files for the app
echo "Setting up Flutter app files..."

# Create API service
mkdir -p $APP_DIR/lib/services
cat > $APP_DIR/lib/services/api_service.dart << 'EOF'
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  final String baseUrl;
  String? _sessionId;
  
  // Default to localhost for development
  ApiService({this.baseUrl = 'http://localhost:5000'});
  
  Future<void> _initSessionId() async {
    if (_sessionId != null) return;
    
    final prefs = await SharedPreferences.getInstance();
    _sessionId = prefs.getString('session_id');
  }
  
  Future<void> _saveSessionId(String sessionId) async {
    _sessionId = sessionId;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('session_id', sessionId);
  }
  
  Future<Map<String, dynamic>> sendMessage(String message) async {
    await _initSessionId();
    
    final response = await http.post(
      Uri.parse('$baseUrl/ask'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'message': message}),
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to send message: ${response.body}');
    }
  }
  
  Future<List<Map<String, dynamic>>> getConversations() async {
    final response = await http.get(Uri.parse('$baseUrl/get_conversations'));
    
    if (response.statusCode == 200) {
      final Map<String, dynamic> data = jsonDecode(response.body);
      return List<Map<String, dynamic>>.from(data['sessions'] ?? []);
    } else {
      throw Exception('Failed to load conversations');
    }
  }
  
  Future<Map<String, dynamic>> resetConversation() async {
    final response = await http.post(
      Uri.parse('$baseUrl/reset'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({}),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data['success'] && data['session_id'] != null) {
        await _saveSessionId(data['session_id']);
      }
      return data;
    } else {
      throw Exception('Failed to reset conversation');
    }
  }
  
  Future<List<Map<String, dynamic>>> getScriptures() async {
    final response = await http.get(Uri.parse('$baseUrl/get_scriptures'));
    
    if (response.statusCode == 200) {
      final Map<String, dynamic> data = jsonDecode(response.body);
      return List<Map<String, dynamic>>.from(data['scriptures'] ?? []);
    } else {
      throw Exception('Failed to load scriptures');
    }
  }
  
  Future<Map<String, dynamic>> getScripture(String scriptureId, int page) async {
    final response = await http.get(
      Uri.parse('$baseUrl/get_scripture/$scriptureId?page=$page'),
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load scripture');
    }
  }
}
EOF

# Create models
mkdir -p $APP_DIR/lib/models
cat > $APP_DIR/lib/models/message.dart << 'EOF'
class Message {
  final String content;
  final String sender;
  final DateTime timestamp;
  
  Message({
    required this.content,
    required this.sender,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();
  
  factory Message.fromJson(Map<String, dynamic> json) {
    return Message(
      content: json['content'],
      sender: json['sender'],
      timestamp: DateTime.parse(json['timestamp']),
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'content': content,
      'sender': sender,
      'timestamp': timestamp.toIso8601String(),
    };
  }
}
EOF

cat > $APP_DIR/lib/models/scripture.dart << 'EOF'
class Scripture {
  final String id;
  final String name;
  
  Scripture({
    required this.id,
    required this.name,
  });
  
  factory Scripture.fromJson(Map<String, dynamic> json) {
    return Scripture(
      id: json['id'],
      name: json['name'],
    );
  }
}

class ScriptureVerse {
  final int verseNum;
  final String text;
  
  ScriptureVerse({
    required this.verseNum,
    required this.text,
  });
  
  factory ScriptureVerse.fromJson(Map<String, dynamic> json) {
    return ScriptureVerse(
      verseNum: json['verse_num'],
      text: json['text'],
    );
  }
}

class ScriptureContent {
  final String title;
  final int page;
  final int totalPages;
  final List<ScriptureVerse> verses;
  
  ScriptureContent({
    required this.title,
    required this.page,
    required this.totalPages,
    required this.verses,
  });
  
  factory ScriptureContent.fromJson(Map<String, dynamic> json) {
    return ScriptureContent(
      title: json['title'],
      page: json['page'],
      totalPages: json['total_pages'],
      verses: (json['verses'] as List)
          .map((v) => ScriptureVerse.fromJson(v))
          .toList(),
    );
  }
}
EOF

# Create screens
mkdir -p $APP_DIR/lib/screens
cat > $APP_DIR/lib/screens/chat_screen.dart << 'EOF'
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/message.dart';
import 'scripture_screen.dart';

class ChatScreen extends StatefulWidget {
  final ApiService apiService;
  
  const ChatScreen({Key? key, required this.apiService}) : super(key: key);

  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _textController = TextEditingController();
  final List<Message> _messages = [];
  bool _isLoading = false;
  
  @override
  void initState() {
    super.initState();
    _resetConversation();
  }
  
  void _resetConversation() async {
    try {
      await widget.apiService.resetConversation();
      setState(() {
        _messages.clear();
      });
    } catch (e) {
      _showError('Failed to reset conversation: $e');
    }
  }
  
  void _handleSubmitted(String text) async {
    if (text.trim().isEmpty) return;
    
    _textController.clear();
    
    // Add user message
    setState(() {
      _messages.add(Message(
        content: text,
        sender: 'user',
      ));
      _isLoading = true;
    });
    
    try {
      // Send message to API
      final response = await widget.apiService.sendMessage(text);
      
      // Parse scripture references, this is a simple approach that would need to be 
      // customized based on your actual scripture reference format
      final String krishnaResponse = response['response'];
      
      // Add Krishna's response
      setState(() {
        _messages.add(Message(
          content: krishnaResponse,
          sender: 'krishna',
        ));
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
      _showError('Failed to send message: $e');
    }
  }
  
  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  Widget _buildMessage(Message message) {
    final isUserMessage = message.sender == 'user';
    
    return Align(
      alignment: isUserMessage ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 16.0),
        padding: const EdgeInsets.all(12.0),
        decoration: BoxDecoration(
          color: isUserMessage ? Colors.blue.shade100 : Colors.orange.shade100,
          borderRadius: BorderRadius.circular(12.0),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              message.content,
              style: TextStyle(
                color: isUserMessage ? Colors.black87 : Colors.black,
              ),
            ),
            if (message.sender == 'krishna' && 
                message.content.contains('View Scripture')) 
              TextButton(
                onPressed: () {
                  // This is where you would handle scripture references
                  // For now, we'll just navigate to the scripture screen
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => ScriptureListScreen(
                        apiService: widget.apiService,
                      ),
                    ),
                  );
                },
                child: Text('View Scriptures'),
                style: TextButton.styleFrom(
                  foregroundColor: Colors.deepOrange,
                ),
              ),
          ],
        ),
      ),
    );
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('KrishnaAI'),
        backgroundColor: Colors.orange.shade600,
        actions: [
          IconButton(
            icon: const Icon(Icons.book),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => ScriptureListScreen(
                    apiService: widget.apiService,
                  ),
                ),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _resetConversation,
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              reverse: false,
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                return _buildMessage(_messages[index]);
              },
            ),
          ),
          if (_isLoading)
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: Text(
                'Krishna is typing...',
                style: TextStyle(
                  fontStyle: FontStyle.italic,
                  color: Colors.orange.shade800,
                ),
              ),
            ),
          Divider(height: 1.0),
          Container(
            decoration: BoxDecoration(
              color: Theme.of(context).cardColor,
            ),
            child: _buildTextComposer(),
          ),
        ],
      ),
    );
  }
  
  Widget _buildTextComposer() {
    return IconTheme(
      data: IconThemeData(color: Theme.of(context).colorScheme.secondary),
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 8.0),
        child: Row(
          children: [
            Flexible(
              child: TextField(
                controller: _textController,
                onSubmitted: _isLoading ? null : _handleSubmitted,
                decoration: InputDecoration.collapsed(
                  hintText: 'Talk to Krishna...',
                ),
                enabled: !_isLoading,
              ),
            ),
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 4.0),
              child: IconButton(
                icon: const Icon(Icons.send),
                onPressed: _isLoading
                    ? null
                    : () => _handleSubmitted(_textController.text),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
EOF

cat > $APP_DIR/lib/screens/scripture_screen.dart << 'EOF'
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/scripture.dart';

class ScriptureListScreen extends StatefulWidget {
  final ApiService apiService;
  
  const ScriptureListScreen({Key? key, required this.apiService}) : super(key: key);

  @override
  _ScriptureListScreenState createState() => _ScriptureListScreenState();
}

class _ScriptureListScreenState extends State<ScriptureListScreen> {
  List<Scripture> _scriptures = [];
  bool _isLoading = true;
  
  @override
  void initState() {
    super.initState();
    _loadScriptures();
  }
  
  Future<void> _loadScriptures() async {
    try {
      final scriptureData = await widget.apiService.getScriptures();
      setState(() {
        _scriptures = scriptureData
            .map((s) => Scripture.fromJson(s))
            .toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
      _showError('Failed to load scriptures: $e');
    }
  }
  
  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Sacred Scriptures'),
        backgroundColor: Colors.orange.shade600,
      ),
      body: _isLoading
          ? Center(child: CircularProgressIndicator())
          : _scriptures.isEmpty
              ? Center(child: Text('No scriptures available'))
              : ListView.builder(
                  itemCount: _scriptures.length,
                  itemBuilder: (context, index) {
                    final scripture = _scriptures[index];
                    return ListTile(
                      leading: Icon(Icons.book, color: Colors.orange),
                      title: Text(scripture.name),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => ScriptureViewScreen(
                              apiService: widget.apiService,
                              scripture: scripture,
                            ),
                          ),
                        );
                      },
                    );
                  },
                ),
    );
  }
}

class ScriptureViewScreen extends StatefulWidget {
  final ApiService apiService;
  final Scripture scripture;
  
  const ScriptureViewScreen({
    Key? key,
    required this.apiService,
    required this.scripture,
  }) : super(key: key);

  @override
  _ScriptureViewScreenState createState() => _ScriptureViewScreenState();
}

class _ScriptureViewScreenState extends State<ScriptureViewScreen> {
  ScriptureContent? _content;
  bool _isLoading = true;
  int _currentPage = 1;
  
  @override
  void initState() {
    super.initState();
    _loadScripturePage(_currentPage);
  }
  
  Future<void> _loadScripturePage(int page) async {
    setState(() {
      _isLoading = true;
    });
    
    try {
      final response = await widget.apiService.getScripture(
        widget.scripture.id,
        page,
      );
      
      if (response['success'] == true) {
        setState(() {
          _content = ScriptureContent.fromJson(response);
          _currentPage = page;
          _isLoading = false;
        });
      } else {
        _showError('Failed to load scripture: ${response['message']}');
        setState(() {
          _isLoading = false;
        });
      }
    } catch (e) {
      _showError('Error: $e');
      setState(() {
        _isLoading = false;
      });
    }
  }
  
  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.scripture.name),
        backgroundColor: Colors.orange.shade600,
      ),
      body: _isLoading
          ? Center(child: CircularProgressIndicator())
          : _content == null
              ? Center(child: Text('Unable to load scripture'))
              : Column(
                  children: [
                    Expanded(
                      child: ListView.builder(
                        padding: EdgeInsets.all(16.0),
                        itemCount: _content!.verses.length,
                        itemBuilder: (context, index) {
                          final verse = _content!.verses[index];
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 16.0),
                            child: RichText(
                              text: TextSpan(
                                children: [
                                  TextSpan(
                                    text: '${verse.verseNum}. ',
                                    style: TextStyle(
                                      fontWeight: FontWeight.bold,
                                      color: Colors.orange.shade800,
                                      fontSize: 16.0,
                                    ),
                                  ),
                                  TextSpan(
                                    text: verse.text,
                                    style: TextStyle(
                                      color: Colors.black87,
                                      fontSize: 16.0,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          ElevatedButton(
                            onPressed: _currentPage > 1
                                ? () => _loadScripturePage(_currentPage - 1)
                                : null,
                            child: Text('Previous'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.orange.shade600,
                              foregroundColor: Colors.white,
                            ),
                          ),
                          Text(
                            'Page $_currentPage of ${_content!.totalPages}',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          ElevatedButton(
                            onPressed: _currentPage < _content!.totalPages
                                ? () => _loadScripturePage(_currentPage + 1)
                                : null,
                            child: Text('Next'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.orange.shade600,
                              foregroundColor: Colors.white,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
    );
  }
}
EOF

# Create main app file
cat > $APP_DIR/lib/main.dart << 'EOF'
import 'package:flutter/material.dart';
import 'screens/chat_screen.dart';
import 'services/api_service.dart';

void main() {
  runApp(KrishnaAI());
}

class KrishnaAI extends StatelessWidget {
  // Change this URL to your server when deploying
  final ApiService apiService = ApiService(baseUrl: 'http://localhost:5000');
  
  KrishnaAI({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'KrishnaAI',
      theme: ThemeData(
        primarySwatch: Colors.orange,
        visualDensity: VisualDensity.adaptivePlatformDensity,
        fontFamily: 'Poppins',
      ),
      debugShowCheckedModeBanner: false,
      home: ChatScreen(apiService: apiService),
    );
  }
}
EOF

# Update dependencies in pubspec.yaml
cat > $APP_DIR/pubspec.yaml << 'EOF'
name: krishna_ai_app
description: KrishnaAI - Your Spiritual Guide

publish_to: 'none'

version: 1.0.0+1

environment:
  sdk: ">=3.0.0 <4.0.0"

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.5
  http: ^1.1.0
  shared_preferences: ^2.2.1
  url_launcher: ^6.1.14
  intl: ^0.18.1
  google_fonts: ^5.1.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^2.0.3

flutter:
  uses-material-design: true
  
  fonts:
    - family: Poppins
      fonts:
        - asset: fonts/Poppins-Regular.ttf
        - asset: fonts/Poppins-Bold.ttf
          weight: 700
        - asset: fonts/Poppins-Light.ttf
          weight: 300
EOF

# Create directory for fonts
mkdir -p $APP_DIR/fonts
echo "Fonts directory created. You'll need to add Poppins font files manually."

# Update iOS project settings
mkdir -p $APP_DIR/ios/Runner/Assets.xcassets/AppIcon.appiconset
echo "iOS app icon directory created. You'll need to add app icons manually."

# Create a shell script for running the app
cat > run_app.sh << 'EOF'
#!/bin/bash

# This script starts both the Flutter app and Flask backend

# Start Flask backend
echo "Starting Flask backend..."
cd "$(dirname "$0")"
python app.py &
FLASK_PID=$!

# Wait a moment for Flask to start
sleep 2

# Start Flutter app
echo "Starting Flutter app..."
cd "$(dirname "$0")"/krishna_ai_app
flutter run -d chrome

# When Flutter app is closed, kill Flask backend
kill $FLASK_PID
EOF
chmod +x run_app.sh

# Create a README file with instructions
cat > $APP_DIR/README.md << 'EOF'
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
EOF

# Install dependencies
cd $APP_DIR
flutter pub get

echo "===== Setup Complete! ====="
echo "To run your KrishnaAI app:"
echo "1. Start your Flask backend: python app.py"
echo "2. Run the Flutter app: cd $APP_DIR && flutter run -d chrome"
echo "or"
echo "Run both with one command: ./run_app.sh"
echo ""
echo "To build for app stores:"
echo "iOS: cd $APP_DIR && flutter build ios"
echo "Android: cd $APP_DIR && flutter build appbundle"
echo ""
echo "Enjoy your cross-platform KrishnaAI app!" 