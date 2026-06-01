import 'dart:ui';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/config/app_config.dart';
import '../../../../core/constants/route_constants.dart';
import '../providers/auth_provider.dart';

// ── Dark auth screen design tokens ───────────────────────────────────────────
// Self-contained (do not pull app_colors.dart — that's the light app theme).
// All values are pixel-exact matches to the ClearSettle web login page:
//   index.css → .login-wrap / .login-form-card / .btn-p
//   Login.jsx → inline styles
abstract final class _C {
  // Background gradient — web: linear-gradient(135deg,#0D1F35,#0A1628,#061020)
  static const bg1 = Color(0xFF0D1F35);
  static const bg2 = Color(0xFF0A1628);
  static const bg3 = Color(0xFF061020);

  // Teal accent — web CTA: linear-gradient(135deg,#0ABFCA,#088F99)
  static const teal   = Color(0xFF0ABFCA);
  static const teal2  = Color(0xFF088F99);
  static const tealLt = Color(0xFF7FE4EC); // gradient text end
  static const purple = Color(0xFF7B52E8); // orb #2

  // Glassmorphism card — web: rgba(255,255,255,.05) / rgba(255,255,255,.1)
  static const card       = Color(0x0DFFFFFF); // ~5 % white
  static const cardBorder = Color(0x1AFFFFFF); // ~10 % white

  // Inputs — web: rgba(255,255,255,.07) / rgba(255,255,255,.12)
  static const inputBg     = Color(0x12FFFFFF); // ~7 % white
  static const inputBorder = Color(0x1FFFFFFF); // ~12 % white

  // Text palette — web: #8FA5BD labels, #4B6080 subtitles
  static const label = Color(0xFF8FA5BD);
  static const sub   = Color(0xFF4B6080);

  // Error — web: rgba(232,52,74,.15) bg / rgba(232,52,74,.3) border / #F87171 text
  static const errBg     = Color(0x26E8344A); // ~15 % red
  static const errBorder = Color(0x4DE8344A); // ~30 % red
  static const errText   = Color(0xFFF87171);
}

// ── Typography ────────────────────────────────────────────────────────────────
// Font weights matched to web (800 headings, 700 CTA, 600 labels, 400 body).
// Family stays Roboto until google_fonts is added to pubspec.
abstract final class _T {
  static const _f = 'Roboto';

  static const brand = TextStyle(
    fontFamily: _f, fontSize: 22,
    fontWeight: FontWeight.w800, color: Colors.white, letterSpacing: -0.5,
  );
  static const heading = TextStyle(
    fontFamily: _f, fontSize: 20,
    fontWeight: FontWeight.w800, color: Colors.white, letterSpacing: -0.3,
  );
  static const subtitle = TextStyle(
    fontFamily: _f, fontSize: 13,
    fontWeight: FontWeight.w400, color: _C.sub,
  );
  static const label = TextStyle(
    fontFamily: _f, fontSize: 12,
    fontWeight: FontWeight.w600, color: _C.label, letterSpacing: 0.2,
  );
  static const input = TextStyle(
    fontFamily: _f, fontSize: 14,
    fontWeight: FontWeight.w400, color: Colors.white,
  );
  static const hint = TextStyle(
    fontFamily: _f, fontSize: 14, color: _C.label,
  );
  static const btn = TextStyle(
    fontFamily: _f, fontSize: 15,
    fontWeight: FontWeight.w700, color: Colors.white, letterSpacing: 0.3,
  );
  static const errMsg = TextStyle(
    fontFamily: _f, fontSize: 13, color: _C.errText, height: 1.45,
  );
  static const errVal = TextStyle(
    fontFamily: _f, fontSize: 11, color: _C.errText,
  );
  static const footer = TextStyle(
    fontFamily: _f, fontSize: 12, color: _C.sub,
  );
}

