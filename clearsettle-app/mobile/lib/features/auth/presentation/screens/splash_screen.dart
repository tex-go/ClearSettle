import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/config/app_config.dart';
import '../../../../core/constants/route_constants.dart';
import '../../../../shared/widgets/cs_logo.dart';
import '../providers/auth_provider.dart';

class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _fade;
  late final Animation<double> _scale;
  bool _navigated = false;

  @override
  void initState() {
    super.initState();
    SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle.light);

    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
    _fade  = CurvedAnimation(parent: _ctrl, curve: Curves.easeOut);
    _scale = Tween<double>(begin: 0.88, end: 1.0)
        .animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeOutCubic));

    _ctrl.forward();

    // Primary: wait for auth to finish loading, then navigate immediately.
    // Fallback: always navigate after 2s even if auth hangs.
    WidgetsBinding.instance.addPostFrameCallback((_) => _waitForAuthThenNav());
    Future.delayed(const Duration(milliseconds: 2000), _doNav);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _waitForAuthThenNav() async {
    // Poll until authProvider is no longer loading, then navigate immediately.
    while (mounted && !_navigated) {
      final auth = ref.read(authProvider);
      if (!auth.isLoading) {
        await Future.delayed(const Duration(milliseconds: 600));
        _doNav();
        return;
      }
      await Future.delayed(const Duration(milliseconds: 50));
    }
  }

  void _doNav() {
    if (!mounted || _navigated) return;
    _navigated = true;
    final auth = ref.read(authProvider);
    final isAuth = auth.valueOrNull?.isAuthenticated ?? false;
    context.go(isAuth ? RouteConstants.dashboard : RouteConstants.login);
  }

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: const Color(0xFF061020),
        body: Stack(
          children: [
            const _Background(),
            Center(
              child: FadeTransition(
                opacity: _fade,
                child: ScaleTransition(
                  scale: _scale,
                  child: const _LogoCard(),
                ),
              ),
            ),
            const Positioned(
              bottom: 48,
              left: 0,
              right: 0,
              child: _BottomMeta(),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Background gradient ───────────────────────────────────────────────────────

class _Background extends StatelessWidget {
  const _Background();

  @override
  Widget build(BuildContext context) {
    return const DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF0D1F35), Color(0xFF0A1628), Color(0xFF061020)],
          stops: [0.0, 0.5, 1.0],
        ),
      ),
      child: SizedBox.expand(),
    );
  }
}

// ── Centre logo card ──────────────────────────────────────────────────────────

class _LogoCard extends StatelessWidget {
  const _LogoCard();

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const CsLogoSplash(size: 140),
        const SizedBox(height: 24),
        ShaderMask(
          shaderCallback: (b) => const LinearGradient(
            colors: [Color(0xFF0DB7A3), Color(0xFF4DD9CB)],
          ).createShader(b),
          child: const Text(
            'ClearSettle',
            style: TextStyle(
              fontFamily: 'Inter',
              fontSize: 30,
              fontWeight: FontWeight.w800,
              color: Colors.white,
              letterSpacing: -0.8,
            ),
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'eCommerce Settlement Intelligence',
          style: TextStyle(
            fontFamily: 'Inter',
            fontSize: 13,
            fontWeight: FontWeight.w400,
            color: Color(0xFF4A6180),
            letterSpacing: 0.1,
          ),
        ),
        const SizedBox(height: 40),
        const SizedBox(
          width: 28,
          height: 28,
          child: CircularProgressIndicator(
            strokeWidth: 2.5,
            valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF0ABFCA)),
          ),
        ),
      ],
    );
  }
}

// ── Bottom version strip ──────────────────────────────────────────────────────

class _BottomMeta extends StatelessWidget {
  const _BottomMeta();

  @override
  Widget build(BuildContext context) {
    return const Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'Powered by ClearSettle Platform',
          style: TextStyle(
            fontFamily: 'Inter',
            fontSize: 11,
            color: Color(0xFF2D4A6A),
            letterSpacing: 0.1,
          ),
        ),
        SizedBox(height: 4),
        Text(
          'v${AppConfig.appVersion}',
          style: TextStyle(
            fontFamily: 'Inter',
            fontSize: 10,
            color: Color(0xFF1E3A58),
          ),
        ),
      ],
    );
  }
}
