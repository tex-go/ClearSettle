import '../../../../core/errors/exceptions.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_endpoints.dart';
import '../models/dashboard_summary_model.dart';

class DashboardRemoteDataSource {
  const DashboardRemoteDataSource({required this.apiClient});

  final ApiClient apiClient;

  Future<DashboardSummaryModel> getSummary() async {
    final response = await apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.dashboardSummary,
    );

    final data = response.data;
    if (data == null) throw const ServerException(message: 'Empty dashboard response.');

    return DashboardSummaryModel.fromJson(data);
  }
}
