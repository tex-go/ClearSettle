import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/search_result_entity.dart';
import '../../domain/usecases/search_usecase.dart';

final searchUseCaseProvider = Provider<SearchUseCase>((_) => SearchUseCase());

class SearchState {
  const SearchState({
    this.query = '',
    this.results = const [],
    this.isSearching = false,
  });

  final String query;
  final List<SearchResult> results;
  final bool isSearching;

  bool get isEmpty => query.isEmpty;
  bool get hasResults => results.isNotEmpty;

  SearchState copyWith({
    String? query,
    List<SearchResult>? results,
    bool? isSearching,
  }) {
    return SearchState(
      query: query ?? this.query,
      results: results ?? this.results,
      isSearching: isSearching ?? this.isSearching,
    );
  }
}

class SearchNotifier extends Notifier<SearchState> {
  late final SearchUseCase _useCase;

  @override
  SearchState build() {
    _useCase = ref.read(searchUseCaseProvider);
    return const SearchState();
  }

  void search(String query) {
    if (query.trim().isEmpty) {
      state = const SearchState();
      return;
    }
    state = state.copyWith(query: query, isSearching: true);
    final results = _useCase(query);
    state = state.copyWith(results: results, isSearching: false);
  }

  void clear() => state = const SearchState();
}

final searchProvider = NotifierProvider<SearchNotifier, SearchState>(
  SearchNotifier.new,
);
