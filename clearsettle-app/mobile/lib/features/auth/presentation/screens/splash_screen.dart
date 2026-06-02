import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/route_constants.dart';
import '../../../../core/theme/app_colors.dart';
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
    _scale = Tween<double>(begin: 0.82, end: 1.0)
        .animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeOutBack));

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
        ClipRRect(
          borderRadius: BorderRadius.circular(28),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
            child: Container(
              width: 110,
              height: 110,
              decoration: BoxDecoration(
                color: const Color(0x0DFFFFFF),
                borderRadius: BorderRadius.circular(28),
                border: Border.all(color: const Color(0x1AFFFFFF)),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(28),
                child: Image.asset(
                  'assets/images/clear_settle_logo.png',
                  fit: BoxFit.contain,
                  errorBuilder: (_, __, ___) => const Icon(
                    Icons.account_balance_outlined,
                    color: AppColors.accent,
                    size: 52,
                  ),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 24),
        ShaderMask(
          shaderCallback: (b) => const LinearGradient(
            colors: [Color(0xFF0ABFCA), Color(0xFF7FE4EC)],
          ).createShader(b),
          child: const Text(
            'ClearSettle',
            style: TextStyle(
              fontSize: 30,
              fontWeight: FontWeight.w800,
              color: Colors.white,
              letterSpacing: -0.5,
            ),
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'eCommerce Settlement Intelligence',
          style: TextStyle(fontSize: 13, color: Color(0xFF4B6080)),
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
          style: TextStyle(fontSize: 11, color: Color(0xFF2D4060)),
        ),
        SizedBox(height: 4),
        Text(
          'v1.0.0',
          style: TextStyle(fontSize: 10, color: Color(0xFF1E3050)),
        ),
      ],
    );
  }
}
