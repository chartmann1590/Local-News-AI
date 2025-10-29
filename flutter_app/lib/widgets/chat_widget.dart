import 'package:flutter/material.dart';
import '../models/chat_message.dart';
import '../services/api_service.dart';
import '../services/logger_service.dart';

class ChatWidget extends StatefulWidget {
  final int articleId;
  final String initialAuthor;
  
  const ChatWidget({
    super.key,
    required this.articleId,
    required this.initialAuthor,
  });
  
  @override
  State<ChatWidget> createState() => _ChatWidgetState();
}

class _ChatWidgetState extends State<ChatWidget> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  List<ChatMessage> _messages = [];
  String _author = 'Local Desk';
  bool _isLoading = false;
  bool _isSending = false;
  String? _error;
  
  @override
  void initState() {
    super.initState();
    _author = widget.initialAuthor;
    LoggerService().logInfo('ChatWidget', 'Widget Initialized', details: 'Article ID: ${widget.articleId}');
    _loadChat();
  }
  
  @override
  void dispose() {
    LoggerService().logInfo('ChatWidget', 'Widget Disposed');
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }
  
  Future<void> _loadChat() async {
    LoggerService().logInfo('ChatWidget', 'Load Chat', details: 'Article ID: ${widget.articleId}');
    setState(() {
      _isLoading = true;
      _error = null;
    });
    
    try {
      final response = await ApiService.getChat(widget.articleId, screenContext: 'ChatWidget');
      
      LoggerService().logInfo('ChatWidget', 'Chat Loaded', details: 'Messages: ${response.messages.length}, Author: ${response.author}');
      
      if (mounted) {
        setState(() {
          _messages = response.messages;
          _author = response.author;
          _isLoading = false;
        });
        _scrollToBottom();
      }
    } catch (e) {
      LoggerService().logError('ChatWidget', 'Load Chat', e);
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error = 'Failed to load conversation';
        });
      }
    }
  }
  
  Future<void> _sendMessage() async {
    final message = _messageController.text.trim();
    if (message.isEmpty || _isSending) {
      if (message.isEmpty) {
        LoggerService().logWarning('ChatWidget', 'Send Message', details: 'Empty message');
      }
      return;
    }
    
    LoggerService().logInfo('ChatWidget', 'Send Message', details: 'Article ID: ${widget.articleId}, Message length: ${message.length}');
    
    setState(() {
      _isSending = true;
      _error = null;
      _messageController.clear();
    });
    
    try {
      final response = await ApiService.postChat(
        widget.articleId,
        message,
        _messages,
        screenContext: 'ChatWidget',
      );
      
      LoggerService().logInfo('ChatWidget', 'Message Sent', details: 'Response received, Messages: ${response.messages.length}');
      
      if (mounted) {
        setState(() {
          _messages = response.messages;
          _author = response.author;
          _isSending = false;
        });
        _scrollToBottom();
      }
    } catch (e) {
      LoggerService().logError('ChatWidget', 'Send Message', e);
      if (mounted) {
        setState(() {
          _isSending = false;
          final errorMsg = e.toString();
          if (errorMsg.contains('429')) {
            _error = 'You are sending messages too quickly. Please wait a moment.';
          } else {
            _error = 'Failed to send message: ${errorMsg}';
          }
        });
      }
    }
  }
  
  Future<void> _clearChat() async {
    LoggerService().logInfo('ChatWidget', 'Clear Chat', details: 'Article ID: ${widget.articleId}');
    try {
      await ApiService.deleteChat(widget.articleId, screenContext: 'ChatWidget');
      
      LoggerService().logInfo('ChatWidget', 'Chat Cleared');
      
      if (mounted) {
        setState(() {
          _messages = [];
        });
      }
    } catch (e) {
      LoggerService().logError('ChatWidget', 'Clear Chat', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to clear conversation: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
  
  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              border: Border(
                bottom: BorderSide(
                  color: Theme.of(context).dividerColor,
                ),
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    'Discuss with $_author',
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                ),
                TextButton(
                  onPressed: _messages.isEmpty ? null : _clearChat,
                  child: const Text('Clear'),
                ),
              ],
            ),
          ),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _messages.isEmpty
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Text(
                            'Start the conversation — ask a question about this article.',
                            style: Theme.of(context).textTheme.bodySmall,
                            textAlign: TextAlign.center,
                          ),
                        ),
                      )
                    : ListView.builder(
                        controller: _scrollController,
                        padding: const EdgeInsets.all(12),
                        itemCount: _messages.length,
                        itemBuilder: (context, index) {
                          final message = _messages[index];
                          return _buildMessage(message);
                        },
                      ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Text(
                _error!,
                style: const TextStyle(
                  color: Colors.red,
                  fontSize: 12,
                ),
              ),
            ),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              border: Border(
                top: BorderSide(
                  color: Theme.of(context).dividerColor,
                ),
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: const InputDecoration(
                      hintText: 'Write a comment or question',
                      border: OutlineInputBorder(),
                      contentPadding: EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 8,
                      ),
                    ),
                    maxLines: null,
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: _isSending
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.send),
                  onPressed: _isSending ? null : _sendMessage,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildMessage(ChatMessage message) {
    final isUser = message.isUser;
    
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        children: [
          if (!isUser) ...[
            CircleAvatar(
              radius: 16,
              backgroundColor: Colors.blue.shade100,
              child: Text(
                _author[0].toUpperCase(),
                style: TextStyle(
                  color: Colors.blue.shade900,
                  fontSize: 12,
                ),
              ),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isUser
                    ? Colors.blue.shade50
                    : Theme.of(context).cardColor,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: isUser
                      ? Colors.blue.shade200
                      : Theme.of(context).dividerColor,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isUser ? 'You' : _author,
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                      color: isUser
                          ? Colors.blue.shade900
                          : Colors.grey[700],
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    message.content,
                    style: const TextStyle(fontSize: 14),
                  ),
                ],
              ),
            ),
          ),
          if (isUser) ...[
            const SizedBox(width: 8),
            CircleAvatar(
              radius: 16,
              backgroundColor: Colors.grey.shade300,
              child: const Icon(
                Icons.person,
                size: 16,
                color: Colors.white,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

