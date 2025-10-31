class ChatMessage {
  final String role; // 'user' or 'assistant'
  final String content;
  final String? createdAt;
  
  ChatMessage({
    required this.role,
    required this.content,
    this.createdAt,
  });
  
  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      role: json['role'] as String,
      content: json['content'] as String,
      createdAt: json['created_at'] as String?,
    );
  }
  
  bool get isUser => role == 'user';
  bool get isAssistant => role == 'assistant';
}

class ChatResponse {
  final String author;
  final List<ChatMessage> messages;
  
  ChatResponse({
    required this.author,
    required this.messages,
  });
  
  factory ChatResponse.fromJson(Map<String, dynamic> json) {
    final messagesList = json['messages'] as List<dynamic>? ?? [];
    return ChatResponse(
      author: json['author'] as String? ?? 'Local Desk',
      messages: messagesList.map((m) => ChatMessage.fromJson(m as Map<String, dynamic>)).toList(),
    );
  }
}





