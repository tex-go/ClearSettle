import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/route_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../shared/widgets/empty_state_widget.dart';
import '../../domain/entities/search_result_entity.dart';
import '../providers/search_provider.dart';

class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(searchProvider);

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        titleSpacing: 0,
        title: TextField(
          controller: _controller,
          autofocus: true,
          style: AppTextStyles.bodyLarge,
          decoration: InputDecoration(
            hintText: 'Search orders, settlements, reports…',
            hintStyle: AppTextStyles.bodyLarge.copyWith(
              color: AppColors.textDisabled,
            ),
            border: InputBorder.none,
            filled: false,
          ),
          onChanged: (q) => ref.read(searchProvider.notifier).search(q),
        ),
        actions: [
          if (_controller.text.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.clear),
              onPressed: () {
                _controller.clear();
                ref.read(searchProvider.notifier).clear();
              },
            ),
        ],
      ),
      body: state.isEmpty
          ? const _SearchHint()
          : state.isSearching
              ? const Center(child: CircularProgressIndicator())
              : state.hasResults
                  ? _ResultList(results: state.results)
                  : EmptyStateWidget(
                      icon: Icons.search_off_outlined,
                      title: 'No results',
                      subtitle: 'No matches found for "${state.query}"',
                    ),
    );
  }
}

class _SearchHint extends StatelessWidget {
  const _SearchHint();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Search across', style: AppTextStyles.titleMedium),
          SizedBox(height: 12),
          _HintRow(icon: Icons.description_outlined, label: 'Report names'),
          _HintRow(icon: Icons.receipt_long_outlined, label: 'Order IDs'),
          _HintRow(icon: Icons.warning_amber_outlined, label: 'Discrepancy descriptions'),
          _HintRow(icon: Icons.storefront_outlined, label: 'Marketplace names'),
        ],
      ),
    );
  }
}

class _HintRow extends StatelessWidget {
  const _HintRow({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Icon(icon, size: 18, color: AppColors.textSecondary),
          const SizedBox(width: 10),
          Text(label, style: AppTextStyles.bodyMedium),
        ],
      ),
    );
  }
}

class _ResultList extends StatelessWidget {
  const _ResultList({required this.results});

  final List<SearchResult> results;

  @override
  Widget build(BuildContext context) {
    final reports =
        results.whereType<ReportSearchResult>().toList();
    final discrepancies =
        results.whereType<DiscrepancySearchResult>().toList();

    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        if (reports.isNotEmpty) ...[
          _SectionHeader(label: 'Reports', count: reports.length),
          ...reports.map((r) => _ReportTile(result: r)),
        ],
        if (discrepancies.isNotEmpty) ...[
          _SectionHeader(label: 'Discrepancies', count: discrepancies.length),
          ...discrepancies.map((d) => _DiscrepancyTile(result: d)),
        ],
        const SizedBox(height: 32),
      ],
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.label, required this.count});

  final String label;
  final int count;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 8, 4, 6),
      child: Text(
        '$label ($count)',
        style: AppTextStyles.labelSmall.copyWith(
          letterSpacing: 1.2,
          color: AppColors.textSecondary,
        ),
      ),
    );
  }
}

class _ReportTile extends ConsumerWidget {
  const _ReportTile({required this.result});

  final ReportSearchResult result;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListTile(
      contentPadding:
          const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      tileColor: Theme.of(context).colorScheme.surface,
      leading: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: AppColors.primary.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(8),
        ),
        child:
            const Icon(Icons.description_outlined, color: AppColors.primary, size: 18),
      ),
      title: Text(result.title, style: AppTextStyles.titleMedium),
      subtitle: Text(result.subtitle, style: AppTextStyles.labelSmall),
      trailing: const Icon(Icons.chevron_right, color: AppColors.textDisabled),
      onTap: () => context.push(RouteConstants.reportDetailPath(result.id)),
    );
  }
}

class _DiscrepancyTile extends StatelessWidget {
  const _DiscrepancyTile({required this.result});

  final DiscrepancySearchResult result;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding:
          const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      tileColor: Theme.of(context).colorScheme.surface,
      leading: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: AppColors.warning.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Icon(Icons.warning_amber_outlined,
            color: AppColors.warning, size: 18),
      ),
      title: Text(result.title, style: AppTextStyles.titleMedium),
      subtitle: Text(result.subtitle, style: AppTextStyles.labelSmall),
      trailing: const Icon(Icons.chevron_right, color: AppColors.textDisabled),
      onTap: () => context.push(
        RouteConstants.reconciliationPath(result.reportId),
      ),
    );
  }
}
