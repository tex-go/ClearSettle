import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/route_constants.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_endpoints.dart';
import '../../../../core/utils/cs_logger.dart';
import '../providers/register_provider.dart';

// ── Design tokens (same palette as login/register screens) ───────────────────
abstract final class _C {
  static const bg1 = Color(0xFF0D1F35);
  static const bg2 = Color(0xFF0A1628);
  static const bg3 = Color(0xFF061020);
  static const teal       = Color(0xFF0ABFCA);
  static const teal2      = Color(0xFF088F99);
  static const tealLt     = Color(0xFF7FE4EC);
  static const purple     = Color(0xFF7B52E8);
  static const card       = Color(0x0DFFFFFF);
  static const cardBorder = Color(0x1AFFFFFF);
  static const inputBg     = Color(0x12FFFFFF);
  static const inputBorder = Color(0x1FFFFFFF);
  static const label   = Color(0xFF8FA5BD);
  static const sub     = Color(0xFF4B6080);
  static const errBg     = Color(0x26E8344A);
  static const errBorder = Color(0x4DE8344A);
  static const errText   = Color(0xFFF87171);
}

abstract final class _T {
  static const _f = 'Roboto';
  static const brand    = TextStyle(fontFamily: _f, fontSize: 22, fontWeight: FontWeight.w800, color: Colors.white, letterSpacing: -0.5);
  static const heading  = TextStyle(fontFamily: _f, fontSize: 20, fontWeight: FontWeight.w800, color: Colors.white, letterSpacing: -0.3);
  static const subtitle = TextStyle(fontFamily: _f, fontSize: 13, fontWeight: FontWeight.w400, color: _C.sub);
  static const label    = TextStyle(fontFamily: _f, fontSize: 12, fontWeight: FontWeight.w600, color: _C.label, letterSpacing: 0.2);
  static const input    = TextStyle(fontFamily: _f, fontSize: 14, fontWeight: FontWeight.w400, color: Colors.white);
  static const hint     = TextStyle(fontFamily: _f, fontSize: 14, color: _C.label);
  static const btn      = TextStyle(fontFamily: _f, fontSize: 15, fontWeight: FontWeight.w700, color: Colors.white, letterSpacing: 0.3);
  static const errMsg   = TextStyle(fontFamily: _f, fontSize: 13, color: _C.errText, height: 1.45);
  static const errVal   = TextStyle(fontFamily: _f, fontSize: 11, color: _C.errText);
  static const stepLabel = TextStyle(fontFamily: _f, fontSize: 11, fontWeight: FontWeight.w600, color: _C.label, letterSpacing: 0.5);
  static const roleTitle = TextStyle(fontFamily: _f, fontSize: 14, fontWeight: FontWeight.w700, color: Colors.white);
  static const roleDesc  = TextStyle(fontFamily: _f, fontSize: 12, fontWeight: FontWeight.w400, color: _C.label, height: 1.4);
}

// ─────────────────────────────────────────────────────────────────────────────

class SocialOnboardingScreen extends ConsumerStatefulWidget {
  const SocialOnboardingScreen({super.key});

  @override
  ConsumerState<SocialOnboardingScreen> createState() =>
      _SocialOnboardingScreenState();
}