// ─────────────────────────────────────────────────────────────────────────────

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen>
    with SingleTickerProviderStateMixin {
  final _formKey  = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  final _passCtrl  = TextEditingController();
  bool _hidePass = true;
  String? _error;
  late final AnimationController _orbAnim;

  @override
  void initState() {
    super.initState();
    _emailCtrl.text = AppConfig.superAdminEmail;
    _orbAnim = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 5),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _orbAnim.dispose();
    _emailCtrl.dispose();
    _passCtrl.dispose();
    super.dispose();
  }

  // ── Logic ─────────────────────────────────────────────────────────────────

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _error = null);

    final conn = await Connectivity().checkConnectivity();
    if (!conn.any((r) => r != ConnectivityResult.none)) {
      setState(() => _error =
          'No internet connection. Check your Wi-Fi or mobile data.');
      return;
    }

    await ref.read(authProvider.notifier).login(
      _emailCtrl.text.trim(),
      _passCtrl.text,
    );

    if (!mounted) return;
    ref.read(authProvider).whenOrNull(
      error: (e, _) => setState(() => _error = _parseError(e)),
    );
  }

  String _parseError(Object e) {
    final msg = e.toString();
    if (msg.contains('401') || msg.contains('Unauthorized')) {
      return 'Invalid email or password.';
    }
    if (msg.contains('429') || msg.contains('locked')) {
      return 'Too many attempts. Please wait 15 minutes and try again.';
    }
    if (msg.contains('Network') || msg.contains('connection') ||
        msg.contains('Connection') || msg.contains('timeout')) {
      return 'Cannot reach the server. Please try again.';
    }
    if (msg.contains('ServerException')) {
      final detail = RegExp(r'ServerException\(\d*\): (.+)').firstMatch(msg)?.group(1);
      if (detail != null && detail != 'Server error.') return detail;
    }
    return 'Login failed. Please try again.';
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final isLoading = ref.watch(authProvider).isLoading;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light, // white status-bar icons on dark bg
      child: Scaffold(
        backgroundColor: _C.bg3,
        body: Stack(
          children: [
            const _Background(),
            _Orbs(anim: _orbAnim),
            SafeArea(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 24, vertical: 28),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 400),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildBrandHeader(),
                          const SizedBox(height: 28),
                          _buildFormCard(isLoading),
                          const SizedBox(height: 32),
                          _buildFooter(),
                        ],
                      ),
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

  // ── Brand header (above card) ─────────────────────────────────────────────
  // Logo badge + gradient "ClearSettle" wordmark + heading + subtitle.
  // On mobile web the left branding panel is hidden; this compensates.

  Widget _buildBrandHeader() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Logo + wordmark row
        Row(
          children: [
            const _LogoBadge(),
            const SizedBox(width: 12),
            ShaderMask(
              shaderCallback: (b) => const LinearGradient(
                colors: [_C.teal, _C.tealLt],
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
              ).createShader(b),
              child: const Text('ClearSettle', style: _T.brand),
            ),
          ],
        ),
        const SizedBox(height: 28),
        // Page heading + subtitle
        const Text('Sign in to ClearSettle', style: _T.heading),
        const SizedBox(height: 6),
        const Text('Manage your eCommerce settlements', style: _T.subtitle),
      ],
    );
  }

  // ── Glassmorphism form card ───────────────────────────────────────────────

  Widget _buildFormCard(bool isLoading) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: _C.card,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: _C.cardBorder),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_error != null) ...[
                _ErrorBanner(message: _error!),
                const SizedBox(height: 16),
              ],
              const _FieldLabel('Email address'),
              const SizedBox(height: 8),
              _buildEmailField(),
              const SizedBox(height: 16),
              const _FieldLabel('Password'),
              const SizedBox(height: 8),
              _buildPasswordField(),
              const SizedBox(height: 24),
              _GradientButton(
                label: 'Sign In',
                isLoading: isLoading,
                onTap: isLoading ? null : _login,
              ),
              const SizedBox(height: 12),
              Center(
                child: GestureDetector(
                  onTap: () =>
                      context.push(RouteConstants.forgotPassword),
                  child: const Text(
                    'Forgot password?',
                    style: TextStyle(
                      fontSize: 13,
                      color: Color(0xFF0ABFCA),
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Fields ────────────────────────────────────────────────────────────────

  Widget _buildEmailField() {
    return TextFormField(
      controller: _emailCtrl,
      keyboardType: TextInputType.emailAddress,
      textInputAction: TextInputAction.next,
      autocorrect: false,
      style: _T.input,
      cursorColor: _C.teal,
      decoration: _inputDec(
        hint: 'you@company.in',
        prefix: Icons.mail_outline_rounded,
      ),
      validator: (v) {
        if (v == null || v.trim().isEmpty) return 'Email is required';
        if (!RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(v.trim())) {
          return 'Enter a valid email address';
        }
        return null;
      },
    );
  }

  Widget _buildPasswordField() {
    return TextFormField(
      controller: _passCtrl,
      obscureText: _hidePass,
      textInputAction: TextInputAction.done,
      onFieldSubmitted: (_) => _login(),
      style: _T.input,
      cursorColor: _C.teal,
      decoration: _inputDec(
        hint: '••••••••',
        prefix: Icons.lock_outline_rounded,
        suffix: IconButton(
          onPressed: () => setState(() => _hidePass = !_hidePass),
          splashRadius: 20,
          icon: Icon(
            _hidePass
                ? Icons.visibility_off_outlined
                : Icons.visibility_outlined,
            size: 18,
            color: _C.label,
          ),
        ),
      ),
      validator: (v) {
        if (v == null || v.isEmpty) return 'Password is required';
        if (v.length < 6) return 'At least 6 characters';
        return null;
      },
    );
  }

  Widget _buildFooter() {
    return const Center(
      child: Text(
        '${AppConfig.appName}  ·  v${AppConfig.appVersion}',
        style: _T.footer,
      ),
    );
  }

  // ── Shared input decoration ───────────────────────────────────────────────

  InputDecoration _inputDec({
    required String hint,
    required IconData prefix,
    Widget? suffix,
  }) {
    const radius = BorderRadius.all(Radius.circular(10));
    return InputDecoration(
      hintText: hint,
      hintStyle: _T.hint,
      filled: true,
      fillColor: _C.inputBg,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      prefixIcon: Icon(prefix, size: 18, color: _C.label),
      suffixIcon: suffix,
      enabledBorder: const OutlineInputBorder(
        borderRadius: radius, borderSide: BorderSide(color: _C.inputBorder)),
      focusedBorder: const OutlineInputBorder(
        borderRadius: radius,
        borderSide: BorderSide(color: _C.teal, width: 1.5)),
      errorBorder: const OutlineInputBorder(
        borderRadius: radius, borderSide: BorderSide(color: _C.errText)),
      focusedErrorBorder: const OutlineInputBorder(
        borderRadius: radius,
        borderSide: BorderSide(color: _C.errText, width: 1.5)),
      errorStyle: _T.errVal,
      errorMaxLines: 2,
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Composable sub-widgets (stateless, extracted for readability + reuse)
// ─────────────────────────────────────────────────────────────────────────────

// Full-screen gradient background
class _Background extends StatelessWidget {
  const _Background();

  @override
  Widget build(BuildContext context) {
    return const DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [_C.bg1, _C.bg2, _C.bg3],
          stops: [0.0, 0.5, 1.0],
        ),
      ),
      child: SizedBox.expand(),
    );
  }
}

// Animated ambient orbs — replicates web's pulsing rgba gradient circles
class _Orbs extends StatelessWidget {
  const _Orbs({required this.anim});
  final Animation<double> anim;

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    return AnimatedBuilder(
      animation: anim,
      builder: (_, __) {
        final v = anim.value; // 0.0 → 1.0 → 0.0 (repeating)
        return Stack(
          children: [
            // Top-left teal orb — web: { w:400, top:'-10%', left:'-10%', c:'rgba(10,191,202,.06)' }
            Positioned(
              top: -120 + v * 24,
              left: -80,
              child: _orb(360, _C.teal.withValues(alpha: 0.04 + v * 0.04)),
            ),
            // Bottom-right purple orb — web: { w:300, bottom:'-5%', right:'5%', c:'rgba(123,82,232,.06)' }
            Positioned(
              bottom: -70 + v * 16,
              right: -50,
              child: _orb(280, _C.purple.withValues(alpha: 0.04 + v * 0.03)),
            ),
            // Centre accent — web: { w:200, top:'40%', left:'45%', c:'rgba(10,191,202,.04)' }
            Positioned(
              top: size.height * 0.4 + v * 12,
              left: size.width * 0.45,
              child: _orb(180, _C.teal.withValues(alpha: 0.02 + v * 0.02)),
            ),
          ],
        );
      },
    );
  }

  static Widget _orb(double size, Color color) => Container(
    width: size, height: size,
    decoration: BoxDecoration(shape: BoxShape.circle, color: color),
  );
}

// Logo contained in a dark-glassed rounded badge
class _LogoBadge extends StatelessWidget {
  const _LogoBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 44, height: 44,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: const Color(0xFF0D2137),
        border: Border.all(color: _C.cardBorder),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Image.asset(
          'assets/images/clear_settle_logo.png',
          width: 44, height: 44,
          fit: BoxFit.contain,
        ),
      ),
    );
  }
}

