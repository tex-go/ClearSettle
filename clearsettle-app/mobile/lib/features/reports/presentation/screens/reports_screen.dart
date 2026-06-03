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
      body: CustomScrollView(
        slivers: [
          // ── App bar ───────────────────────────────────────────────────
          SliverAppBar(
            backgroundColor: AppColors.surface,
            surfaceTintColor: Colors.transparent,
            elevation: 0,
            floating: true,
            snap: true,
            expandedHeight: 100,
            flexibleSpace: FlexibleSpaceBar(
              titlePadding:
                  const EdgeInsets.fromLTRB(20, 0, 20, 16),
              title: Row(
                children: [
                  Expanded(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Settlement Reports',
                            style: AppTextStyles.headlineSmall),
                        Text(
                          '${state.reports.length} report${state.reports.length == 1 ? '' : 's'}',
                          style: AppTextStyles.labelSmall,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              expandedTitleScale: 1,
            ),
            actions: [
              if (state.isBusy)
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  child: SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: AppColors.accent),
                  ),
                )
              else
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: _UploadButton(
                    onTap: () => ref
                        .read(reportsProvider.notifier)
                        .pickAndUpload(),
                  ),
                ),
              Padding(
                padding: const EdgeInsets.only(right: 12),
                child: GestureDetector(
                  onTap: () => context.push(RouteConstants.search),
                  child: Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: AppColors.surfaceVariant,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.search_rounded,
                        size: 18, color: AppColors.textSecondary),
                  ),
                ),
              ),
            ],
          ),

          // ── Error banner ──────────────────────────────────────────────
          if (state.errorMessage != null)
            SliverToBoxAdapter(
              child: _ErrorBanner(
                message: state.errorMessage!,
                onDismiss: () =>
                    ref.read(reportsProvider.notifier).clearError(),
              ),
            ),

          // ── Upload progress ───────────────────────────────────────────
          if (state.isUploading)
            SliverToBoxAdapter(
              child: _UploadProgress(fileName: state.uploadingFileName),
            ),

          // ── List / empty ──────────────────────────────────────────────
          state.reports.isEmpty
              ? SliverFillRemaining(
                  hasScrollBody: false,
                  child: _EmptyReports(
                    onUpload: () => ref
                        .read(reportsProvider.notifier)
                        .pickAndUpload(),
                  ),
                )
              : SliverPadding(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                  sliver: SliverList.separated(
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
        ],
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
            borderRadius: BorderRadius.circular(AppRadius.r5)),
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
    if (confirmed == true) {
      ref.read(reportsProvider.notifier).deleteReport(reportId);
    }
  }
}

// ── Upload button ──────────────────────────────────────────────────────────

class _UploadButton extends StatelessWidget {
  const _UploadButton({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 36,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(
          color: AppColors.accent,
          borderRadius: BorderRadius.circular(10),
          boxShadow: AppShadows.ctaButton,
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.upload_rounded, size: 15, color: Colors.white),
            SizedBox(width: 6),
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

// ── Error banner ───────────────────────────────────────────────────────────

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message, required this.onDismiss});
  final String message;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColors.error.withValues(alpha: 0.06),
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
            child: const Icon(Icons.close, size: 16,
                color: AppColors.textMuted),
          ),
        ],
      ),
    );
  }
}

// ── Upload progress bar ────────────────────────────────────────────────────

class _UploadProgress extends StatelessWidget {
  const _UploadProgress({this.fileName});
  final String? fileName;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      color: AppColors.accent.withValues(alpha: 0.04),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.cloud_upload_outlined,
                  size: 14, color: AppColors.accent),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  fileName != null
                      ? 'Uploading $fileName…'
                      : 'Preparing upload…',
                  style: AppTextStyles.bodySmall
                      .copyWith(color: AppColors.accent, fontWeight: FontWeight.w500),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: const LinearProgressIndicator(
              color: AppColors.accent,
              backgroundColor: AppColors.surfaceVariant,
              minHeight: 3,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Empty state ────────────────────────────────────────────────────────────

class _EmptyReports extends StatelessWidget {
  const _EmptyReports({required this.onUpload});
  final VoidCallback onUpload;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Illustration placeholder — icon in circle
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
            Text('No reports uploaded yet',
                style: AppTextStyles.headlineSmall,
                textAlign: TextAlign.center),
            const SizedBox(height: 8),
            Text(
              'Upload your first settlement report to start reconciliation and see your financial insights.',
              style: AppTextStyles.bodyMedium
                  .copyWith(color: AppColors.textSecondary),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 28),
            GestureDetector(
              onTap: onUpload,
              child: Container(
                height: 50,
                padding: const EdgeInsets.symmetric(horizontal: 28),
                decoration: BoxDecoration(
                  color: AppColors.accent,
                  borderRadius: BorderRadius.circular(AppRadius.r2),
                  boxShadow: AppShadows.ctaButton,
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.upload_file_outlined,
                        color: Colors.white, size: 18),
                    SizedBox(width: 8),
                    Text('Upload Report',
                        style: TextStyle(
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: FontWeight.w600)),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
