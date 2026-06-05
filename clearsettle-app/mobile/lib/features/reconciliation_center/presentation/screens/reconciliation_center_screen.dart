import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../shared/widgets/bottom_sheets/upload_confirm_bottom_sheet.dart';
import '../../../../shared/widgets/reconciliation_ring.dart';

// ── Minimal in-place state ────────────────────────────────────────────────────

class _ReconState {
  const _ReconState({
    this.percent = 95.0,
    this.uploadedReports = 12,
    this.matchedTransactions = 11452,
    this.issuesFound = 23,
    this.recentUploads = const [],
  });
  final double percent;
  final int uploadedReports, matchedTransactions, issuesFound;
  final List<_UploadRecord> recentUploads;
}

class _UploadRecord {
  const _UploadRecord({
    required this.fileName,
    required this.uploadedAt,
    required this.status,
  });
  final String fileName;
  final DateTime uploadedAt;
  final String status; // 'Completed' | 'Processing' | 'Failed'
}

final _reconProvider = StateProvider<_ReconState>(
  (_) => _ReconState(
    recentUploads: [
      _UploadRecord(
        fileName: 'Amazon_May_2025.xlsx',
        uploadedAt: DateTime(2025, 5, 15, 10, 30),
        status: 'Completed',
      ),
      _UploadRecord(
        fileName: 'Flipkart_Apr_2025.xlsx',
        uploadedAt: DateTime(2025, 4, 28, 14, 0),
        status: 'Completed',
      ),
    ],
  ),
);

/// Reconciliation Center — upload zone + donut ring + recent uploads.
class ReconciliationCenterScreen extends ConsumerWidget {
  const ReconciliationCenterScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state  = ref.watch(_reconProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? AppColors.backgroundDark : AppColors.background;
    final surfColor = isDark ? AppColors.surfaceDark : AppColors.surface;
    final textPrimary = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;
    final textMuted   = isDark ? AppColors.textMutedDark   : AppColors.textMuted;
    final borderColor = isDark ? AppColors.borderDark      : AppColors.border;

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: surfColor,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        toolbarHeight: AppSpacing.appBarHeight,
        title: Text('Reconciliation Center',
            style: TextStyle(
                fontFamily: 'Inter', fontSize: 18,
                fontWeight: FontWeight.w600, color: textPrimary)),
        centerTitle: false,
        actions: [
          IconButton(
            icon: Icon(Icons.info_outline_rounded, color: textMuted),
            tooltip: 'About reconciliation',
            onPressed: () {},
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppColors.teal500,
        displacement: 60,
        onRefresh: () async {
          await Future.delayed(const Duration(milliseconds: 600));
        },
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(
              AppSpacing.pageHorizontal, 24,
              AppSpacing.pageHorizontal, 32),
          children: [
            // ── Donut ring ─────────────────────────────────────────────
            Center(
              child: ReconciliationRing(percent: state.percent),
            ),

            const SizedBox(height: 28),

            // ── Stats row ──────────────────────────────────────────────
            _StatsRow(
              uploaded: state.uploadedReports,
              matched: state.matchedTransactions,
              issues: state.issuesFound,
              isDark: isDark,
              borderColor: borderColor,
              textPrimary: textPrimary,
              textMuted: textMuted,
            ),

            const SizedBox(height: 24),
            Divider(color: borderColor),
            const SizedBox(height: 24),

            // ── Upload zone ────────────────────────────────────────────
            _UploadZone(
              isUploading: false,
              isDark: isDark,
              borderColor: borderColor,
              textMuted: textMuted,
              onUpload: () => _pickAndUpload(context, ref),
            ),

            const SizedBox(height: AppSpacing.sectionGap),

            // ── Recent uploads ─────────────────────────────────────────
            _RecentUploads(
              uploads: state.recentUploads,
              isDark: isDark,
              textPrimary: textPrimary,
              textMuted: textMuted,
              borderColor: borderColor,
              surfColor: surfColor,
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _pickAndUpload(BuildContext context, WidgetRef ref) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['xlsx', 'csv', 'txt'],
    );
    if (result == null || result.files.isEmpty) return;
    final file = result.files.first;

    if (!context.mounted) return;
    await UploadConfirmBottomSheet.show(
      context,
      fileName: file.name,
      fileSize: file.size > 0
          ? '${(file.size / 1024).toStringAsFixed(1)} KB'
          : 'Unknown',
      marketplace: 'Auto-detect',
      onConfirm: () {
        ref.read(_reconProvider.notifier).state = _ReconState(
          percent: ref.read(_reconProvider).percent,
          uploadedReports: ref.read(_reconProvider).uploadedReports + 1,
          matchedTransactions:
              ref.read(_reconProvider).matchedTransactions,
          issuesFound: ref.read(_reconProvider).issuesFound,
          recentUploads: [
            _UploadRecord(
              fileName: file.name,
              uploadedAt: DateTime.now(),
              status: 'Completed',
            ),
            ...ref.read(_reconProvider).recentUploads,
          ],
        );
      },
    );
  }
}

// ── Stats row ─────────────────────────────────────────────────────────────────

class _StatsRow extends StatelessWidget {
  const _StatsRow({
    required this.uploaded,
    required this.matched,
    required this.issues,
    required this.isDark,
    required this.borderColor,
    required this.textPrimary,
    required this.textMuted,
  });

  final int uploaded, matched, issues;
  final bool isDark;
  final Color borderColor, textPrimary, textMuted;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _StatCell(label: 'Uploaded', value: '$uploaded Reports',
            textPrimary: textPrimary, textMuted: textMuted),
        _VertDivider(color: borderColor),
        _StatCell(label: 'Matched',
            value: '${_fmt(matched)} Transactions',
            textPrimary: textPrimary, textMuted: textMuted),
        _VertDivider(color: borderColor),
        _StatCell(label: 'Issues Found',
            value: '$issues Transactions',
            textPrimary: textPrimary, textMuted: textMuted,
            valueColor: issues > 0 ? AppColors.danger : null),
      ],
    );
  }

