import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../../domain/entities/chat_message.dart';

const _uuid = Uuid();

class CopilotNotifier extends Notifier<List<ChatMessage>> {
  @override
  List<ChatMessage> build() => [
        ChatMessage(
          id: _uuid.v4(),
          role: MessageRole.assistant,
          text: 'Hi Vishnu! 👋 How can I help you today?',
          timestamp: DateTime.now(),
        ),
      ];

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;

    // Add user message
    state = [
      ...state,
      ChatMessage(
        id: _uuid.v4(),
        role: MessageRole.user,
        text: text.trim(),
        timestamp: DateTime.now(),
      ),
    ];

    // Simulate AI response (replace with real API call)
    await Future.delayed(const Duration(milliseconds: 800));
    final reply = _generateMockReply(text.trim());
    state = [...state, reply];
  }

  void clearHistory() => state = [
        ChatMessage(
          id: _uuid.v4(),
          role: MessageRole.assistant,
          text: 'Hi! How can I help you today?',
          timestamp: DateTime.now(),
        ),
      ];

  ChatMessage _generateMockReply(String query) {
    final q = query.toLowerCase();
    if (q.contains('settlement') && q.contains('lower')) {
      return ChatMessage(
        id: _uuid.v4(),
        role: MessageRole.assistant,
        text: 'Your Amazon settlement is ₹8,420 lower than expected due to:\n'
            '• Higher returns\n'
            '• Extra fees\n'
            '• Promo discounts',
        ctaLabel: 'View Full Analysis',
        ctaRoute: '/issues',
        timestamp: DateTime.now(),
      );
    }
    if (q.contains('high impact') || q.contains('issue')) {
      return ChatMessage(
        id: _uuid.v4(),
        role: MessageRole.assistant,
        text: 'You have 7 high impact issues worth ₹28,450.',
        ctaLabel: 'View Issues →',
        ctaRoute: '/issues',
        timestamp: DateTime.now(),
      );
    }
    if (q.contains('recover') || q.contains('claim')) {
      return ChatMessage(
        id: _uuid.v4(),
        role: MessageRole.assistant,
        text: 'Based on your current discrepancies, you can potentially '
            'recover ₹42,680 this month. I recommend filing claims for the '
            '3 high-priority missing payments first.',
        ctaLabel: 'Start Recovery',
        ctaRoute: '/issues',
        timestamp: DateTime.now(),
      );
    }
    return ChatMessage(
      id: _uuid.v4(),
      role: MessageRole.assistant,
      text: 'I\'m analysing your settlement data. Could you be more specific '
          'about what you\'d like to know? For example, try asking about '
          'missing payments, excess fees, or settlement trends.',
      timestamp: DateTime.now(),
    );
  }
}

final copilotProvider =
    NotifierProvider<CopilotNotifier, List<ChatMessage>>(CopilotNotifier.new);
