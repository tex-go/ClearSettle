import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/route_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../shared/widgets/empty_state_widget.dart';
import '../providers/reports_provider.dart';
import '../widgets/report_card.dart';

class ReportsScreen extends ConsumerWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(reportsProvider);

    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(
        title: const Text('Reports'),
        actions: [
          if (state.isBusy)
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: AppColors.textInverse,
                ),
              ),
            )
          else
            IconButton(
              icon: const Icon(Icons.upload_file_outlined),
              onPressed: () => _uploadReport(context, ref),
              tooltip: 'Upload report',
            ),
        ],
      ),
      body: Column(
        children: [
          if (state.errorMessage != null) _ErrorBanner(
            message: state.errorMessage!,
            onDismiss: () => ref.read(reportsProvider.notifier).clearError(),
          ),
          if (state.isUploading) _UploadProgressBar(
            fileName: state.uploadingFileName,
          ),
          Expanded(
            child: state.reports.isEmpty
                ? EmptyStateWidget(
                    icon: Icons.description_outlined,
                    title: 'No reports yet',
                    subtitle: 'Upload a Flipkart settlement Excel file\nto analyse fees and discrepancies.',
                    action: ElevatedButton.icon(
                      onPressed: () => _uploadReport(context, ref),
                      icon: const Icon(Icons.upload_file_outlined, size: 18),
                      label: const Text('Upload Report'),
                      style: ElevatedButton.styleFrom(
                        minimumSize: const Size(200, 46),
                      ),
                    ),
                  )
                : ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: state.reports.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (context, index) {
                      final report = state.reports[index];
                      return ReportCard(
                        report: report,
                        isParsing: state.parsingReportId == report.id,
                        onTap: () => context.push(
                          RouteConstants.reportDetailPath(report.id),
                        ),
                        onRetry: report.isFailed
                            ? () => ref
                                .read(reportsProvider.notifier)
                                .retryParse(report.id)
                            : null,
                        onDelete: () => _confirmDelete(context, ref, report.id),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Future<void> _uploadReport(BuildContext context, WidgetRef ref) async {
    await ref.read(reportsProvider.notifier).pickAndUpload();
  }

  Future<void> _confirmDelete(
    BuildContext context,
    WidgetRef ref,
    String reportId,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Report'),
        content: const Text(
          'This will permanently delete the report file and all parsed data.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text(
              'Delete',
              style: TextStyle(color: AppColors.error),
            ),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      ref.read(reportsProvider.notifier).deleteReport(reportId);
    }
  }
}

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message, required this.onDismiss});

  final String message;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColors.error.withValues(alpha: 0.08),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: AppColors.error, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
            ),
          ),
          IconButton(
            onPressed: onDismiss,
            icon: const Icon(Icons.close, size: 16),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
        ],
      ),
    );
  }
}

class _UploadProgressBar extends StatelessWidget {
  const _UploadProgressBar({this.fileName});

  final String? fileName;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      color: AppColors.primary.withValues(alpha: 0.05),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            fileName != null ? 'Uploading $fileName…' : 'Preparing upload…',
            style: AppTextStyles.bodySmall,
          ),
          const SizedBox(height: 6),
          const LinearProgressIndicator(
            color: AppColors.primary,
            backgroundColor: AppColors.surfaceVariant,
          ),
        ],
      ),
    );
  }
}
