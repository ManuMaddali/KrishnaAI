import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:http/http.dart' as http;
import 'package:mockito/annotations.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:krishna_ai_app/services/api_service.dart';
import 'dart:convert';

// Generate a MockClient using the Mockito package
@GenerateMocks([http.Client])
import 'api_service_test.mocks.dart';

void main() {
  late MockClient mockClient;
  late ApiService apiService;
  
  setUp(() async {
    // Initialize SharedPreferences
    SharedPreferences.setMockInitialValues({
      'session_id': 'test-session-id',
    });
    
    mockClient = MockClient();
    apiService = ApiService();
  });
  
  test('Short follow-up messages should be enhanced with context', () async {
    // Mock initial message
    final initialMessage = 'Tell me about Krishna';
    final initialResponse = {
      'response': 'Krishna is the Supreme Personality of Godhead.',
    };
    
    // Mock follow-up message
    final followUpMessage = 'can you deepen';
    final enhancedMessage = 'Based on your previous response about "Tell me about Krishna", can you deepen';
    final followUpResponse = {
      'response': 'Krishna is the source of all spiritual and material worlds.',
    };
    
    // Send the initial message
    await apiService.sendMessage(initialMessage);
    
    // Send the follow-up message and verify it's enhanced
    final response = await apiService.sendMessage(followUpMessage);
    
    // Verify the follow-up message was enhanced with context
    expect(apiService.getLastEnhancedMessage(), contains(initialMessage));
    expect(apiService.getLastEnhancedMessage(), equals(enhancedMessage));
  });
  
  test('resetConversation should clear message context', () async {
    // Set up initial message context
    await apiService.sendMessage('Initial message');
    expect(apiService.getLastUserMessage(), equals('Initial message'));
    
    // Reset conversation
    await apiService.resetConversation();
    
    // Verify context is cleared
    expect(apiService.getLastUserMessage(), isEmpty);
    expect(apiService.getLastKrishnaResponse(), isEmpty);
  });
} 