class _SocialOnboardingScreenState
    extends ConsumerState<SocialOnboardingScreen>
    with SingleTickerProviderStateMixin {

  int _step = 0; // 0 = Business, 1 = Role
  final _pageCtrl = PageController();

  // Step 1 — Business
  final _step1Key     = GlobalKey<FormState>();
  final _phoneCtrl    = TextEditingController();
  final _companyCtrl  = TextEditingController();
  final _stateCtrl    = TextEditingController();
  final _cityCtrl     = TextEditingController();
  final _gstinCtrl    = TextEditingController();

  // Step 2 — Role
  String _selectedRole = 'company_admin';

  bool _submitting = false;
  String? _error;

  late final AnimationController _orbAnim;

  @override
  void initState() {
    super.initState();
    _orbAnim = AnimationController(vsync: this, duration: const Duration(seconds: 5))
      ..repeat(reverse: true);
  }

  @override
  void dispose() {
    _orbAnim.dispose();
    _pageCtrl.dispose();
    _phoneCtrl.dispose();
    _companyCtrl.dispose();
    _stateCtrl.dispose();
    _cityCtrl.dispose();
    _gstinCtrl.dispose();
    super.dispose();
  }

  // ── Navigation ─────────────────────────────────────────────────────────────

  void _next() {
    if (_step == 0) {
      if (!_step1Key.currentState!.validate()) return;
      setState(() => _step++);
      _pageCtrl.animateToPage(1,
          duration: const Duration(milliseconds: 300), curve: Curves.easeInOut);
    } else {
      _submit();
    }
  }

  void _back() {
    if (_step > 0) {
      setState(() => _step--);
      _pageCtrl.animateToPage(0,
          duration: const Duration(milliseconds: 300), curve: Curves.easeInOut);
    }
  }

  Future<void> _submit() async {
    setState(() { _submitting = true; _error = null; });
    try {
      final api = ref.read(apiClientProvider);
      await api.post<Map<String, dynamic>>(
        ApiEndpoints.socialCompleteProfile,
        data: {
          'phone':        _phoneCtrl.text.trim(),
          'company_name': _companyCtrl.text.trim(),
          'state':        _stateCtrl.text.trim(),
          'role':         _selectedRole,
          if (_cityCtrl.text.trim().isNotEmpty)  'city':  _cityCtrl.text.trim(),
          if (_gstinCtrl.text.trim().isNotEmpty) 'gstin': _gstinCtrl.text.trim().toUpperCase(),
        },
      );
      CsLogger.info('SocialOnboarding', 'Profile completed');
      if (mounted) context.go(RouteConstants.dashboard);
    } catch (e) {
      CsLogger.error('SocialOnboarding', 'Profile submit failed', error: e);
      setState(() => _error = 'Could not save your details. Please try again.');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  // ── Build ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: _C.bg3,
        body: Stack(
          children: [
            const _Background(),
            _Orbs(anim: _orbAnim),
            SafeArea(
              child: Column(
                children: [
                  _buildTopBar(),
                  _buildStepIndicator(),
                  Expanded(
                    child: PageView(
                      controller: _pageCtrl,
                      physics: const NeverScrollableScrollPhysics(),
                      children: [
                        _buildStep1(),
                        _buildStep2(),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── Top bar ────────────────────────────────────────────────────────────────

  Widget _buildTopBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: Row(
        children: [
          if (_step > 0)
            GestureDetector(
              onTap: _back,
              child: Container(
                width: 38, height: 38,
                decoration: BoxDecoration(
                  color: _C.inputBg,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: _C.inputBorder),
                ),
                child: const Icon(Icons.arrow_back_rounded, color: _C.label, size: 18),
              ),
            )
          else
            const SizedBox(width: 38),
          const SizedBox(width: 12),
          ShaderMask(
            shaderCallback: (b) => const LinearGradient(
              colors: [_C.teal, _C.tealLt],
            ).createShader(b),
            child: const Text('ClearSettle', style: _T.brand),
          ),
        ],
      ),
    );
  }

  // ── Step indicator ─────────────────────────────────────────────────────────

  Widget _buildStepIndicator() {
    const steps = ['Business', 'Role'];
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 0),
      child: Row(
        children: List.generate(steps.length * 2 - 1, (i) {
          if (i.isOdd) {
            return Expanded(
              child: Container(height: 1, color: i ~/ 2 < _step ? _C.teal : _C.inputBorder),
            );
          }
          final idx    = i ~/ 2;
          final done   = idx < _step;
          final active = idx == _step;
          return Column(children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 28, height: 28,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: done || active ? _C.teal : _C.inputBg,
                border: Border.all(color: done || active ? _C.teal : _C.inputBorder, width: 1.5),
              ),
              child: Center(
                child: done
                    ? const Icon(Icons.check_rounded, size: 14, color: Colors.white)
                    : Text('${idx + 1}', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: active ? Colors.white : _C.sub)),
              ),
            ),
            const SizedBox(height: 4),
            Text(steps[idx], style: _T.stepLabel),
          ]);
        }),
      ),
    );
  }

  // ── Step 1 — Business details ──────────────────────────────────────────────

  Widget _buildStep1() {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 400),
        child: Form(
          key: _step1Key,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Complete your profile', style: _T.heading),
              const SizedBox(height: 4),
              const Text("You're almost in — just tell us about your business.", style: _T.subtitle),
              const SizedBox(height: 24),
              _buildGlassCard([
                if (_error != null) ...[
                  _ErrorBanner(message: _error!),
                  const SizedBox(height: 16),
                ],
                const _FieldLabel('Mobile Number'),
                const SizedBox(height: 8),
                _buildTextField(_phoneCtrl,
                  hint: '+91 98765 43210',
                  icon: Icons.phone_outlined,
                  keyboardType: TextInputType.phone,
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return 'Mobile number is required';
                    final digits = v.replaceAll(RegExp(r'[\s\-\(\)\+]'), '');
                    if (!RegExp(r'^\d+$').hasMatch(digits) || digits.length < 10) {
                      return 'Enter a valid 10-digit mobile number';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 14),
                const _FieldLabel('Company / Organisation Name'),
                const SizedBox(height: 8),
                _buildTextField(_companyCtrl,
                  hint: 'Acme Traders Pvt Ltd',
                  icon: Icons.business_outlined,
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Company name is required' : null,
                ),
                const SizedBox(height: 14),
                const _FieldLabel('State'),
                const SizedBox(height: 8),
                _buildTextField(_stateCtrl,
                  hint: 'Tamil Nadu',
                  icon: Icons.location_on_outlined,
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'State is required' : null,
                ),
                const SizedBox(height: 14),
                const _FieldLabel('City (Optional)'),
                const SizedBox(height: 8),
                _buildTextField(_cityCtrl, hint: 'Chennai', icon: Icons.location_city_outlined),
                const SizedBox(height: 14),
                const _FieldLabel('GST Number (Optional)'),
                const SizedBox(height: 8),
                _buildTextField(
                  _gstinCtrl,
                  hint: '33AABCU9603R1ZX',
                  icon: Icons.receipt_long_outlined,
                  textCapitalization: TextCapitalization.characters,
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return null;
                    final pattern = RegExp(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$');
                    if (!pattern.hasMatch(v.trim().toUpperCase())) {
                      return 'Invalid GST format (e.g. 33AABCU9603R1ZX)';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 24),
                _GradientButton(label: 'Continue', isLoading: false, onTap: _next),
              ]),
            ],
          ),
        ),
      ),
    );
  }

  // ── Step 2 — Role ──────────────────────────────────────────────────────────

  Widget _buildStep2() {
    final rolesAsync = ref.watch(registrationRolesProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 400),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Your role', style: _T.heading),
            const SizedBox(height: 4),
            const Text('Select the role that best describes you', style: _T.subtitle),
            const SizedBox(height: 20),
            if (_error != null) ...[
              _ErrorBanner(message: _error!),
              const SizedBox(height: 16),
            ],
            rolesAsync.when(
              loading: () => const Center(child: CircularProgressIndicator(color: _C.teal)),
              error:   (_, __) => _buildFallbackRoles(),
              data:    (roles) => Column(
                children: roles.map((r) => _buildRoleCard(r.id, r.name, r.description)).toList(),
              ),
            ),
            const SizedBox(height: 20),
            _GradientButton(
              label: 'Start using ClearSettle',
              isLoading: _submitting,
              onTap: _submitting ? null : _submit,
            ),
            const SizedBox(height: 12),
            Center(
              child: GestureDetector(
                onTap: _back,
                child: const Text('← Back',
                    style: TextStyle(fontSize: 13, color: _C.label, fontWeight: FontWeight.w500)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFallbackRoles() {
    const fallback = [
      ('company_admin',          'Organization Owner',       'Full access to organization, users, reports, reconciliation and settings.'),
      ('finance_manager',        'Finance Manager',          'Manage settlements, reconciliation, disputes and financial reports.'),
      ('accountant',             'Accountant',               'Upload reports, view reconciliation and GST data.'),
      ('reconciliation_analyst', 'Reconciliation Executive', 'View and run reconciliation across all marketplaces.'),
      ('gst_consultant',         'GST Executive',            'Access GST modules — view, file and export GST returns.'),
      ('auditor',                'Auditor',                  'Read-only access across all modules including audit logs.'),
      ('viewer',                 'Viewer',                   'Read-only access to settlements and reports.'),
    ];
    return Column(
      children: fallback.map((r) => _buildRoleCard(r.$1, r.$2, r.$3)).toList(),
    );
  }

  Widget _buildRoleCard(String id, String name, String description) {
    final selected = _selectedRole == id;
    return GestureDetector(
      onTap: () => setState(() => _selectedRole = id),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: selected ? _C.teal.withValues(alpha: 0.12) : _C.inputBg,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: selected ? _C.teal : _C.inputBorder, width: selected ? 1.5 : 1),
        ),
        child: Row(children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            width: 20, height: 20,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: selected ? _C.teal : Colors.transparent,
              border: Border.all(color: selected ? _C.teal : _C.inputBorder, width: 1.5),
            ),
            child: selected ? const Icon(Icons.check_rounded, size: 12, color: Colors.white) : null,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(name, style: _T.roleTitle),
              const SizedBox(height: 3),
              Text(description, style: _T.roleDesc),
            ]),
          ),
        ]),
      ),
    );
  }

  // ── Helpers ────────────────────────────────────────────────────────────────

  Widget _buildGlassCard(List<Widget> children) {
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
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: children),
        ),
      ),
    );
  }

  Widget _buildTextField(
    TextEditingController ctrl, {
    required String hint,
    required IconData icon,
    TextInputType keyboardType = TextInputType.text,
    TextInputAction textInputAction = TextInputAction.next,
    TextCapitalization textCapitalization = TextCapitalization.none,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: ctrl,
      keyboardType: keyboardType,
      textInputAction: textInputAction,
      textCapitalization: textCapitalization,
      style: _T.input,
      cursorColor: _C.teal,
      decoration: _inputDec(hint: hint, prefix: icon),
      validator: validator,
    );
  }

  InputDecoration _inputDec({required String hint, required IconData prefix}) {
    const radius = BorderRadius.all(Radius.circular(10));
    return InputDecoration(
      hintText: hint,
      hintStyle: _T.hint,
      filled: true,
      fillColor: _C.inputBg,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      prefixIcon: Icon(prefix, size: 18, color: _C.label),
      enabledBorder: const OutlineInputBorder(borderRadius: radius, borderSide: BorderSide(color: _C.inputBorder)),
      focusedBorder: const OutlineInputBorder(borderRadius: radius, borderSide: BorderSide(color: _C.teal, width: 1.5)),
      errorBorder: const OutlineInputBorder(borderRadius: radius, borderSide: BorderSide(color: _C.errText)),
      focusedErrorBorder: const OutlineInputBorder(borderRadius: radius, borderSide: BorderSide(color: _C.errText, width: 1.5)),
      errorStyle: _T.errVal,
      errorMaxLines: 2,
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-widgets
// ─────────────────────────────────────────────────────────────────────────────

class _Background extends StatelessWidget {
  const _Background();
  @override
  Widget build(BuildContext context) {
    return const DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft, end: Alignment.bottomRight,
          colors: [_C.bg1, _C.bg2, _C.bg3], stops: [0.0, 0.5, 1.0],
        ),
      ),
      child: SizedBox.expand(),
    );
  }
}

