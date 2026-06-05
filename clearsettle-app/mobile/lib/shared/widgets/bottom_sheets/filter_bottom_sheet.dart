import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';

/// Generic filter bottom sheet with a list of selectable options.
///
/// Returns the selected value via [onSelected].
/// Pass [multi: true] for multi-select mode.
class FilterBottomSheet extends StatefulWidget {
  const FilterBottomSheet({
    super.key,
    required this.title,
    required this.options,
    this.selected = const [],
    this.multi = false,
  });

  final String title;
  final List<String> options;
  final List<String> selected;
  final bool multi;

  static Future<List<String>?> show(
    BuildContext context, {
    required String title,
    required List<String> options,
    List<String> selected = const [],
    bool multi = false,
  }) {
    return showModalBottomSheet<List<String>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => FilterBottomSheet(
        title: title,
        options: options,
        selected: selected,
        multi: multi,
      ),
    );
  }

  @override
  State<FilterBottomSheet> createState() => _FilterBottomSheetState();
}

class _FilterBottomSheetState extends State<FilterBottomSheet> {
  late final Set<String> _selected = Set.from(widget.selected);

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? AppColors.surfaceDark : AppColors.surface;
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
            // Handle
            Center(
              child: Container(
                margin: const EdgeInsets.only(top: 12, bottom: 8),
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: textMuted.withValues(alpha: 0.3),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
              child: Text(
                widget.title,
                style: TextStyle(
                  fontFamily: 'Inter',
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: textPrimary,
                ),
              ),
            ),
            const Divider(height: 16),
            ...widget.options.map((opt) {
              final isSelected = _selected.contains(opt);
              return ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 16),
                title: Text(
                  opt,
                  style: TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 14,
                    color: isSelected ? AppColors.teal500 : textPrimary,
                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                  ),
                ),
                trailing: isSelected
                    ? const Icon(Icons.check_circle_rounded,
                        color: AppColors.teal500, size: 20)
                    : Icon(Icons.circle_outlined,
                        color: textMuted, size: 20),
                onTap: () {
                  setState(() {
                    if (widget.multi) {
                      if (isSelected) {
                        _selected.remove(opt);
                      } else {
                        _selected.add(opt);
                      }
                    } else {
                      _selected
                        ..clear()
                        ..add(opt);
                    }
                  });
                  if (!widget.multi) {
                    Navigator.of(context).pop(_selected.toList());
                  }
                },
              );
            }),
            if (widget.multi)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                child: ElevatedButton(
                  onPressed: () =>
                      Navigator.of(context).pop(_selected.toList()),
                  child: const Text('Apply'),
                ),
              )
            else
              const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}
