import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';

/// Confirms file upload — shows filename, size, marketplace before submitting.
class UploadConfirmBottomSheet extends StatelessWidget {
  const UploadConfirmBottomSheet({
    super.key,
    required this.fileName,
    required this.fileSize,
    required this.marketplace,
    required this.onConfirm,
  });

  final String fileName;
  final String fileSize;
  final String marketplace;
  final VoidCallback onConfirm;

  static Future<bool?> show(
    BuildContext context, {
    required String fileName,
    required String fileSize,
    required String marketplace,
    required VoidCallback onConfirm,
  }) {
    return showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => UploadConfirmBottomSheet(
        fileName: fileName,
        fileSize: fileSize,
        marketplace: marketplace,
        onConfirm: onConfirm,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor    = isDark ? AppColors.surfaceDark : AppColors.surface;
    final borderColor = isDark ? AppColors.borderDark : AppColors.border;
    final textPrimary = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;
    final textMuted   = isDark ? AppColors.textMutedDark   : AppColors.textMuted;
    final surfaceAlt  = isDark ? AppColors.surfaceElevatedDark : AppColors.surfaceVariant;

    return Container(
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        border: Border(top: BorderSide(color: borderColor)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Center(
                child: Container(
                  width: 36, height: 4,
                  decoration: BoxDecoration(
                    color: textMuted.withValues(alpha: 0.3),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              Text('Confirm Upload',
                  style: TextStyle(fontFamily: 'Inter', fontSize: 18,
                      fontWeight: FontWeight.w700, color: textPrimary)),
              const SizedBox(height: 4),
              Text('Review the details before uploading.',
                  style: TextStyle(fontFamily: 'Inter', fontSize: 13,
                      color: textMuted)),
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: surfaceAlt,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: borderColor),
                ),
                child: Column(
                  children: [
                    _DetailRow(label: 'File', value: fileName,
                        textPrimary: textPrimary, textMuted: textMuted),
                    const SizedBox(height: 10),
                    _DetailRow(label: 'Size', value: fileSize,
                        textPrimary: textPrimary, textMuted: textMuted),
                    const SizedBox(height: 10),
                    _DetailRow(label: 'Marketplace', value: marketplace,
                        textPrimary: textPrimary, textMuted: textMuted),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.of(context).pop(false),
                      child: const Text('Cancel'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: () {
                        Navigator.of(context).pop(true);
                        onConfirm();
                      },
                      child: const Text('Upload'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.label,
    required this.value,
    required this.textPrimary,
    required this.textMuted,
  });
  final String label, value;
  final Color textPrimary, textMuted;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: 90,
          child: Text(label,
              style: TextStyle(fontFamily: 'Inter', fontSize: 12,
                  color: textMuted)),
        ),
        Expanded(
          child: Text(value,
              style: TextStyle(fontFamily: 'Inter', fontSize: 13,
                  fontWeight: FontWeight.w500, color: textPrimary),
              maxLines: 1, overflow: TextOverflow.ellipsis),
        ),
      ],
    );
  }
}
