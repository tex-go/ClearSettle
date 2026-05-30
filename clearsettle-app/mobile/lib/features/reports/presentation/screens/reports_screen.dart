import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/date_formatter.dart';
import '../../../../shared/widgets/empty_state_widget.dart';
import '../../../../storage/entities/local_report_hive_object.dart';
import '../../../../storage/hive_manager.dart';

class ReportsScreen extends ConsumerWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final reports = HiveManager.localReportBox.values.toList()
      ..sort((a, b) => b.uploadedAt.compareTo(a.uploadedAt));

    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(
        title: const Text('Reports'),
        actions: [
          IconButton(
            icon: const Icon(Icons.upload_file_outlined),
            onPressed: () => _showUploadSheet(context),
            tooltip: 'Upload report',
          ),
        ],
      ),
      body: reports.isEmpty
          ? EmptyStateWidget(
              icon: Icons.description_outlined,
              title: 'No reports yet',
              subtitle:
                  'Upload your first settlement report to get started.',
              action: TextButton.icon(
                onPressed: () => _showUploadSheet(context),
                icon: const Icon(Icons.upload_file_outlined),
                label: const Text('Upload Report'),
              ),
            )
          : ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: reports.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, index) =>
                  _ReportTile(report: reports[index]),
            ),
    );
  }

  void _showUploadSheet(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => const _UploadSheet(),
    );
  }
}

class _ReportTile extends StatelessWidget {
  const _ReportTile({required this.report});

  final LocalReportHiveObject report;

  Color get _statusColor {
    switch (report.status) {
      case 'processed':
        return AppColors.success;
      case 'failed':
        return AppColors.error;
      case 'processing':
        return AppColors.warning;
      default:
        return AppColors.textSecondary;
    }
  }

  String get _statusLabel {
    switch (report.status) {
      case 'processed':
        return 'Processed';
      case 'failed':
        return 'Failed';
      case 'processing':
        return 'Processing';
      case 'uploaded':
        return 'Uploaded';
      default:
        return 'Pending Upload';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.divider),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.08),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(
              Icons.table_chart_outlined,
              color: AppColors.primary,
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  report.fileName,
                  style: AppTextStyles.titleMedium,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 3),
                Text(
                  '${report.platform.toUpperCase()} • ${report.reportType}',
                  style: AppTextStyles.bodySmall,
                ),
                const SizedBox(height: 2),
                Text(
                  DateFormatter.formatDate(
                    DateTime.tryParse(report.uploadedAt) ?? DateTime.now(),
                  ),
                  style: AppTextStyles.labelSmall,
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: _statusColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              _statusLabel,
              style: AppTextStyles.labelSmall.copyWith(color: _statusColor),
            ),
          ),
        ],
      ),
    );
  }
}

class _UploadSheet extends StatelessWidget {
  const _UploadSheet();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 24,
        right: 24,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 32,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 36,
              height: 4,
              decoration: BoxDecoration(
                color: AppColors.divider,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text('Upload Settlement Report', style: AppTextStyles.headlineMedium),
          const SizedBox(height: 6),
          Text(
            'Supported: Flipkart settlement Excel (.xlsx)',
            style: AppTextStyles.bodySmall,
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton.icon(
              onPressed: () => Navigator.of(context).pop(),
              icon: const Icon(Icons.upload_file_outlined),
              label: const Text('Choose File'),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: OutlinedButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
          ),
        ],
      ),
    );
  }
}
