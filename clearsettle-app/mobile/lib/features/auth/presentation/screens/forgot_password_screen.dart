import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// Reuses the dark login design tokens — no app_colors light theme
class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() =>
      _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState
    extends ConsumerState<ForgotPasswordScreen> {
  final _formKey   = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  bool _loading   = false;
  bool _sent      = false;
  String? _error;

  static const _bg1    = Color(0xFF0D1F35);
  static const _bg3    = Color(0xFF061020);
  static const _teal   = Color(0xFF0ABFCA);
  static const _card   = Color(0x0DFFFFFF);
  static const _border = Color(0x1AFFFFFF);
  static const _input  = Color(0x12FFFFFF);
  static const _label  = Color(0xFF8FA5BD);
  static const _errBg  = Color(0x26E8344A);
  static const _errBdr = Color(0x4DE8344A);
  static const _errTxt = Color(0xFFF87171);

  @override
  void dispose() {
    _emailCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _loading = true; _error = null; });

    // Simulate API call — replace with real forgot-password endpoint
    await Future.delayed(const Duration(seconds: 2));

    if (!mounted) return;
    setState(() { _loading = false; _sent = true; });
  }

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: _bg3,
        body: Stack(
          children: [
            const DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [_bg1, Color(0xFF0A1628), _bg3],
                  stops: [0.0, 0.5, 1.0],
                ),
              ),
              child: SizedBox.expand(),
            ),
            SafeArea(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 24, vertical: 28),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 400),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _BackButton(onTap: () => Navigator.of(context).pop()),
                        const SizedBox(height: 24),
                        _buildCard(),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCard() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          padding: const EdgeInsets.all(28),
          decoration: BoxDecoration(
            color: _card,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: _border),
          ),
          child: _sent ? _buildSuccess() : _buildForm(),
        ),
      ),
    );
  }

  Widget _buildSuccess() {
    return Column(
      children: [
        Container(
          width: 64,
          height: 64,
          decoration: BoxDecoration(
            color: _teal.withValues(alpha: 0.15),
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.mark_email_read_outlined,
              color: _teal, size: 32),
        ),
        const SizedBox(height: 20),
        const Text(
          'Check your email',
          style: TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 12),
        Text(
          'We sent a password reset link to\n${_emailCtrl.text.trim()}',
          style: const TextStyle(color: _label, fontSize: 14, height: 1.5),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 28),
        _TealButton(
          label: 'Back to Sign In',
          isLoading: false,
          onTap: () => Navigator.of(context).pop(),
        ),
      ],
    );
  }

  Widget _buildForm() {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Forgot Password',
            style: TextStyle(
              color: Colors.white,
              fontSize: 22,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.3,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            "Enter your account email and we'll send you a reset link.",
            style: TextStyle(color: _label, fontSize: 13, height: 1.5),
          ),
          const SizedBox(height: 24),
          if (_error != null) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: _errBg,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: _errBdr),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline_rounded,
                      color: _errTxt, size: 16),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(_error!,
                        style: const TextStyle(
                            color: _errTxt, fontSize: 13)),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],
          const Text(
            'EMAIL ADDRESS',
            style: TextStyle(
              color: _label,
              fontSize: 11,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.8,
            ),
          ),
          const SizedBox(height: 8),
          TextFormField(
            controller: _emailCtrl,
            keyboardType: TextInputType.emailAddress,
            autocorrect: false,
            style: const TextStyle(color: Colors.white, fontSize: 14),
            cursorColor: _teal,
            decoration: InputDecoration(
              hintText: 'you@company.in',
              hintStyle: const TextStyle(color: _label, fontSize: 14),
              filled: true,
              fillColor: _input,
              contentPadding: const EdgeInsets.symmetric(
                  horizontal: 14, vertical: 14),
              prefixIcon: const Icon(Icons.mail_outline_rounded,
                  size: 18, color: _label),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide:
                    const BorderSide(color: Color(0x1FFFFFFF)),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: _teal, width: 1.5),
              ),
              errorBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: _errTxt),
              ),
              focusedErrorBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: _errTxt, width: 1.5),
              ),
              errorStyle:
                  const TextStyle(color: _errTxt, fontSize: 11),
            ),
            validator: (v) {
              if (v == null || v.trim().isEmpty) return 'Email is required';
              if (!RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(v.trim())) {
                return 'Enter a valid email address';
              }
              return null;
            },
          ),
          const SizedBox(height: 24),
          _TealButton(
            label: 'Send Reset Link',
            isLoading: _loading,
            onTap: _loading ? null : _submit,
          ),
        ],
      ),
    );
  }
}

// ── Shared sub-widgets ────────────────────────────────────────────────────────

class _BackButton extends StatelessWidget {
  const _BackButton({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.arrow_back_ios_new_rounded,
              color: Color(0xFF8FA5BD), size: 16),
          SizedBox(width: 6),
          Text(
            'Back to Sign In',
            style: TextStyle(color: Color(0xFF8FA5BD), fontSize: 13),
          ),
        ],
      ),
    );
  }
}

class _TealButton extends StatelessWidget {
  const _TealButton({
    required this.label,
    required this.isLoading,
    required this.onTap,
  });

  final String label;
  final bool isLoading;
  final VoidCallback? onTap;

  static const _teal  = Color(0xFF0ABFCA);
  static const _teal2 = Color(0xFF088F99);

  @override
  Widget build(BuildContext context) {
    final disabled = isLoading || onTap == null;
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: disabled
              ? [const Color(0xFF5AB3BB), const Color(0xFF3D7A82)]
              : [_teal, _teal2],
        ),
        borderRadius: BorderRadius.circular(10),
        boxShadow: disabled
            ? null
            : [
                BoxShadow(
                  color: _teal.withValues(alpha: 0.25),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(10),
          child: SizedBox(
            height: 52,
            child: Center(
              child: isLoading
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        valueColor:
                            AlwaysStoppedAnimation(Colors.white),
                      ),
                    )
                  : Text(
                      label,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.3,
                      ),
                    ),
            ),
          ),
        ),
      ),
    );
  }
}