class _Orbs extends StatelessWidget {
  const _Orbs({required this.anim});
  final Animation<double> anim;
  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    return AnimatedBuilder(
      animation: anim,
      builder: (_, __) {
        final v = anim.value;
        return Stack(children: [
          Positioned(top: -120 + v * 24, left: -80,  child: _orb(360, _C.teal.withValues(alpha: 0.04 + v * 0.04))),
          Positioned(bottom: -70 + v * 16, right: -50, child: _orb(280, _C.purple.withValues(alpha: 0.04 + v * 0.03))),
          Positioned(top: size.height * 0.4 + v * 12, left: size.width * 0.45, child: _orb(180, _C.teal.withValues(alpha: 0.02 + v * 0.02))),
        ]);
      },
    );
  }
  static Widget _orb(double size, Color color) =>
      Container(width: size, height: size, decoration: BoxDecoration(shape: BoxShape.circle, color: color));
}

class _FieldLabel extends StatelessWidget {
  const _FieldLabel(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Text(text, style: _T.label);
}

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message});
  final String message;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(color: _C.errBg, borderRadius: BorderRadius.circular(10), border: Border.all(color: _C.errBorder)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Padding(padding: EdgeInsets.only(top: 1), child: Icon(Icons.error_outline_rounded, color: _C.errText, size: 16)),
        const SizedBox(width: 10),
        Expanded(child: Text(message, style: _T.errMsg)),
      ]),
    );
  }
}

class _GradientButton extends StatelessWidget {
  const _GradientButton({required this.label, required this.isLoading, required this.onTap});
  final String label;
  final bool isLoading;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) {
    final disabled = isLoading || onTap == null;
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: disabled ? [const Color(0xFF5AB3BB), const Color(0xFF3D7A82)] : [_C.teal, _C.teal2],
          begin: Alignment.centerLeft, end: Alignment.centerRight,
        ),
        borderRadius: BorderRadius.circular(10),
        boxShadow: disabled ? null : [BoxShadow(color: _C.teal.withValues(alpha: 0.25), blurRadius: 8, offset: const Offset(0, 2))],
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
                  ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5, valueColor: AlwaysStoppedAnimation(Colors.white)))
                  : Text('$label  →', style: _T.btn),
            ),
          ),
        ),
      ),
    );
  }
}
