import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../shared/widgets/ai_chat_bubble.dart';
import '../providers/copilot_provider.dart';

/// AI Copilot — natural-language settlement query interface.
///
/// Layout: AIIdentityCard (fixed top) + ChatScrollArea + InputBar (fixed bottom)
class CopilotScreen extends ConsumerStatefulWidget {
  const CopilotScreen({super.key});

  @override
  ConsumerState<CopilotScreen> createState() => _CopilotScreenState();
}

class _CopilotScreenState extends ConsumerState<CopilotScreen> {
  final _controller  = TextEditingController();
  final _scrollCtrl  = ScrollController();
  bool _isSending    = false;

  @override
  void dispose() {
    _controller.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _isSending) return;
    _controller.clear();
    setState(() => _isSending = true);
    await ref.read(copilotProvider.notifier).sendMessage(text);
    setState(() => _isSending = false);
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final messages = ref.watch(copilotProvider);
    final isDark   = Theme.of(context).brightness == Brightness.dark;

    final bgColor    = isDark ? AppColors.backgroundDark : AppColors.background;
    final surfColor  = isDark ? AppColors.surfaceDark    : AppColors.surface;
    final borderColor = isDark ? AppColors.borderDark    : AppColors.border;
    final textPrimary = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;
    final textMuted   = isDark ? AppColors.textMutedDark   : AppColors.textMuted;

    return Scaffold(
      backgroundColor: bgColor,
      appBar: _buildAppBar(isDark, textPrimary, textMuted),
      body: Column(
        children: [
          // AI identity card (pinned below app bar)
          _AiIdentityCard(isDark: isDark, borderColor: borderColor),

          // Chat scroll area
          Expanded(
            child: ListView.builder(
              controller: _scrollCtrl,
              padding: const EdgeInsets.fromLTRB(
                  AppSpacing.pageHorizontal, 16,
                  AppSpacing.pageHorizontal, 16),
              itemCount: messages.length + (_isSending ? 1 : 0),
              itemBuilder: (context, i) {
                if (i == messages.length) {
                  // Typing indicator
                  return _TypingIndicator(isDark: isDark);
                }
                final msg = messages[i];
                return AiChatBubble(
                  message: msg.text,
                  isUser: msg.isUser,
                  embeddedCtaLabel: msg.ctaLabel,
                  onCtaTap: msg.ctaRoute != null
                      ? () => context.push(msg.ctaRoute!)
                      : null,
                );
              },
            ),
          ),

          // Input bar
          _InputBar(
            controller: _controller,
            isSending: _isSending,
            onSend: _send,
            isDark: isDark,
            surfColor: surfColor,
            borderColor: borderColor,
            textMuted: textMuted,
          ),
        ],
      ),
    );
  }

  AppBar _buildAppBar(bool isDark, Color textPrimary, Color textMuted) {
    return AppBar(
      backgroundColor:
          isDark ? AppColors.surfaceDark : AppColors.surface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      toolbarHeight: AppSpacing.appBarHeight,
      title: Text('AI Copilot',
          style: TextStyle(
              fontFamily: 'Inter',
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: textPrimary)),
      centerTitle: false,
      actions: [
        IconButton(
          icon: Icon(Icons.settings_outlined, color: textMuted),
          tooltip: 'Copilot settings',
          onPressed: () {},
        ),
      ],
    );
  }
}

// ── AI identity card ──────────────────────────────────────────────────────────

class _AiIdentityCard extends StatelessWidget {
  const _AiIdentityCard({required this.isDark, required this.borderColor});
  final bool isDark;
  final Color borderColor;

