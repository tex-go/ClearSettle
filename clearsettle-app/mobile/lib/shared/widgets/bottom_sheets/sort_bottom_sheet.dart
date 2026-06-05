import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';

enum SortOrder { ascending, descending }

class SortOption {
  const SortOption({required this.label, required this.value});
  final String label;
  final String value;
}

/// Sort bottom sheet — single-select with asc/desc toggle.
class SortBottomSheet extends StatefulWidget {
  const SortBottomSheet({
    super.key,
    required this.options,
    this.selectedValue,
    this.selectedOrder = SortOrder.descending,
  });

  final List<SortOption> options;
  final String? selectedValue;
  final SortOrder selectedOrder;

  static Future<({String value, SortOrder order})?> show(
    BuildContext context, {
    required List<SortOption> options,
    String? selectedValue,
    SortOrder selectedOrder = SortOrder.descending,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => SortBottomSheet(
        options: options,
        selectedValue: selectedValue,
        selectedOrder: selectedOrder,
      ),
    );
  }

  @override
  State<SortBottomSheet> createState() => _SortBottomSheetState();
}

class _SortBottomSheetState extends State<SortBottomSheet> {
  late String? _value = widget.selectedValue;
  late SortOrder _order = widget.selectedOrder;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor    = isDark ? AppColors.surfaceDark : AppColors.surface;
    final borderColor = isDark ? AppColors.borderDark : AppColors.border;
    final textPrimary = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;
    final textMuted   = isDark ? AppColors.textMutedDark   : AppColors.textMuted;

    return Container(
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        border: Border(top: BorderSide(color: borderColor)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                margin: const EdgeInsets.only(top: 12, bottom: 8),
                width: 36, height: 4,
                decoration: BoxDecoration(
                  color: textMuted.withValues(alpha: 0.3),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
              child: Row(
                children: [
                  Text('Sort by',
                      style: TextStyle(
                          fontFamily: 'Inter', fontSize: 16,
                          fontWeight: FontWeight.w600, color: textPrimary)),
                  const Spacer(),
                  _OrderToggle(
                    order: _order,
                    onToggle: (o) => setState(() => _order = o),
                    textMuted: textMuted,
                  ),
                ],
              ),
            ),
            const Divider(height: 16),
            ...widget.options.map((opt) {
              final isSelected = _value == opt.value;
              return ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 16),
                title: Text(opt.label,
                    style: TextStyle(
                        fontFamily: 'Inter', fontSize: 14,
                        color: isSelected ? AppColors.teal500 : textPrimary,
                        fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400)),
                trailing: isSelected
                    ? const Icon(Icons.check_circle_rounded,
                        color: AppColors.teal500, size: 20)
                    : null,
                onTap: () {
                  setState(() => _value = opt.value);
                  Navigator.of(context)
                      .pop((value: opt.value, order: _order));
                },
              );
            }),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}

class _OrderToggle extends StatelessWidget {
  const _OrderToggle({
    required this.order,
    required this.onToggle,
    required this.textMuted,
  });
  final SortOrder order;
  final ValueChanged<SortOrder> onToggle;
  final Color textMuted;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => onToggle(
          order == SortOrder.descending ? SortOrder.ascending : SortOrder.descending),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: textMuted.withValues(alpha: 0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              order == SortOrder.descending
                  ? Icons.arrow_downward_rounded
                  : Icons.arrow_upward_rounded,
              size: 14, color: AppColors.teal500,
            ),
            const SizedBox(width: 4),
            Text(
              order == SortOrder.descending ? 'High → Low' : 'Low → High',
              style: const TextStyle(fontFamily: 'Inter', fontSize: 12,
                  color: AppColors.teal500, fontWeight: FontWeight.w500),
            ),
          ],
        ),
      ),
    );
  }
}
