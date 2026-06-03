import 'package:flutter/material.dart';

import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';

class MarketplaceBadge extends StatelessWidget {
  const MarketplaceBadge({
    super.key,
    required this.platform,
    this.isConnected = true,
  });

  final String platform;
  final bool isConnected;

  Color get _platformColor {
    switch (platform.toLowerCase()) {
      case 'flipkart':
        return AppColors.flipkart;
      case 'amazon':
        return AppColors.amazon;
      case 'meesho':
        return AppColors.meesho;
      case 'myntra':
        return AppColors.myntra;
      default:
        return AppColors.primary;
    }
  }

  String get _displayName =>
      AppConstants.marketplaceDisplayNames[platform.toLowerCase()] ?? platform;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: _platformColor.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _platformColor.withValues(alpha: 0.25)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 7,
            height: 7,
            decoration: BoxDecoration(
              color: isConnected ? AppColors.success : AppColors.textDisabled,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            _displayName,
            style: AppTextStyles.labelMedium.copyWith(color: _platformColor),
          ),
        ],
      ),
    );
  }
}
