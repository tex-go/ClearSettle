import 'package:equatable/equatable.dart';

enum MessageRole { user, assistant }

class ChatMessage extends Equatable {
  const ChatMessage({
    required this.id,
    required this.role,
    required this.text,
    this.ctaLabel,
    this.ctaRoute,
    required this.timestamp,
  });

  final String id;
  final MessageRole role;
  final String text;
  final String? ctaLabel;  // e.g. "View Full Analysis"
  final String? ctaRoute;  // route to navigate to on CTA tap
  final DateTime timestamp;

  bool get isUser => role == MessageRole.user;

  @override
  List<Object?> get props => [id];
}
