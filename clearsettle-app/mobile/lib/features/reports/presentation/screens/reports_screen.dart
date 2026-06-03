import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/route_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../providers/reports_provider.dart';
import '../widgets/report_card.dart';

class ReportsScreen extends ConsumerWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(reportsProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      // ── App bar ──────────────────────────────────────────────────────────
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0.5,
        shadowColor: AppColors.divider,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Settlement Reports',
                style: AppTextStyles.headlineSmall),
            Text(
              '${state.reports.length} report${state.reports.length == 1 ? '' : 's'}',
              style:
                  AppTextStyles.labelSmall.copyWith(color: AppColors.textMuted),
            ),
          ],
        ),
        actions: [
          if (state.isBusy)
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 16),
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                    strokeWidth: 2, color: AppColors.accent),
              ),
            )
          else
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: IconButton(
                icon: const Icon(Icons.search_rounded),
                color: AppColors.textSecondary,
                onPressed: () => context.push(RouteConstants.search),
                tooltip: 'Search',
              ),
            ),
          if (!state.isBusy)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: _UploadChip(
                onTap: () =>
                    ref.read(reportsProvider.notifier).pickAndUpload(),
              ),
            ),
        ],
      ),

      body: Column(
        children: [
          // ── Error banner ───────────────────────────────────────────────
          if (state.errorMessage != null)
            _ErrorBanner(
              message: state.errorMessage!,
              onDismiss: () =>
                  ref.read(reportsProvider.notifier).clearError(),
            ),

          // ── 6-Step upload flow panel ───────────────────────────────────
          if (state.isBusy)
            _UploadFlowPanel(
              isUploading: state.isUploading,
              fileName: state.uploadingFileName ??
                  state.reports
                      .where((r) => r.id == state.parsingReportId)
                      .map((r) => r.fileName)
                      .firstOrNull,
            ),

          // ── List / empty state ─────────────────────────────────────────
          Expanded(
            child: state.reports.isEmpty
                ? _EmptyReports(
                    onUpload: () =>
                        ref.read(reportsProvider.notifier).pickAndUpload(),
                  )
                : RefreshIndicator(
                    color: AppColors.accent,
                    onRefresh: () async =>
                        ref.read(reportsProvider.notifier).refresh(),
                    child: ListView.separated(
                      padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
                      itemCount: state.reports.length,
                      separatorBuilder: (_, __) =>
                          const SizedBox(height: 10),
                      itemBuilder: (context, i) {
                        final report = state.reports[i];
                        return ReportCard(
                          report: report,
                          isParsing:
                              state.parsingReportId == report.id,
                          onTap: () => context.push(
                            RouteConstants.reportDetailPath(report.id),
                          ),
                          onRetry: report.isFailed
                              ? () => ref
                                  .read(reportsProvider.notifier)
                                  .retryParse(report.id)
                              : null,
                          onDelete: () =>
                              _confirmDelete(context, ref, report.id),
                        );
                      },
                    ),
                  ),
          ),
        ],
      ),

      // ── FAB — visible at all times for easy access ──────────────────────
      floatingActionButton: state.isBusy
          ? null
          : FloatingActionButton.extended(
              onPressed: () =>
                  ref.read(reportsProvider.notifier).pickAndUpload(),
              backgroundColor: AppColors.accent,
              foregroundColor: Colors.white,
              elevation: 4,
              icon: const Icon(Icons.upload_file_outlined, size: 20),
              label: const Text('Upload Report',
                  style: TextStyle(fontWeight: FontWeight.w600)),
            ),
    );
  }

  Future<void> _confirmDelete(
    BuildContext context,
    WidgetRef ref,
    String reportId,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16)),
        title: const Text('Delete Report'),
        content: const Text(
          'This will permanently delete the report and all parsed data. This cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Delete',
                style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      ref.read(reportsProvider.notifier).deleteReport(reportId);
    }
  }
}

// ── Upload chip in AppBar ────────────────────────────────────────────────────

class _UploadChip extends StatelessWidget {
  const _UploadChip({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 34,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(
          color: AppColors.accent,
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.upload_rounded, size: 14, color: Colors.white),
            SizedBox(width: 5),
            Text('Upload',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}

// ── Error banner ─────────────────────────────────────────────────────────────

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message, required this.onDismiss});
  final String message;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColors.error.withValues(alpha: 0.07),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: AppColors.error, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(message,
                style: AppTextStyles.bodySmall
                    .copyWith(color: AppColors.error)),
          ),
          GestureDetector(
            onTap: onDismiss,
            child: const Icon(Icons.close,
                size: 16, color: AppColors.textMuted),
          ),
        ],
      ),
    );
  }
}

// ── 6-Step Upload Flow Panel ─────────────────────────────────────────────────

class _UploadFlowPanel extends StatefulWidget {
  const _UploadFlowPanel({required this.isUploading, this.fileName});
  final bool isUploading;
  final String? fileName;

  @override
  State<_UploadFlowPanel> createState() => _UploadFlowPanelState();
}

class _UploadFlowPanelState extends State<_UploadFlowPanel> {
  // How many steps are "done" (showing green tick)
  int _doneCount = 0;
  // Index of the step currently spinning (-1 = none)
  int _activeStep = 0;

  static const _uploadSteps = [
    'Reading file',
    'Sending to AI analysis',
  ];

  static const _parseSteps = [
    'Platform detected',
    'Report type confirmed',
    'Validating transactions',
    'Generating insights',
  ];