// Input field label — matches web: 12px / 600 / #8FA5BD
class _FieldLabel extends StatelessWidget {
  const _FieldLabel(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Text(text, style: _T.label);
}

// Error banner — matches web: rgba(232,52,74,.15) bg + rgba(232,52,74,.3) border + #F87171
class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: _C.errBg,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: _C.errBorder),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 1),
            child: Icon(Icons.error_outline_rounded, color: _C.errText, size: 16),
          ),
          const SizedBox(width: 10),
          Expanded(child: Text(message, style: _T.errMsg)),
        ],
      ),
    );
  }
}

// CTA button — teal gradient + glow shadow, matches web .btn-p
// Disabled/loading state uses muted gradient without shadow.
class _GradientButton extends StatelessWidget {
  const _GradientButton({
    required this.label,
    required this.isLoading,
    required this.onTap,
  });

  final String label;
  final bool isLoading;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final disabled = isLoading || onTap == null;
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: disabled
              ? [const Color(0xFF5AB3BB), const Color(0xFF3D7A82)]
              : [_C.teal, _C.teal2],
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
        ),
        borderRadius: BorderRadius.circular(10),
        boxShadow: disabled
            ? null
            : [
                BoxShadow(
                  color: _C.teal.withValues(alpha: 0.25),
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
                      width: 22, height: 22,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        valueColor: AlwaysStoppedAnimation(Colors.white),
                      ),
                    )
                  : Text('$label  →', style: _T.btn),
            ),
          ),
        ),
      ),
    );
  }
}