  @override
  Widget build(BuildContext context) {
    final surfColor  = isDark ? AppColors.surfaceDark : AppColors.surface;
    final textPrimary = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;

    return Container(
      padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.pageHorizontal, vertical: 12),
      decoration: BoxDecoration(
        color: surfColor,
        border: Border(bottom: BorderSide(color: borderColor)),
      ),
      child: Row(
        children: [
          // ClearSettle logo avatar
          Container(
            width: 40, height: 40,
            decoration: const BoxDecoration(
              gradient: AppColors.accentGradient,
              shape: BoxShape.circle,
            ),
            child: const Center(
              child: Text('CS',
                  style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                      color: Colors.white)),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('ClearSettle AI',
                    style: TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: textPrimary)),
                const SizedBox(height: 2),
                Row(
                  children: [
                    Container(
                      width: 7, height: 7,
                      decoration: const BoxDecoration(
                        color: Color(0xFF22C55E),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 5),
                    Text('Online',
                        style: TextStyle(
                            fontFamily: 'Inter',
                            fontSize: 11,
                            color: isDark
                                ? AppColors.textMutedDark
                                : AppColors.textMuted)),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Input bar ─────────────────────────────────────────────────────────────────

class _InputBar extends StatelessWidget {
  const _InputBar({
    required this.controller,
    required this.isSending,
    required this.onSend,
    required this.isDark,
    required this.surfColor,
    required this.borderColor,
    required this.textMuted,
  });

  final TextEditingController controller;
  final bool isSending;
  final VoidCallback onSend;
  final bool isDark;
  final Color surfColor, borderColor, textMuted;

  @override
  Widget build(BuildContext context) {
    final inputBg = isDark ? AppColors.surfaceElevatedDark : AppColors.surfaceVariant;

    return Container(
      padding: EdgeInsets.fromLTRB(
          AppSpacing.pageHorizontal,
          8,
          AppSpacing.pageHorizontal,
          8 + MediaQuery.of(context).padding.bottom),
      decoration: BoxDecoration(
        color: surfColor,
        border: Border(top: BorderSide(color: borderColor)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Container(
              height: 44,
              decoration: BoxDecoration(
                color: inputBg,
                borderRadius: BorderRadius.circular(22),
              ),
              child: Semantics(
                label: 'Ask AI Copilot a question',
                child: TextField(
                  controller: controller,
                  style: TextStyle(
                      fontFamily: 'Inter', fontSize: 14,
                      color: isDark ? AppColors.textPrimaryDark : AppColors.textPrimary),
                  decoration: InputDecoration(
                    hintText: 'Ask anything...',
                    hintStyle: TextStyle(
                        fontFamily: 'Inter', fontSize: 14, color: textMuted),
                    border: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 12),
                    suffixIcon: Semantics(
                      label: 'Voice input',
                      child: Icon(Icons.mic_outlined,
                          color: textMuted, size: 20),
                    ),
                  ),
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => onSend(),
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Semantics(
            label: 'Send message',
            child: GestureDetector(
              onTap: onSend,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 150),
                width: 40, height: 40,
                decoration: BoxDecoration(
                  color: isSending
                      ? AppColors.teal500.withValues(alpha: 0.5)
                      : AppColors.teal500,
                  shape: BoxShape.circle,
                ),
                child: isSending
                    ? const Padding(
                        padding: EdgeInsets.all(10),
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.arrow_upward_rounded,
                        color: Colors.white, size: 18),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Typing indicator ──────────────────────────────────────────────────────────

class _TypingIndicator extends StatelessWidget {
  const _TypingIndicator({required this.isDark});
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    final bgColor = isDark ? AppColors.surfaceDark : AppColors.surfaceVariant;
    final dotColor = isDark ? AppColors.textSecondaryDark : AppColors.textSecondary;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(4),
                topRight: Radius.circular(16),
                bottomRight: Radius.circular(16),
                bottomLeft: Radius.circular(16),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(3, (i) => Padding(
                padding: EdgeInsets.only(right: i < 2 ? 4 : 0),
                child: Container(
                  width: 6, height: 6,
                  decoration: BoxDecoration(color: dotColor, shape: BoxShape.circle),
                ),
              )),
            ),
          ),
        ],
      ),
    );
  }
}