  // Delays (ms) before each parse step becomes "done"
  static const _parseDelays = [1000, 2500, 4500, 7000];

  @override
  void initState() {
    super.initState();
    _runUploadSteps();
  }

  @override
  void didUpdateWidget(_UploadFlowPanel old) {
    super.didUpdateWidget(old);
    // Transitioned from uploading → parsing
    if (old.isUploading && !widget.isUploading) {
      _doneCount = _uploadSteps.length;
      _activeStep = _uploadSteps.length;
      _runParseSteps();
    }
  }

  Future<void> _runUploadSteps() async {
    for (int i = 0; i < _uploadSteps.length; i++) {
      if (!mounted) return;
      await Future.delayed(Duration(milliseconds: 600 + i * 800));
      if (!mounted) return;
      setState(() {
        _doneCount = i + 1;
        _activeStep = i + 1;
      });
    }
  }

  Future<void> _runParseSteps() async {
    for (int i = 0; i < _parseSteps.length; i++) {
      if (!mounted) return;
      await Future.delayed(Duration(milliseconds: _parseDelays[i]));
      if (!mounted) return;
      setState(() {
        _doneCount = _uploadSteps.length + i + 1;
        _activeStep = _uploadSteps.length + i + 1;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final allSteps = [..._uploadSteps, ..._parseSteps];
    final label = widget.fileName != null
        ? widget.isUploading
            ? 'Uploading ${widget.fileName}'
            : 'Analysing ${widget.fileName}'
        : widget.isUploading
            ? 'Preparing upload…'
            : 'Analysing report…';

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 4),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.r3),
        border: Border.all(color: AppColors.border),
        boxShadow: AppShadows.card,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(
                    strokeWidth: 2, color: AppColors.accent),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(label,
                    style: AppTextStyles.bodySmall.copyWith(
                      color: AppColors.accent,
                      fontWeight: FontWeight.w600,
                    )),
              ),
              Text(
                '$_doneCount/${allSteps.length}',
                style: AppTextStyles.labelSmall
                    .copyWith(color: AppColors.textMuted),
              ),
            ],
          ),
          const SizedBox(height: 10),
          // Progress bar
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: allSteps.isEmpty
                  ? 0
                  : _doneCount / allSteps.length,
              minHeight: 4,
              backgroundColor: AppColors.borderLight,
              valueColor:
                  const AlwaysStoppedAnimation<Color>(AppColors.accent),
            ),
          ),
          const SizedBox(height: 12),
          // Step rows
          ...List.generate(allSteps.length, (i) {
            final isDone   = i < _doneCount;
            final isActive = i == _activeStep && !isDone;
            final isParseSep = i == _uploadSteps.length;

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (isParseSep && i > 0) ...[
                  const Divider(height: 12),
                ],
                _StepRow(
                  label: allSteps[i],
                  isDone: isDone,
                  isActive: isActive,
                ),
              ],
            );
          }),
        ],
      ),
    );
  }
}

class _StepRow extends StatelessWidget {
  const _StepRow({
    required this.label,
    required this.isDone,
    required this.isActive,
  });

  final String label;
  final bool isDone;
  final bool isActive;

  @override
  Widget build(BuildContext context) {
    final color = isDone
        ? AppColors.success
        : isActive
            ? AppColors.accent
            : AppColors.textDisabled;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 300),
            child: isDone
                ? const Icon(Icons.check_circle_rounded,
                    key: ValueKey('done'),
                    size: 15,
                    color: AppColors.success)
                : isActive
                    ? const SizedBox(
                        key: ValueKey('spin'),
                        width: 15,
                        height: 15,
                        child: CircularProgressIndicator(
                            strokeWidth: 1.5, color: AppColors.accent),
                      )
                    : const Icon(Icons.radio_button_unchecked,
                        key: ValueKey('idle'),
                        size: 15,
                        color: AppColors.textDisabled),
          ),
          const SizedBox(width: 10),
          Text(
            label,
            style: AppTextStyles.bodySmall.copyWith(
              color: color,
              fontWeight: isDone || isActive
                  ? FontWeight.w500
                  : FontWeight.w400,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Empty state ──────────────────────────────────────────────────────────────

class _EmptyReports extends StatelessWidget {
  const _EmptyReports({required this.onUpload});
  final VoidCallback onUpload;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: AppColors.accent.withValues(alpha: 0.08),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.description_outlined,
                  size: 36, color: AppColors.accent),
            ),
            const SizedBox(height: 20),
            const Text(
              'No reports uploaded yet',
              style: AppTextStyles.headlineSmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Upload your Flipkart settlement Excel file to get a full financial analytics report.',
              style: AppTextStyles.bodyMedium
                  .copyWith(color: AppColors.textSecondary),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            GestureDetector(
              onTap: onUpload,
              child: Container(
                height: 52,
                padding: const EdgeInsets.symmetric(horizontal: 32),
                decoration: BoxDecoration(
                  color: AppColors.accent,
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.accent.withValues(alpha: 0.35),
                      blurRadius: 16,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.upload_file_outlined,
                        color: Colors.white, size: 20),
                    SizedBox(width: 10),
                    Text(
                      'Upload Report',
                      style: TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.check_circle_outline,
                    size: 13, color: AppColors.success),
                const SizedBox(width: 5),
                Text('Supports .xlsx and .xls files',
                    style: AppTextStyles.labelSmall
                        .copyWith(color: AppColors.textMuted)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