  String _fmt(int n) =>
      n >= 1000 ? '${(n / 1000).toStringAsFixed(1)}k' : '$n';
}

class _StatCell extends StatelessWidget {
  const _StatCell({
    required this.label,
    required this.value,
    required this.textPrimary,
    required this.textMuted,
    this.valueColor,
  });

  final String label, value;
  final Color textPrimary, textMuted;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Semantics(
        label: '$label: $value',
        child: Column(
          children: [
            Text(value,
                style: TextStyle(
                  fontFamily: 'Inter', fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: valueColor ?? textPrimary,
                ),
                textAlign: TextAlign.center),
            const SizedBox(height: 3),
            Text(label,
                style: TextStyle(fontFamily: 'Inter',
                    fontSize: 11, color: textMuted),
                textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}

class _VertDivider extends StatelessWidget {
  const _VertDivider({required this.color});
  final Color color;
  @override
  Widget build(BuildContext context) =>
      Container(width: 1, height: 36, color: color);
}

// ── Upload zone ───────────────────────────────────────────────────────────────

class _UploadZone extends StatelessWidget {
  const _UploadZone({
    required this.isUploading,
    required this.isDark,
    required this.borderColor,
    required this.textMuted,
    required this.onUpload,
  });

  final bool isUploading, isDark;
  final Color borderColor, textMuted;
  final VoidCallback onUpload;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Upload settlement report',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Upload Settlement Report',
              style: TextStyle(
                  fontFamily: 'Inter', fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: isDark ? AppColors.textPrimaryDark : AppColors.textPrimary)),
          const SizedBox(height: 12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 24),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: borderColor,
                width: 1.5,
                // dashed via custom painter; use solid for simplicity in Flutter
              ),
            ),
            child: Column(
              children: [
                Icon(Icons.cloud_upload_outlined,
                    size: 36, color: textMuted),
                const SizedBox(height: 8),
                Text('Drag & drop your file here',
                    style: TextStyle(fontFamily: 'Inter',
                        fontSize: 14, color: textMuted)),
                const SizedBox(height: 6),
                Row(
                  children: [
                    Expanded(child: Divider(color: borderColor)),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 10),
                      child: Text('or',
                          style: TextStyle(fontFamily: 'Inter',
                              fontSize: 12, color: textMuted)),
                    ),
                    Expanded(child: Divider(color: borderColor)),
                  ],
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: 160,
                  child: ElevatedButton.icon(
                    onPressed: isUploading ? null : onUpload,
                    icon: isUploading
                        ? const SizedBox(
                            width: 16, height: 16,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white))
                        : const Icon(Icons.upload_rounded, size: 18),
                    label: Text(isUploading ? 'Uploading...' : 'Upload File'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      textStyle: const TextStyle(
                          fontFamily: 'Inter', fontSize: 14,
                          fontWeight: FontWeight.w600),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Text('Supported: XLSX, CSV, TXT (Max 50MB)',
                    style: TextStyle(fontFamily: 'Inter',
                        fontSize: 11, color: textMuted)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Recent uploads ────────────────────────────────────────────────────────────

class _RecentUploads extends StatelessWidget {
  const _RecentUploads({
    required this.uploads,
    required this.isDark,
    required this.textPrimary,
    required this.textMuted,
    required this.borderColor,
    required this.surfColor,
  });

  final List<_UploadRecord> uploads;
  final bool isDark;
  final Color textPrimary, textMuted, borderColor, surfColor;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text('Recent Uploads',
                style: TextStyle(fontFamily: 'Inter', fontSize: 16,
                    fontWeight: FontWeight.w600, color: textPrimary)),
            const Spacer(),
            TextButton(
              onPressed: () {},
              child: const Text('View All',
                  style: TextStyle(fontFamily: 'Inter', fontSize: 13,
                      color: AppColors.teal500)),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (uploads.isEmpty)
          Text('No reports uploaded yet.',
              style: TextStyle(fontFamily: 'Inter',
                  fontSize: 13, color: textMuted))
        else
          Container(
            decoration: BoxDecoration(
              color: surfColor,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: borderColor),
              boxShadow: AppShadows.card,
            ),
            child: Column(
              children: List.generate(uploads.length, (i) {
                final u = uploads[i];
                final isLast = i == uploads.length - 1;
                return Column(
                  children: [
                    _UploadRow(
                        record: u,
                        textPrimary: textPrimary,
                        textMuted: textMuted),
                    if (!isLast)
                      Divider(height: 1, color: borderColor,
                          indent: 16, endIndent: 16),
                  ],
                );
              }),
            ),
          ),
      ],
    );
  }
}

class _UploadRow extends StatelessWidget {
  const _UploadRow({
    required this.record,
    required this.textPrimary,
    required this.textMuted,
  });

  final _UploadRecord record;
  final Color textPrimary, textMuted;

  @override
  Widget build(BuildContext context) {
    final statusColor = record.status == 'Completed'
        ? AppColors.teal500
        : record.status == 'Processing'
            ? AppColors.warning
            : AppColors.danger;

    return Semantics(
      label: '${record.fileName}, uploaded '
          '${DateFormat('d MMM yyyy, h:mm a').format(record.uploadedAt)}, '
          '${record.status}',
      child: Padding(
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.cardPadding, vertical: 12),
        child: Row(
          children: [
            Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                color: AppColors.teal500.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.description_outlined,
                  color: AppColors.teal500, size: 18),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(record.fileName,
                      style: TextStyle(fontFamily: 'Inter', fontSize: 13,
                          fontWeight: FontWeight.w500, color: textPrimary),
                      maxLines: 1, overflow: TextOverflow.ellipsis),
                  Text(
                    DateFormat('d MMM yyyy, h:mm a').format(record.uploadedAt),
                    style: TextStyle(fontFamily: 'Inter',
                        fontSize: 11, color: textMuted),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: statusColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(100),
                border: Border.all(color: statusColor.withValues(alpha: 0.3)),
              ),
              child: Text(record.status,
                  style: TextStyle(fontFamily: 'Inter', fontSize: 11,
                      fontWeight: FontWeight.w600, color: statusColor)),
            ),
          ],
        ),
      ),
    );
  }
}
